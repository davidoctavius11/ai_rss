#!/usr/bin/env python3
"""
Podcast pipeline:
- Select up to N items per day (default 10) using priority scoring
- Skip origin podcasts (leave as RSS only)
- Generate script (single host or two host)
- Optionally generate audio via TTS
- Emit podcast RSS feed (podcast.xml)
"""

import os
import re
import json
import tempfile
import wave
import sqlite3
from datetime import datetime, timedelta, timezone

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

from app_ai_filtered import _row_to_article, RECENCY_DAYS, EVERGREEN_SCORE, FILTER_THRESHOLD
from generator import RSSGenerator

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ai_rss.db')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output', 'podcast')
SCRIPT_DIR = os.path.join(OUTPUT_DIR, 'scripts')
AUDIO_DIR = os.path.join(OUTPUT_DIR, 'audio')
PODCAST_FEED_PATH = os.path.join(OUTPUT_DIR, 'podcast.xml')

# Audio config
ENABLE_TTS = os.getenv("ENABLE_TTS", "1") == "1"
TTS_MODEL = os.getenv("TTS_MODEL", "tts-1")
TTS_VOICE = os.getenv("TTS_VOICE", "alloy")
TTS_FORMAT = os.getenv("TTS_FORMAT", "wav")
TTS_SPEED = float(os.getenv("TTS_SPEED", "1.0"))
PODCAST_AUDIO_BASE_URL = os.getenv("PODCAST_AUDIO_BASE_URL", "https://rss.borntofly.ai/podcast/audio/").rstrip("/") + "/"
PODCAST_FEED_URL = os.getenv("PODCAST_FEED_URL", "https://rss.borntofly.ai/podcast.xml")

# Selection rules
DAILY_CAP = 10
MIN_SCORE = FILTER_THRESHOLD

# Episode length: scale by score, capped 15-20 minutes
MIN_MINUTES = 15
MAX_MINUTES = 20

# Source categories
RESEARCH_SOURCES = {
    "Google Research Blog",
    "DeepMind Blog",
    "OpenAI Blog",
    "Hugging Face Blog",
    "Apple Machine Learning Research",
    "Salesforce AI Research Blog",
    "QwenLM Blog",
}

# Origin podcast sources: skip (leave as RSS only)
PODCAST_SOURCES = {
    "Farnam Street",
}

# Keyword signals
SYSTEM_ARCH_KEYWORDS = [
    "architecture", "system design", "scalability", "reliability",
    "latency", "throughput", "distributed", "microservice",
    "observability", "sre", "platform", "governance",
    "cost", "tradeoff", "migration", "resilience",
    "capex", "opex", "roi", "strategy", "roadmap",
    "operating model", "org", "decision", "alignment",
]

INFRA_KEYWORDS = [
    "infrastructure", "compute", "gpu", "data center", "cluster",
    "inference", "training", "deployment", "serving",
    "kubernetes", "cloud", "edge", "vector database",
]

MARKETING_KEYWORDS = [
    "sponsored", "press release", "announcement", "launch event",
    "partnership", "brand", "marketing", "promo",
]

def _contains_any(text, keywords):
    t = (text or "").lower()
    return any(k in t for k in keywords)

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS podcast_episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_link TEXT UNIQUE,
            article_title TEXT,
            episode_type TEXT,
            minutes INTEGER,
            score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            script_path TEXT,
            audio_path TEXT
        )
    ''')
    conn.commit()
    conn.close()

def _eligible_articles(days=1):
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
        ORDER BY published_date DESC, criteria_score DESC
    ''', (MIN_SCORE,))

    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENCY_DAYS)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    results = []
    for row in c.fetchall():
        a = _row_to_article(row)
        if a['published'] < since:
            continue
        if a['score'] >= EVERGREEN_SCORE or a['published'] >= cutoff:
            results.append(a)
    conn.close()
    return results

def _already_done(link):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT 1 FROM podcast_episodes WHERE article_link = ?', (link,))
    ok = c.fetchone() is not None
    conn.close()
    return ok

def _priority_score(article):
    # Base score
    score = (article['score'] or 0) / 10.0

    text = f"{article.get('title','')} {article.get('summary','')}"

    # Highest weight: system architect / CTO-CEO mindset
    if _contains_any(text, SYSTEM_ARCH_KEYWORDS):
        score += 10

    # Research & infra bonuses
    if article.get('source') in RESEARCH_SOURCES:
        score += 6
    if _contains_any(text, INFRA_KEYWORDS):
        score += 4

    # Length / depth proxy
    if article.get('summary') and len(article['summary']) > 2000:
        score += 3

    # Marketing penalty
    if _contains_any(text, MARKETING_KEYWORDS):
        score -= 4

    return score

def _episode_minutes(score):
    # Score range roughly 5-20; map to 15-20 minutes
    span = MAX_MINUTES - MIN_MINUTES
    scaled = MIN_MINUTES + min(1.0, max(0.0, (score - 5) / 15.0)) * span
    return int(round(scaled))

def _episode_type(article):
    if article.get('source') in RESEARCH_SOURCES:
        return "two-host"
    return "single-host"

def _should_skip(article):
    # Skip origin podcasts: leave as RSS only
    if article.get('source') in PODCAST_SOURCES:
        return True
    # Heuristic: title mentions podcast or episode
    title = (article.get('title') or "").lower()
    if "podcast" in title or "episode" in title:
        return True
    return False

def _ensure_dirs():
    os.makedirs(SCRIPT_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)

def _build_prompt(article, minutes, episode_type):
    role = "两位主持人对谈" if episode_type == "two-host" else "单人主持"
    length_hint = f"{minutes}分钟"
    target_chars = minutes * 360  # rough Chinese characters per minute
    prompt = f"""
请将以下内容改写成中文播客脚本（{role}），时长约{length_hint}（目标字数约{target_chars}字）。
要求：
1) 重点突出技术与商业目标的系统性视角（CTO/CEO视角）
2) 提供关键概念解释与简化类比
3) 清晰结构：开场 -> 关键点 -> 影响与取舍 -> 结论
4) 语气专业但易懂
5) 开头加一句“本音频由AI生成”

标题：{article.get('title')}
来源：{article.get('source')}
内容（摘要/全文片段）：
{article.get('summary')}
""".strip()
    return prompt

def _generate_script(prompt):
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key or OpenAI is None:
        return None
    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "你是播客撰稿人，擅长技术与商业结合的讲解。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=2200,
    )
    return resp.choices[0].message.content

def _split_text(text, max_chars=3500):
    # split by paragraphs then sentences to fit TTS limit
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    buf = ""
    for p in paras:
        if len(buf) + len(p) + 1 <= max_chars:
            buf = (buf + "\n\n" + p).strip()
        else:
            if buf:
                chunks.append(buf)
                buf = ""
            # if paragraph itself too long, split by sentence
            if len(p) > max_chars:
                sentences = re.split(r"(。|！|？|；|;|\.)", p)
                tmp = ""
                for s in sentences:
                    if not s:
                        continue
                    if len(tmp) + len(s) <= max_chars:
                        tmp += s
                    else:
                        if tmp:
                            chunks.append(tmp)
                        tmp = s
                if tmp:
                    chunks.append(tmp)
            else:
                buf = p
    if buf:
        chunks.append(buf)
    return chunks

def _tts_to_wav(text, out_path):
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key or OpenAI is None:
        return None
    client = OpenAI(api_key=api_key, base_url=base_url)
    chunks = _split_text(text, max_chars=3500)
    tmp_files = []
    try:
        for i, chunk in enumerate(chunks):
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            tmp.close()
            with client.audio.speech.with_streaming_response.create(
                model=TTS_MODEL,
                voice=TTS_VOICE,
                input=chunk,
                response_format=TTS_FORMAT,
                speed=TTS_SPEED,
            ) as response:
                response.stream_to_file(tmp.name)
            tmp_files.append(tmp.name)

        # concat wav chunks
        with wave.open(out_path, 'wb') as wf_out:
            for i, f in enumerate(tmp_files):
                with wave.open(f, 'rb') as wf_in:
                    if i == 0:
                        wf_out.setparams(wf_in.getparams())
                    wf_out.writeframes(wf_in.readframes(wf_in.getnframes()))
        return out_path
    finally:
        for f in tmp_files:
            try:
                os.unlink(f)
            except Exception:
                pass

def _save_script(article, minutes, episode_type, script_text):
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", article['title'].lower())[:60].strip("-")
    name = f"{article['published'].strftime('%Y%m%d')}-{slug}.txt"
    path = os.path.join(SCRIPT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(script_text)
    return path

def _register_episode(article, episode_type, minutes, score, script_path, audio_path=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO podcast_episodes
        (article_link, article_title, episode_type, minutes, score, script_path, audio_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        article['link'],
        article['title'],
        episode_type,
        minutes,
        score,
        script_path,
        audio_path,
    ))
    conn.commit()
    conn.close()

def _build_podcast_feed():
    # Only include episodes that have audio_path
    from feedgen.feed import FeedGenerator

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''
        SELECT article_title, article_link, created_at, audio_path, episode_type, minutes
        FROM podcast_episodes
        WHERE audio_path IS NOT NULL AND audio_path != ''
        ORDER BY created_at DESC
    ''')
    rows = c.fetchall()
    conn.close()

    fg = FeedGenerator()
    fg.title("AI RSS Podcast")
    fg.link(href=PODCAST_FEED_URL, rel='self')
    fg.description("AI RSS 播客（中文）")
    fg.language('zh-CN')

    for r in rows:
        fe = fg.add_entry()
        fe.title(r['article_title'])
        fe.link(href=r['article_link'])
        fe.pubDate(datetime.fromisoformat(r['created_at']))
        fe.description(f"{r['episode_type']} | {r['minutes']}分钟")

        audio_path = r['audio_path']
        filename = os.path.basename(audio_path)
        audio_url = PODCAST_AUDIO_BASE_URL + filename
        size = os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
        fe.enclosure(audio_url, str(size), "audio/wav")

    xml = fg.rss_str(pretty=True).decode('utf-8')
    with open(PODCAST_FEED_PATH, "w", encoding="utf-8") as f:
        f.write(xml)

def run(days=1):
    _init_db()
    _ensure_dirs()

    items = _eligible_articles(days=days)
    candidates = []
    for a in items:
        if _already_done(a['link']):
            continue
        if _should_skip(a):
            continue
        candidates.append(a)

    # score + sort
    scored = []
    for a in candidates:
        ps = _priority_score(a)
        scored.append((ps, a))
    scored.sort(key=lambda x: x[0], reverse=True)

    selected = scored[:DAILY_CAP]

    for ps, a in selected:
        minutes = _episode_minutes(ps)
        e_type = _episode_type(a)
        prompt = _build_prompt(a, minutes, e_type)
        script = _generate_script(prompt)
        if not script:
            # store prompt as placeholder for manual generation
            script = prompt
        script_path = _save_script(a, minutes, e_type, script)

        audio_path = None
        if ENABLE_TTS:
            slug = os.path.splitext(os.path.basename(script_path))[0]
            audio_path = os.path.join(AUDIO_DIR, f"{slug}.wav")
            try:
                _tts_to_wav(script, audio_path)
            except Exception:
                audio_path = None

        _register_episode(a, e_type, minutes, ps, script_path, audio_path=audio_path)

    _build_podcast_feed()

if __name__ == "__main__":
    run(days=1)
