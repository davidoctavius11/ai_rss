#!/usr/bin/env python3
"""
Multi-perspective synthesis (cluster-based, CTO/CEO focused).
Generates and stores summaries to be appended in RSS descriptions.
"""

import os
import re
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from openai import OpenAI

from app_ai_filtered import _row_to_article, FILTER_THRESHOLD, RECENCY_DAYS, EVERGREEN_SCORE

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ai_rss.db')

# Sources eligible for multi-perspective synthesis
ELIGIBLE_SOURCES = {
    "TechCrunch",
    "36氪",
    "InfoQ·架构与算力",
    "The Verge Full Feed",
    "InfoQ Architecture (All)",
    "InfoQ Architecture Articles",
    "InfoQ Architecture News",
    "AWS Architecture Blog",
    "Cloudflare Changelog (Global)",
    "Cloudflare Changelog (Developer Platform)",
}

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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
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
               criteria_score, criteria_reason, feed_name
        FROM articles
        WHERE criteria_score >= ?
        AND criteria_reason IS NOT NULL
        AND criteria_reason != ''
        ORDER BY published_date DESC
    ''', (FILTER_THRESHOLD,))
    rows = c.fetchall()
    conn.close()

    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENCY_DAYS)
    seeds = []
    for row in rows:
        a = _row_to_article(row)
        if a['source'] not in ELIGIBLE_SOURCES:
            continue
        if _already_done(a['link']):
            continue
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
        SELECT feed_name, article_title, article_link, published_date, raw_content
        FROM articles
        WHERE published_date >= datetime('now', ?)
    ''', (f"-{days} days",))
    rows = c.fetchall()
    conn.close()
    return rows

def _synthesize(cluster):
    load_dotenv('.env')
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL')
    if not api_key:
        return None
    client = OpenAI(api_key=api_key, base_url=base_url)

    context = "\n\n".join([
        f"- {r['feed_name']}: {r['article_title']}\n  摘要: {(r['raw_content'] or '')[:800]}"
        for r in cluster
    ])
    prompt = f"""
你是CTO/CEO助手，请基于以下同主题文章，输出三视角总结（中文），每条3-5句：
1) 战略视角
2) 技术/架构视角
3) 风险/治理视角

然后输出【延伸阅读方向】（3-5条），要求：
- 以CTO/首席架构师/CEO视角为核心
- 关注商业目标、组织能力、系统架构、长期护城河
- 输出为短提示语，不要链接

文章：
{context}
""".strip()

    resp = client.chat.completions.create(
        model='deepseek-chat',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.4,
        max_tokens=1000
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
        c.execute('''
            INSERT OR IGNORE INTO multi_perspectives
            (article_link, article_title, summary)
            VALUES (?, ?, ?)
        ''', (seed['article_link'], seed['article_title'], summary))
        conn.commit()
        created += 1

    conn.close()
    print(f"Created {created} multi-perspective summaries.")
    return created

if __name__ == "__main__":
    run(limit=10, pool_days=30)
