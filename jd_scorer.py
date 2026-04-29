#!/usr/bin/env python3
"""
jd_scorer.py — DeepSeek-based scoring engine for JD retail AI intelligence.

Scoring rules, org chart, and domain taxonomy live in:
  jd_scoring_rules.md   — PMF framework, team routing rules, 14 domains, output spec
  jd_leadership_voice.md — Raw first-hand words from CTO/President (memos, chats, meeting notes)

Edit those markdown files directly to update scoring logic — no code change needed.

Bonus: arXiv papers with a GitHub repo ≥500 stars get +10 (capped at 100).
"""

import os
import re
import json
import time
import sqlite3
import requests
from dotenv import load_dotenv
from openai import OpenAI

_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(_env_path, override=True)

DB_PATH   = os.path.join(os.path.dirname(__file__), 'data', 'ai_rss.db')
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL     = "deepseek-chat"

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1"),
)


# ── Context loaders (re-read from disk each scoring run so edits take effect) ──

def _load_scoring_rules() -> str:
    path = os.path.join(_BASE_DIR, 'jd_scoring_rules.md')
    with open(path, 'r', encoding='utf-8') as f:
        return f.read().strip()

def _load_leadership_voice() -> str:
    path = os.path.join(_BASE_DIR, 'jd_leadership_voice.md')
    if not os.path.exists(path):
        return ""
    content = open(path, 'r', encoding='utf-8').read().strip()
    # Strip comment lines (<!-- ... -->) before injecting
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL).strip()
    return content

# ── Prompt templates (stable structure; content loaded from .md files at runtime) ──

SCORING_PROMPT = """{scoring_rules}

{leadership_block}

当前日期：{today}
文章发布距今：{age_days}天（约{age_months}个月）

{corroborating_block}

文章信息：
标题: {title}
来源: {source_label}
层级: Tier {tier}
摘要: {summary}
{criteria_block}
"""

TEAM_ROUTING_PROMPT = """{scoring_rules}

你的任务是：仅根据上方的情报分配引擎规则和团队列表，判断以下文章应路由给哪些团队。
严格输出JSON，不加任何其他内容：
{{"primary_teams": ["团队名1"], "cc_teams": ["团队名2", "团队名3"]}}

文章: {title}
来源: {source_label}
摘要: {summary}
"""


def _extract_github_repo(text: str) -> str | None:
    m = re.search(r'github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)', text or '')
    return m.group(1) if m else None


def _get_github_stars(repo: str) -> int:
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}", headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get("stargazers_count", 0)
    except Exception:
        pass
    return 0


def _call_llm(prompt: str, max_tokens: int = 512, _retry: bool = True) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.choices[0].message.content
    if not content:
        # DeepSeek occasionally returns None/empty on content-sensitive titles.
        # Retry once with a stripped-down prompt (title + source only).
        if _retry:
            short = prompt[-800:] if len(prompt) > 800 else prompt
            return _call_llm(short, max_tokens=max_tokens, _retry=False)
        return ''
    raw = content.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return raw


# ── Semantic embedding model (lazy-loaded) ──────────────────────────────────
_embedding_model = None

def _get_embedding_model():
    """Lazy-load paraphrase-multilingual-MiniLM-L12-v2 (handles CN+EN, 384-dim)."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    return _embedding_model


def _get_embedding(text: str) -> list[float]:
    """Return a normalized 384-dim embedding vector for the given text."""
    model = _get_embedding_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def _ensure_embedding_column(db_path: str = DB_PATH):
    """Add `embedding` TEXT column to articles if it doesn't exist yet."""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("ALTER TABLE articles ADD COLUMN embedding TEXT")
        conn.commit()
        conn.close()
    except Exception:
        pass   # column already exists — silently ignore


# ── Cross-article corroboration (semantic) ───────────────────────────────────

def find_corroborating_articles(title: str, feed_name: str,
                                 published_date: str = "",
                                 db_path: str = DB_PATH,
                                 window_days: int = 60,
                                 max_results: int = 5) -> list[dict]:
    """
    Semantic-embedding-based cross-article corroboration lookup.

    Uses sentence-transformers cosine similarity on stored title embeddings.
    Similarity thresholds:
      ≥ 0.65  →  same topic  (potential corroboration)
      ≥ 0.92  →  too similar (likely same story retold — no bonus)

    Returns a list of dicts: {title, feed_name, score, similarity}
    Only considers articles that already have a stored embedding and criteria_score.
    """
    import numpy as np

    try:
        target_emb = _get_embedding(title)
    except Exception:
        return []

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('''
            SELECT article_title, feed_name, published_date, criteria_score, embedding
            FROM articles
            WHERE feed_name != ?
              AND criteria_score IS NOT NULL
              AND published_date IS NOT NULL
              AND embedding IS NOT NULL
            ORDER BY published_date DESC
            LIMIT 2000
        ''', (feed_name,))
        candidates = c.fetchall()
        conn.close()
    except Exception:
        return []

    from datetime import datetime, timezone
    try:
        target_date = datetime.fromisoformat(
            (published_date or datetime.now(timezone.utc).isoformat()).replace('Z', '+00:00')
        )
        if target_date.tzinfo is None:
            target_date = target_date.replace(tzinfo=timezone.utc)
    except Exception:
        target_date = datetime.now(timezone.utc)

    target_arr = np.array(target_emb, dtype=np.float32)
    scored = []

    for row in candidates:
        # Time window filter
        try:
            pub = datetime.fromisoformat(row['published_date'].replace('Z', '+00:00'))
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if abs((target_date - pub).days) > window_days:
                continue
        except Exception:
            continue

        # Cosine similarity (vectors are pre-normalized → dot product = cosine sim)
        try:
            emb = json.loads(row['embedding'])
            sim = float(np.dot(target_arr, np.array(emb, dtype=np.float32)))
        except Exception:
            continue

        if sim < 0.65:
            continue   # not same topic
        if sim > 0.92:
            continue   # too similar — likely same story, no convergence bonus

        score = row['criteria_score']
        if score is None:
            continue

        scored.append({
            'title':      row['article_title'],
            'feed_name':  row['feed_name'],
            'score':      score,
            'similarity': round(sim, 3),
        })

    # Return top N by descending similarity
    scored.sort(key=lambda x: x['similarity'], reverse=True)
    return scored[:max_results]


def _format_corroborating_block(articles: list[dict]) -> str:
    """Format corroborating articles into a prompt context block."""
    if not articles:
        return ""
    lines = ["【数据库中已发现的同主题独立信源文章（来自不同来源，供判断信号收敛性）】"]
    for a in articles:
        lines.append(
            f"  · [{a['feed_name']}] {a['title']} "
            f"（情报分：{a['score']}，语义相似度：{a['similarity']}）"
        )
    lines.append(
        "收敛加分说明：若上述文章与本文从不同角度印证同一趋势（观点互补、相互强化）→ convergence给高分；"
        "若内容实质相同（同一消息的不同转载）→ 不视为收敛信号，convergence不加分。"
    )
    return "\n".join(lines)


def _article_age_days(published_date_str: str) -> int:
    """Return article age in days. Returns 0 if date unparseable."""
    if not published_date_str:
        return 0
    try:
        from datetime import datetime, timezone
        pub = datetime.fromisoformat(published_date_str.replace('Z', '+00:00'))
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - pub).days)
    except Exception:
        return 0


def _hard_novelty_cap(age_days: int) -> int | None:
    """Return a hard cap on novelty score (max 25 in new schema). None = no cap."""
    if age_days > 730:   # > 2 years
        return 2
    if age_days > 365:   # 1–2 years
        return 6
    if age_days > 180:   # 6–12 months
        return 13
    return None          # < 6 months: let LLM decide freely


def score_article(title: str, summary: str, source_label: str, tier: int,
                  is_arxiv: bool = False, source_criteria: str = "",
                  published_date: str = "", feed_name: str = "") -> dict:
    import re as _re
    from datetime import datetime, timezone

    # ── Twitter/nitter retweet detection ─────────────────────────────────
    # Nitter titles for RTs look like: "RT by @karpathy: [original text]"
    # Pure RTs (no added comment) carry endorsement signal but zero original analysis.
    # We detect them and cap novelty at 8 + add an endorsement note for the LLM.
    is_retweet = False
    rt_endorser = ""
    rt_note = ""
    _rt_match = _re.match(r'^RT by @(\w+):\s*', title or "")
    if _rt_match:
        is_retweet = True
        rt_endorser = _rt_match.group(1)
        # Strip the "RT by @X: " prefix so scorer sees clean content
        title = title[_rt_match.end():]
        rt_note = (f"\n【注意：这是 @{rt_endorser} 的转推(RT)，无原创评论。"
                   f"novelty分请给5-12分（转推本身没有新分析），"
                   f"但来源层级应反映 @{rt_endorser} 选择转发这条内容本身的背书价值。】")
    # ─────────────────────────────────────────────────────────────────────

    age_days = _article_age_days(published_date)
    age_months = age_days // 30
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    # ── Cross-article corroboration lookup ───────────────────────────────
    corroborating = find_corroborating_articles(
        title=title,
        feed_name=feed_name or source_label,
        published_date=published_date,
    )
    corroborating_block = _format_corroborating_block(corroborating)
    if corroborating:
        print(f"    🔗 找到 {len(corroborating)} 篇同主题独立文章：{[a['feed_name'] for a in corroborating]}")
    # ─────────────────────────────────────────────────────────────────────

    criteria_block = f"\n【本来源专属过滤规则】{source_criteria}" if source_criteria else ""
    if rt_note:
        criteria_block += rt_note

    # ── Manual signal type scoring overrides ─────────────────────────────
    if feed_name == 'jd-manual-community':
        criteria_block += (
            "\n【信号类型：社区信号（Discord/Reddit/HN/微信群）】"
            "这是从在线社区或讨论帖提炼的情报，非正式发表文章。"
            "novelty分请给5-15分（社区帖本身无学术或新闻价值），"
            "但如果内容包含第一手实测数据、内测体验或工程师的直接观察，"
            "relevance可给满分。请特别关注'我测试了…''刚拿到内测…''我们在生产环境用了…'等语言。"
        )
    elif feed_name == 'jd-manual-report':
        criteria_block += (
            "\n【信号类型：内部报告/会议纪要】"
            "这是内部一手文件（竞品调研/战略备忘录/会议纪要），非公开发表内容。"
            "relevance权重×1.3（内部一手信息溢价），"
            "source_tier按内容质量而非媒体品牌评分（内部文件可给Tier1待遇）。"
            "novelty按内容新鲜程度正常评分，不因来源是内部文件而压低。"
        )

    # Load external context files — re-read each run so edits take effect immediately
    scoring_rules   = _load_scoring_rules()
    leadership_voice = _load_leadership_voice()
    leadership_block = (
        "【当前管理层战略关注点 — 请在判断相关性时参考，从以下原话中自行提炼优先级信号】\n"
        + leadership_voice
    ) if leadership_voice else ""

    prompt = (SCORING_PROMPT
              .replace("{scoring_rules}", scoring_rules)
              .replace("{leadership_block}", leadership_block)
              .replace("{today}", today_str)
              .replace("{age_days}", str(age_days))
              .replace("{age_months}", str(age_months))
              .replace("{corroborating_block}", corroborating_block)
              .replace("{title}", title)
              .replace("{source_label}", source_label)
              .replace("{tier}", str(tier))
              .replace("{summary}", (summary or "")[:1500])
              .replace("{criteria_block}", criteria_block))

    github_bonus = 0
    github_note = ""
    if is_arxiv:
        combined = f"{title} {summary or ''}"
        repo = _extract_github_repo(combined)
        if repo:
            stars = _get_github_stars(repo)
            if stars >= 500:
                github_bonus = 10
                github_note = f" [GitHub: {repo} ⭐{stars:,} +{github_bonus}分]"
            elif stars > 0:
                github_note = f" [GitHub: {repo} ⭐{stars:,}]"

    try:
        raw = _call_llm(prompt, max_tokens=600)
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError(f"LLM returned non-dict JSON: {type(result).__name__}")
    except Exception as e:
        print(f"    ⚠️ 打分失败: {e}")
        result = {
            "source_tier": 8, "novelty": 8, "relevance": 10, "convergence": 4,
            "total": 30, "primary_teams": ["产品架构/技术架构"], "cc_teams": [],
            "reason": "打分失败，使用默认分数", "action_note": ""
        }

    result.setdefault("source_tier", 5)
    result.setdefault("novelty", 10)
    result.setdefault("relevance", 10)
    result.setdefault("convergence", 5)
    result.setdefault("total", 30)
    result.setdefault("reason", "")
    result.setdefault("primary_teams", ["产品架构/技术架构"])
    result.setdefault("cc_teams", [])
    result.setdefault("action_note", "")
    if result.get("domain") not in (
        "基础通讯","社交社区","内容直播","智能零售","交易服务平台","广告营销",
        "金融与支付","物流与供应链","具身智能与机器人","能源与可持续发展",
        "医疗健康","消费电子与智能硬件","跨语言与全球化","汽车与出行服务"
    ):
        result["domain"] = None
    result["github_bonus"] = github_bonus

    # Store corroborating article references (titles + feeds) for UI display
    if corroborating:
        result["corroborating"] = [
            {"feed": a["feed_name"], "title": a["title"], "score": a["score"]}
            for a in corroborating
        ]

    # Coerce all numeric fields from LLM to int (LLM sometimes returns strings)
    for _f in ("total", "source_tier", "novelty", "relevance", "convergence"):
        if _f in result:
            try:
                result[_f] = int(result[_f])
            except (TypeError, ValueError):
                result[_f] = 0

    # Hard cap for pure retweets: novelty ≤ 12 regardless of LLM
    if is_retweet and result.get("novelty", 0) > 12:
        excess = result["novelty"] - 12
        result["novelty"] = 12
        result["total"] = max(0, result.get("total", 0) - excess)
        result["reason"] = f"[转推(RT)，无原创评论，新鲜度上限12分] " + result.get("reason", "")

    # Hard cap for community signals: novelty ≤ 15 unless content has first-person evidence markers
    if feed_name == 'jd-manual-community':
        evidence_markers = ['测试', '实测', '内测', '生产环境', '部署', 'benchmark', '我们用', '我发现']
        summary_lower = (summary or "").lower()
        has_evidence = any(m in summary_lower for m in evidence_markers)
        cap = 20 if has_evidence else 15
        if result.get("novelty", 0) > cap:
            excess = result["novelty"] - cap
            result["novelty"] = cap
            result["total"] = max(0, result.get("total", 0) - excess)
            result["reason"] = f"[社区信号，新鲜度上限{cap}分] " + result.get("reason", "")

    # Hard age cap: override LLM novelty if article is old
    novelty_cap = _hard_novelty_cap(age_days)
    if novelty_cap is not None and result.get("novelty", 0) > novelty_cap:
        original_novelty = result["novelty"]
        result["novelty"] = novelty_cap
        result["total"] = result.get("total", 0) - (original_novelty - novelty_cap)
        if age_days > 365:
            result["reason"] = f"[时效警告: 发布于{age_days}天前，新鲜度强制压至{novelty_cap}分] " + result.get("reason", "")

    result["total"] = min(100, max(0, result.get("total", 0) + github_bonus))
    if github_note:
        result["reason"] = result.get("reason", "") + github_note
    return result


def tag_teams_for_article(title: str, summary: str, source_label: str) -> dict:
    """Lightweight team routing — returns {primary_teams, cc_teams} for retroactive tagging."""
    prompt = (TEAM_ROUTING_PROMPT
              .replace("{scoring_rules}", _load_scoring_rules())
              .replace("{title}", title)
              .replace("{source_label}", source_label)
              .replace("{summary}", (summary or "")[:600]))
    try:
        raw = _call_llm(prompt, max_tokens=150)
        result = json.loads(raw)
        if isinstance(result, dict):
            return {
                "primary_teams": result.get("primary_teams", ["产品架构/技术架构"]),
                "cc_teams": result.get("cc_teams", []),
            }
    except Exception:
        pass
    return {"primary_teams": ["产品架构/技术架构"], "cc_teams": []}


def score_unscored_jd_articles(limit: int = 200):
    """Score all jd- articles that have no criteria_score yet."""
    from jd_config import JD_SOURCES
    source_map = {s["name"]: s for s in JD_SOURCES}

    _ensure_embedding_column()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT id, feed_name, article_title, raw_content, content, published_date
        FROM articles
        WHERE feed_name LIKE 'jd-%' AND criteria_score IS NULL
        ORDER BY published_date DESC LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    print(f"📊 待打分文章: {len(rows)} 篇")

    for i, row in enumerate(rows, 1):
        src = source_map.get(row["feed_name"], {})
        label = src.get("label", row["feed_name"])
        tier = src.get("tier", 2)
        is_arxiv = src.get("is_arxiv", False)
        summary = row["content"] or row["raw_content"] or ""

        # Strip any residual HTML from titles (e.g. Fierce Electronics stores <a> tags)
        import html as _html
        clean_title = re.sub(r'<[^>]+>', '', row["article_title"] or "")
        clean_title = _html.unescape(clean_title).strip() or row["article_title"]

        print(f"  [{i}/{len(rows)}] {clean_title[:60]}...")
        scores = score_article(
            title=clean_title, summary=summary,
            source_label=label, tier=tier,
            is_arxiv=is_arxiv, source_criteria=src.get("criteria", ""),
            published_date=row["published_date"] or "",
            feed_name=row["feed_name"],
        )

        criteria_json = json.dumps({
            "source_tier":  scores["source_tier"],
            "novelty":      scores["novelty"],
            "relevance":    scores["relevance"],
            "convergence":  scores["convergence"],
            "total":        scores.get("total", 0),
            "github_bonus": scores["github_bonus"],
            "corroborating": scores.get("corroborating", []),
            "primary_teams": scores.get("primary_teams", ["产品架构/技术架构"]),
            "cc_teams":     scores.get("cc_teams", []),
            "action_note":  scores.get("action_note", ""),
            "domain":       scores.get("domain"),
            "reason":       scores.get("reason", ""),
        }, ensure_ascii=False)

        # Compute and store semantic embedding for future corroboration lookups
        try:
            emb_json = json.dumps(_get_embedding(row["article_title"]), separators=(',', ':'))
        except Exception:
            emb_json = None

        c.execute("""
            UPDATE articles SET criteria_score=?, criteria_reason=?, criteria=?, signal_tier=?, embedding=?
            WHERE id=?
        """, (scores["total"], scores["reason"], criteria_json, tier, emb_json, row["id"]))
        conn.commit()
        p = scores.get("primary_teams", [])
        cc = scores.get("cc_teams", [])
        print(f"    ✅ {scores['total']}分 ⚡{p} 👁{cc} — {scores['reason'][:60]}")
        time.sleep(0.3)

    conn.close()
    print(f"\n✅ 打分完成，共处理 {len(rows)} 篇")


def retag_existing_articles(limit: int = 500):
    """Add primary_teams/cc_teams to already-scored articles."""
    from jd_config import JD_SOURCES
    source_map = {s["name"]: s for s in JD_SOURCES}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT id, feed_name, article_title, raw_content, criteria
        FROM articles
        WHERE feed_name LIKE 'jd-%'
          AND criteria_score IS NOT NULL
          AND (criteria NOT LIKE '%primary_teams%' OR criteria IS NULL)
        ORDER BY criteria_score DESC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    print(f"📊 待补充团队标签: {len(rows)} 篇")

    for i, row in enumerate(rows, 1):
        src = source_map.get(row["feed_name"], {})
        label = src.get("label", row["feed_name"])
        summary = row["raw_content"] or ""

        print(f"  [{i}/{len(rows)}] {row['article_title'][:55]}...")
        routing = tag_teams_for_article(row["article_title"], summary, label)

        try:
            bd = json.loads(row["criteria"] or "{}")
        except Exception:
            bd = {}
        bd.pop("relevant_teams", None)
        bd["primary_teams"] = routing["primary_teams"]
        bd["cc_teams"] = routing["cc_teams"]

        c.execute("UPDATE articles SET criteria=? WHERE id=?",
                  (json.dumps(bd, ensure_ascii=False), row["id"]))
        conn.commit()
        print(f"    ✅ ⚡{routing['primary_teams']} 👁{routing['cc_teams']}")
        time.sleep(0.2)

    conn.close()
    print(f"\n✅ 团队标签补充完成，共处理 {len(rows)} 篇")


DOMAIN_CLASSIFY_PROMPT = """你是一个行业领域分类器。根据文章标题和摘要，从下列14个业务领域中选出最匹配的一个。
若文章明显不属于任何一个领域（如纯基础科研/AI基础模型/通用技术），输出null。

领域列表（只能选其中之一，或null）：
基础通讯 — 通信协议、消息、5G、网络基础设施
社交社区 — 社交图谱、UGC、社区、虚拟经济
内容直播 — 内容创作、短视频、直播带货、创作者经济
智能零售 — 商品发现、选购、履约、逆向物流
交易服务平台 — M2M撮合、信任验证、交易促成、评价飞轮
广告营销 — 受众定向、创意、竞价、归因、CRM
金融与支付 — 支付通道、信贷、负债管理、保险
物流与供应链 — 仓储、路由、最后一公里、跨境、逆向
具身智能与机器人 — 感知、规划、物理执行、自主部署
能源与可持续发展 — 清洁能源、碳追踪、智能建筑、EV充电
医疗健康 — 健康监测、AI诊断、护理协调、预防
消费电子与智能硬件 — 硬件、OS/固件、生态应用、服务变现
跨语言与全球化 — 本地化、跨境电商、多语言AI、海外运营
汽车与出行服务 — EV硬件、车载OS、充电网络、出行平台

只输出JSON，不加任何其他内容：
{{"domain": "<领域名称或null>"}}

文章标题: {title}
摘要: {summary}
"""

_VALID_DOMAINS = {
    "基础通讯","社交社区","内容直播","智能零售","交易服务平台","广告营销",
    "金融与支付","物流与供应链","具身智能与机器人","能源与可持续发展",
    "医疗健康","消费电子与智能硬件","跨语言与全球化","汽车与出行服务"
}


def classify_domain(title: str, summary: str) -> str | None:
    prompt = DOMAIN_CLASSIFY_PROMPT.format(
        title=title, summary=(summary or "")[:500]
    )
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=30,
        )
        raw = resp.choices[0].message.content.strip()
        data = json.loads(re.search(r'\{.*\}', raw, re.S).group())
        d = data.get("domain")
        return d if d in _VALID_DOMAINS else None
    except Exception:
        return None


def retag_domains(limit: int = 600):
    """Backfill domain field for articles that don't have one yet."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT id, article_title, raw_content, criteria
        FROM articles
        WHERE feed_name LIKE 'jd-%'
          AND criteria IS NOT NULL
          AND criteria NOT LIKE '%"domain"%'
        ORDER BY criteria_score DESC NULLS LAST
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    print(f"🗂 待补充领域标签: {len(rows)} 篇")

    for i, row in enumerate(rows, 1):
        title = row["article_title"] or ""
        summary = row["raw_content"] or ""
        print(f"  [{i}/{len(rows)}] {title[:55]}...")
        domain = classify_domain(title, summary)

        try:
            bd = json.loads(row["criteria"] or "{}")
        except Exception:
            bd = {}
        bd["domain"] = domain
        c.execute("UPDATE articles SET criteria=? WHERE id=?",
                  (json.dumps(bd, ensure_ascii=False), row["id"]))
        conn.commit()
        print(f"    → {domain or '(无匹配领域)'}")
        time.sleep(0.15)

    conn.close()
    print(f"\n✅ 领域标签补充完成，共处理 {len(rows)} 篇")


if __name__ == "__main__":
    import sys
    if "--retag-domains" in sys.argv:
        retag_domains(limit=600)
    elif "--retag" in sys.argv:
        retag_existing_articles(limit=500)
    elif "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        lim = int(sys.argv[idx + 1])
        score_unscored_jd_articles(limit=lim)
    else:
        score_unscored_jd_articles(limit=200)
