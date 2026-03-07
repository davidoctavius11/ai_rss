#!/usr/bin/env python3
"""
Multi-perspective synthesis (cluster-based, CTO/CEO focused).
Generates and stores summaries to be appended in RSS descriptions.
"""

import json
import os
import re
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from dotenv import dotenv_values
from openai import OpenAI

KNOWLEDGE_LOG_PATH = os.path.expanduser('~/Agents/knowledge_log/concepts.json')


def _load_learning_context():
    """Load compact concept list from knowledge log for injection into synthesis prompt."""
    try:
        with open(KNOWLEDGE_LOG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        lines = [f"[{c['domain']}] {c['concept']}" for c in data.get('concepts', [])]
        return '\n'.join(lines)
    except Exception:
        return ''

from app_ai_filtered import _row_to_article, FILTER_THRESHOLD, RECENCY_DAYS, EVERGREEN_SCORE

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ai_rss.db')

# Sources eligible for multi-perspective synthesis
ELIGIBLE_SOURCES = {
    # Existing
    "TechCrunch", "36氪", "InfoQ·架构与算力", "The Verge Full Feed",
    "InfoQ Architecture (All)", "InfoQ Architecture Articles", "InfoQ Architecture News",
    "AWS Architecture Blog", "Cloudflare Changelog (Global)", "Cloudflare Changelog (Developer Platform)",
    # New — English depth
    "Wired", "Ars Technica", "MIT Technology Review", "VentureBeat",
    # New — Chinese AI
    "机器之心",
    # Extended coverage
    "爱范儿·未来商业", "NVIDIA Developer Blog", "Google AI Blog",
    "Microsoft AI Blog", "DeepMind Blog", "OpenAI Blog", "Hugging Face Blog",
}

# Sources considered "Chinese media" for cross-perspective detection
CN_SOURCES = {"36氪", "爱范儿·未来商业", "机器之心", "腾讯研究院", "少数派", "InfoQ·架构与算力"}

STOPWORDS = set([
    'the','and','for','with','this','that','from','will','your','about','into',
    'over','under','their','they','them','been','were','have','has','had','not',
    'but','you','our','are','its','new','how','why','what','when','where'
])

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS multi_perspectives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_link TEXT UNIQUE,
            article_title TEXT,
            summary TEXT,
            cluster_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Migration: add cluster_json to existing tables
    try:
        c.execute('ALTER TABLE multi_perspectives ADD COLUMN cluster_json TEXT')
    except Exception:
        pass  # column already exists
    conn.commit()
    conn.close()

def _already_done(link):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT 1 FROM multi_perspectives WHERE article_link = ?', (link,))
    ok = c.fetchone() is not None
    conn.close()
    return ok

def _keywords(text, topk=12):
    words = re.findall(r"[A-Za-z]{3,}", (text or "").lower())
    words = [w for w in words if w not in STOPWORDS]
    return [w for w,_ in Counter(words).most_common(topk)]

def _cluster(seed, pool_rows, size=5):
    seed_text = (seed['article_title'] or '') + ' ' + (seed['raw_content'] or '')
    keys = _keywords(seed_text, topk=12)
    scored = []
    for r in pool_rows:
        text = ((r['article_title'] or '') + ' ' + (r['raw_content'] or '')).lower()
        score = sum(1 for k in keys if k in text)
        if score > 0:
            scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    cluster = [seed]
    for _, r in scored:
        if len(cluster) >= size:
            break
        if r['article_link'] == seed['article_link']:
            continue
        cluster.append(r)
    return cluster

def _eligible_seed_articles(limit=10):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT article_title, article_link, published_date, raw_content,
               criteria_score, criteria_reason, feed_name,
               COALESCE(content, raw_content, '') as best_content
        FROM articles
        WHERE criteria_score >= ?
        AND criteria_reason IS NOT NULL
        AND criteria_reason != ''
        ORDER BY published_date DESC
    ''', (FILTER_THRESHOLD,))
    rows = c.fetchall()
    conn.close()

    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENCY_DAYS)
    # Only long-form articles qualify: full text ≥500 chars, or summary ≥300 chars
    MIN_FULLTEXT = 500
    MIN_SUMMARY = 300
    seeds = []
    for row in rows:
        a = _row_to_article(row)
        if a['source'] not in ELIGIBLE_SOURCES:
            continue
        if _already_done(a['link']):
            continue
        best = row['best_content'] or ''
        raw = row['raw_content'] or ''
        is_fulltext = len(best) >= MIN_FULLTEXT and best != raw
        if not is_fulltext and len(raw) < MIN_SUMMARY:
            continue  # skip short news items
        if a['score'] >= EVERGREEN_SCORE or a['published'] >= cutoff:
            seeds.append(row)
        if len(seeds) >= limit:
            break
    return seeds

def _pool_rows(days=30):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''
        SELECT feed_name, article_title, article_link, published_date, raw_content,
               COALESCE(content, raw_content, '') as best_content
        FROM articles
        WHERE published_date >= datetime('now', ?)
    ''', (f"-{days} days",))
    rows = c.fetchall()
    conn.close()
    return rows

def _synthesize(cluster):
    _env = dotenv_values(os.path.join(os.path.dirname(__file__), '.env'))
    api_key = _env.get('DEEPSEEK_API_KEY') or _env.get('OPENAI_API_KEY')
    base_url = _env.get('OPENAI_BASE_URL', 'https://api.deepseek.com/v1')
    if not api_key:
        return None
    client = OpenAI(api_key=api_key, base_url=base_url)

    sources_in_cluster = [r['feed_name'] for r in cluster]
    has_cn = any(s in CN_SOURCES for s in sources_in_cluster)
    has_en = any(s not in CN_SOURCES for s in sources_in_cluster)

    context = "\n\n".join([
        f"[{r['feed_name']}] {r['article_title']}\n{(r['best_content'] or r['raw_content'] or '')[:1000]}"
        for r in cluster
    ])

    cross_media_section = ""
    if has_cn and has_en:
        cross_media_section = """
4) 中西方媒体视角差异：
   对比中文媒体与英文媒体在报道角度、关注重点、价值判断上的差异。
   （例如：中文媒体更关注___，而西方媒体更强调___）"""

    source_list = "、".join(sorted(set(sources_in_cluster)))
    learning_context = _load_learning_context()
    learning_section = ""
    if learning_context:
        learning_section = f"""
**与我们项目的关联**（可选，仅当有实质关联时输出一句，否则省略）：
对照以下我正在实践的技术领域，点出这篇故事与哪个具体项目经验直接相关，以及它能如何加深我的理解或指导未来决策。
{learning_context}
"""

    prompt = f"""你是一位资深科技分析师，你的读者是数据驱动的业务分析师（BA）——熟悉数据、与产品经理和算法工程师紧密协作，正在向战略视角成长。

以下是来自 {len(cluster)} 个媒体（{source_list}）关于同一话题的报道，请综合输出简洁的「故事全貌」：

**战略层面**（这件事意味着什么）：
宏观影响、行业格局变化、商业逻辑与竞争走向。3-5句，聚焦"why it matters"。

**执行层面**（我们应该怎么做）：
技术/架构选择、数据与指标体系影响、对 BA 与算法/产品团队协作方式的具体影响、值得关注的新工具或方法。3-5句，聚焦"so what for practitioners"。
{cross_media_section}{learning_section}
**延伸思考**（2-3条，面向 BA 成长，不要链接）

---
报道内容：
{context}""".strip()

    resp = client.chat.completions.create(
        model='deepseek-chat',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.4,
        max_tokens=1600
    )
    return resp.choices[0].message.content

def run(limit=10, pool_days=30):
    _init_db()
    seeds = _eligible_seed_articles(limit=limit)
    if not seeds:
        print("No eligible seeds.")
        return 0
    pool = _pool_rows(days=pool_days)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    created = 0
    for seed in seeds:
        cluster = _cluster(seed, pool, size=5)
        summary = _synthesize(cluster)
        if not summary:
            continue
        cluster_data = [
            {"title": r['article_title'], "source": r['feed_name'], "link": r['article_link']}
            for r in cluster
        ]
        c.execute('''
            INSERT OR IGNORE INTO multi_perspectives
            (article_link, article_title, summary, cluster_json)
            VALUES (?, ?, ?, ?)
        ''', (seed['article_link'], seed['article_title'], summary,
              json.dumps(cluster_data, ensure_ascii=False)))
        conn.commit()
        created += 1

    conn.close()
    print(f"Created {created} multi-perspective summaries.")
    return created

if __name__ == "__main__":
    run(limit=10, pool_days=30)
