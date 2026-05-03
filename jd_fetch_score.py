#!/usr/bin/env python3
"""
jd_fetch_score.py — One-shot fetch + score for JD retail AI intelligence demo.

Usage:
    python3 jd_fetch_score.py            # fetch all sources, then score
    python3 jd_fetch_score.py --score-only   # skip fetch, score unscored articles
    python3 jd_fetch_score.py --fetch-only   # fetch only, no scoring
"""

import sys
import os
import time
import sqlite3
import requests
import feedparser
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))
from jd_config import JD_SOURCES

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ai_007.db')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/xml,text/xml,application/rss+xml,*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def _clean_xml_bytes(data: bytes) -> bytes:
    return bytes(b for b in data if b in (9, 10, 13) or b >= 32)


def _parse_date(entry) -> datetime:
    for attr in ('published_parsed', 'updated_parsed'):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)


def fetch_source(source: dict, max_entries: int = 30) -> int:
    name = source["name"]
    url = source["url"]
    tier = source["tier"]

    # Twitter feeds: use syndication API (nitter.net is unreliable)
    if name.startswith('jd-twitter-') or name.startswith('jd-weibo-'):
        handle = name.split('-', 2)[2]  # jd-twitter-simonw → simonw
        from jd_twitter_fetcher import fetch_and_save as _tw_fetch
        return _tw_fetch(handle, name, tier=tier, count=50)

    # Feeds handled by jd_hot_fetcher — skip RSS fetch here
    if source.get('_fetch_via_hot_api') or name in ('jd-devto-ai', 'jd-hn-showhn', 'jd-lobsters-ai', 'jd-v2ex'):
        return 0

    print(f"  📡 {source['label']} ({url[:60]}...)" if len(url) > 60 else f"  📡 {source['label']} ({url})")

    # Reddit: let feedparser fetch directly — its User-Agent is accepted by Reddit
    if 'reddit.com' in url:
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                print(f"     ⚠️ 没有条目 (reddit)")
                return 0
        except Exception as e:
            print(f"     ❌ 抓取失败: {e}")
            return 0
    else:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"     ❌ 抓取失败: {e}")
            return 0
        content = resp.content
        feed = feedparser.parse(content)
        if feed.bozo:
            feed = feedparser.parse(_clean_xml_bytes(content))

    entries = feed.entries[:max_entries]
    if not entries:
        print(f"     ⚠️ 没有条目")
        return 0

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    new_count = 0

    for entry in entries:
        title = getattr(entry, 'title', '').strip()
        link = getattr(entry, 'link', '').strip()
        summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '') or ''
        published = _parse_date(entry)

        if not title or not link:
            continue

        try:
            c.execute("""
                INSERT INTO articles
                    (feed_name, feed_url, feed_priority, article_title, article_link,
                     published_date, raw_content, signal_tier)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, url, f"tier{tier}",
                title, link,
                published.strftime('%Y-%m-%dT%H:%M:%S'),
                summary[:5000],
                tier,
            ))
            conn.commit()
            new_count += 1
        except sqlite3.IntegrityError:
            pass  # duplicate link, skip

    conn.close()
    print(f"     ✅ 新增 {new_count} 篇")
    return new_count


def fetch_all() -> int:
    print("=" * 60)
    print(f"🚀 JD情报抓取 — {len(JD_SOURCES)} 个源")
    print("=" * 60)
    total = 0
    for src in JD_SOURCES:
        total += fetch_source(src, max_entries=20)
        time.sleep(1)
    print(f"\n📦 抓取完成，共新增 {total} 篇\n")
    return total


if __name__ == "__main__":
    fetch_only = "--fetch-only" in sys.argv
    score_only = "--score-only" in sys.argv

    if not score_only:
        fetch_all()

    if not fetch_only:
        from jd_scorer import score_unscored_jd_articles
        score_unscored_jd_articles(limit=200)
