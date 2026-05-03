#!/usr/bin/env python3
"""
jd_hot_fetcher.py — Fetch hottest discussions from V2EX and SSPAI.

V2EX: uses the official hot-topics JSON API (/api/topics/hot.json)
      Returns the 8 currently-hottest threads with reply counts + full content.

SSPAI: uses the article index API sorted by like_count, filters to last 14 days,
       re-ranks by engagement (likes×3 + comments), takes top 20.

Articles are upserted: new ones inserted, existing ones get raw_content updated
and criteria_score reset so the scorer re-evaluates with richer text.

Usage:
    python3 jd_hot_fetcher.py          # fetch both
    python3 jd_hot_fetcher.py --v2ex   # V2EX only
    python3 jd_hot_fetcher.py --sspai  # SSPAI only
"""

import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone, timedelta

import requests

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ai_007.db')

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json,*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def _upsert_article(conn, feed_name: str, feed_url: str, tier: int,
                    title: str, link: str, published: datetime,
                    raw_content: str) -> str:
    """Insert new article or refresh raw_content+reset score for existing one.
    Returns 'inserted' | 'updated' | 'skipped'."""
    c = conn.cursor()
    c.execute('SELECT id, raw_content FROM articles WHERE article_link = ?', (link,))
    row = c.fetchone()
    pub_str = published.strftime('%Y-%m-%dT%H:%M:%S')

    if row is None:
        c.execute("""
            INSERT INTO articles
                (feed_name, feed_url, feed_priority, article_title, article_link,
                 published_date, raw_content, signal_tier, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (feed_name, feed_url, f'tier{tier}', title, link,
              pub_str, raw_content[:5000], tier, datetime.now()))
        conn.commit()
        return 'inserted'

    # Update with richer content and reset score so re-evaluation runs
    existing_content = row[1] or ''
    if len(raw_content) > len(existing_content) + 20:
        c.execute("""
            UPDATE articles
            SET raw_content = ?, published_date = ?, last_seen = ?,
                criteria_score = NULL, criteria_reason = NULL
            WHERE article_link = ?
        """, (raw_content[:5000], pub_str, datetime.now(), link))
        conn.commit()
        return 'updated'

    c.execute('UPDATE articles SET last_seen = ? WHERE article_link = ?',
              (datetime.now(), link))
    conn.commit()
    return 'skipped'


# ── V2EX ─────────────────────────────────────────────────────────────────────

V2EX_HOT_API = 'https://www.v2ex.com/api/topics/hot.json'
V2EX_FEED_NAME = 'jd-v2ex'
V2EX_FEED_URL  = V2EX_HOT_API


def fetch_v2ex_hot() -> int:
    """Fetch the 8 currently-hottest V2EX threads via the official JSON API."""
    print('  📡 V2EX hot API…')
    try:
        resp = requests.get(V2EX_HOT_API, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        topics = resp.json()
    except Exception as e:
        print(f'     ❌ {e}')
        return 0

    if not isinstance(topics, list):
        print('     ❌ Unexpected response format')
        return 0

    conn = sqlite3.connect(DB_PATH)
    inserted = updated = skipped = 0

    for t in topics:
        title   = t.get('title', '').strip()
        link    = t.get('url', '').strip()
        replies = t.get('replies', 0)
        node    = t.get('node', {}).get('title', '') or t.get('node', {}).get('name', '')
        content = t.get('content', '') or ''
        member  = t.get('member', {}).get('username', '')
        # Use last_modified as published_date so active threads stay "recent"
        last_mod = t.get('last_modified') or t.get('created') or 0
        try:
            published = datetime.fromtimestamp(int(last_mod), tz=timezone.utc)
        except Exception:
            published = datetime.now(timezone.utc)

        if not title or not link:
            continue

        # Fetch top replies to give the AI opinion-range context
        topic_id = t.get('id')
        reply_texts = []
        if topic_id and replies > 0:
            try:
                rr = requests.get(
                    f'https://www.v2ex.com/api/replies/show.json?topic_id={topic_id}&p=1',
                    headers=HEADERS, timeout=10
                )
                if rr.status_code == 200:
                    reply_data = rr.json()
                    # Take top 20 replies by position (API returns chronological)
                    for rep in reply_data[:20]:
                        txt = rep.get('content_rendered') or rep.get('content') or ''
                        # Strip HTML tags
                        txt = re.sub(r'<[^>]+>', ' ', txt).strip()
                        txt = re.sub(r'\s+', ' ', txt)
                        if txt and len(txt) > 10:
                            reply_texts.append(txt[:300])
            except Exception:
                pass

        replies_block = ''
        if reply_texts:
            replies_block = '\n\n精选讨论观点:\n' + '\n'.join(f'• {r}' for r in reply_texts)

        raw = (
            f'[节点:{node}] [回复:{replies}条] [作者:{member}]\n\nOP内容: {content}{replies_block}'
        ).strip()

        result = _upsert_article(
            conn, V2EX_FEED_NAME, V2EX_FEED_URL, 2,
            title, link, published, raw
        )
        if result == 'inserted':
            inserted += 1
        elif result == 'updated':
            updated += 1
        else:
            skipped += 1

    conn.close()
    total = inserted + updated + skipped
    print(f'     ✅ {total} 条热帖: {inserted} 新增, {updated} 更新内容, {skipped} 已是最新')
    return inserted + updated


# ── SSPAI ─────────────────────────────────────────────────────────────────────

SSPAI_API     = 'https://sspai.com/api/v1/article/index/page/get'
SSPAI_FEED_NAME = 'jd-sspai'
SSPAI_FEED_URL  = SSPAI_API
SSPAI_DAYS    = 14   # only consider articles from last N days
SSPAI_TAKE    = 20   # keep top N by engagement after date filter


def fetch_sspai_hot() -> int:
    """Fetch SSPAI articles from last 14 days, ranked by like×3 + comment."""
    print('  📡 SSPAI hot API…')

    cutoff_ts = (datetime.now() - timedelta(days=SSPAI_DAYS)).timestamp()

    # Fetch multiple pages to build a pool of recent articles
    all_articles = []
    for offset in range(0, 90, 30):
        try:
            resp = requests.get(
                SSPAI_API,
                params={'offset': offset, 'limit': 30, 'sort': 'like_count'},
                headers=HEADERS,
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f'     ⚠️ page offset={offset}: {e}')
            break

        batch = data.get('data', [])
        if not batch:
            break
        all_articles.extend(batch)
        time.sleep(0.5)

    # Filter to recent window
    recent = [a for a in all_articles if a.get('released_time', 0) > cutoff_ts]

    if not recent:
        print(f'     ⚠️ 0 篇文章在过去{SSPAI_DAYS}天内')
        return 0

    # Rank by engagement
    recent.sort(key=lambda a: a['like_count'] * 3 + a['comment_count'], reverse=True)
    top = recent[:SSPAI_TAKE]

    conn = sqlite3.connect(DB_PATH)
    inserted = updated = skipped = 0

    for a in top:
        article_id = a['id']
        title   = a.get('title', '').strip()
        summary = a.get('summary', '') or ''
        likes   = a.get('like_count', 0)
        comments = a.get('comment_count', 0)
        author  = a.get('author', {}).get('nickname', '') if isinstance(a.get('author'), dict) else ''
        ts      = a.get('released_time', 0)
        link    = f'https://sspai.com/post/{article_id}'

        try:
            published = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        except Exception:
            published = datetime.now(timezone.utc)

        if not title or not article_id:
            continue

        # Enrich raw_content with engagement signals for better scoring
        raw = (
            f'[点赞:{likes}] [评论:{comments}] [作者:{author}]\n\n{summary}'
        ).strip()

        result = _upsert_article(
            conn, SSPAI_FEED_NAME, SSPAI_FEED_URL, 2,
            title, link, published, raw
        )
        if result == 'inserted':
            inserted += 1
        elif result == 'updated':
            updated += 1
        else:
            skipped += 1

    conn.close()
    total = inserted + updated + skipped
    print(f'     ✅ {total} 篇热文(过去{SSPAI_DAYS}天): {inserted} 新增, {updated} 更新内容, {skipped} 已是最新')
    return inserted + updated


# ── Lobste.rs ─────────────────────────────────────────────────────────────────

LOBSTERS_FEED_NAME = 'jd-lobsters-ai'
LOBSTERS_FEED_URL  = 'https://lobste.rs'
LOBSTERS_TAGS      = ['ai', 'vibecoding']
LOBSTERS_TAKE      = 20   # top N by score across both tags


def fetch_lobsters() -> int:
    """Fetch top Lobste.rs stories tagged ai/vibecoding with their comment threads."""
    print('  📡 Lobste.rs (ai + vibecoding)…')
    proxies = {'http': os.environ.get('HTTP_PROXY', ''),
               'https': os.environ.get('HTTPS_PROXY', '')} if os.environ.get('HTTP_PROXY') else None

    # Collect stories from both tags, deduplicate by short_id
    seen = {}
    for tag in LOBSTERS_TAGS:
        try:
            r = requests.get(f'https://lobste.rs/t/{tag}.json',
                             headers=HEADERS, timeout=15, proxies=proxies)
            r.raise_for_status()
            for s in r.json():
                sid = s.get('short_id')
                if sid and sid not in seen:
                    seen[sid] = s
        except Exception as e:
            print(f'     ⚠️ tag={tag}: {e}')
        time.sleep(0.5)

    if not seen:
        print('     ❌ no stories fetched')
        return 0

    # Sort by score desc, take top N
    stories = sorted(seen.values(), key=lambda s: s.get('score', 0), reverse=True)[:LOBSTERS_TAKE]

    conn = sqlite3.connect(DB_PATH)
    inserted = updated = skipped = 0

    for s in stories:
        short_id    = s['short_id']
        title       = s.get('title', '').strip()
        url         = s.get('url', '') or s.get('short_id_url', '')
        score       = s.get('score', 0)
        n_comments  = s.get('comment_count', 0)
        tags        = ', '.join(s.get('tags', []))
        description = s.get('description_plain', '') or ''
        submitter   = s.get('submitter_user', {}).get('username', '') if isinstance(s.get('submitter_user'), dict) else ''
        lobsters_url = s.get('short_id_url', f'https://lobste.rs/s/{short_id}')

        try:
            published = datetime.fromisoformat(s['created_at'].replace('Z', '+00:00'))
        except Exception:
            published = datetime.now(timezone.utc)

        if not title or not url:
            continue

        # Fetch story JSON for comments
        comment_texts = []
        if n_comments > 0:
            try:
                cr = requests.get(f'https://lobste.rs/s/{short_id}.json',
                                  headers=HEADERS, timeout=10, proxies=proxies)
                if cr.status_code == 200:
                    story_data = cr.json()
                    # Top-level comments only (depth=0), sorted by score desc
                    top_comments = sorted(
                        [c for c in story_data.get('comments', [])
                         if not c.get('is_deleted') and not c.get('is_moderated')
                         and c.get('depth', 0) == 0],
                        key=lambda c: c.get('score', 0),
                        reverse=True
                    )[:15]
                    for c in top_comments:
                        txt = (c.get('comment_plain') or '').strip()
                        if txt and len(txt) > 10:
                            comment_texts.append(txt[:300])
            except Exception:
                pass
            time.sleep(0.3)

        desc_block = f'\n\n描述: {description}' if description else ''
        comments_block = ''
        if comment_texts:
            comments_block = '\n\n精选讨论观点:\n' + '\n'.join(f'• {c}' for c in comment_texts)

        raw = (
            f'[tags:{tags}] [⬆{score}分] [💬{n_comments}评论] [作者:{submitter}]'
            f'{desc_block}'
            f'\n\n讨论: {lobsters_url}'
            f'{comments_block}'
        ).strip()

        result = _upsert_article(
            conn, LOBSTERS_FEED_NAME, LOBSTERS_FEED_URL, 1,
            title, url, published, raw
        )
        if result == 'inserted':
            inserted += 1
        elif result == 'updated':
            updated += 1
        else:
            skipped += 1

    conn.close()
    total = inserted + updated + skipped
    print(f'     ✅ {total} 条: {inserted} 新增, {updated} 更新内容, {skipped} 已是最新')
    return inserted + updated


# ── Show HN ───────────────────────────────────────────────────────────────────

SHOWHN_API      = 'https://hn.algolia.com/api/v1/search'
SHOWHN_FEED_NAME = 'jd-hn-showhn'
SHOWHN_FEED_URL  = 'https://news.ycombinator.com'
SHOWHN_DAYS     = 14
SHOWHN_TAKE     = 30


def fetch_showhn() -> int:
    """Fetch Show HN posts from last 14 days via Algolia, ranked by points."""
    print('  📡 Show HN (Algolia)…')
    import time as _time

    cutoff = int((_time.time()) - SHOWHN_DAYS * 86400)
    try:
        resp = requests.get(
            SHOWHN_API,
            params={
                'tags': 'show_hn',
                'hitsPerPage': 50,
                'numericFilters': f'created_at_i>{cutoff},num_comments>2',
            },
            headers={**HEADERS, 'Accept': 'application/json'},
            timeout=20,
        )
        resp.raise_for_status()
        hits = resp.json().get('hits', [])
    except Exception as e:
        print(f'     ❌ {e}')
        return 0

    # Sort by points descending, take top N
    hits.sort(key=lambda h: h.get('points', 0) or 0, reverse=True)
    hits = hits[:SHOWHN_TAKE]

    conn = sqlite3.connect(DB_PATH)
    inserted = updated = skipped = 0

    for h in hits:
        title    = (h.get('title') or '').strip()
        link     = h.get('url') or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        hn_link  = f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        points   = h.get('points', 0) or 0
        comments = h.get('num_comments', 0) or 0
        author   = h.get('author', '')
        ts       = h.get('created_at_i', 0)

        if not title:
            continue

        try:
            published = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        except Exception:
            published = datetime.now(timezone.utc)

        raw = (
            f'[Show HN] [👍{points}分] [💬{comments}评论] [作者:{author}]\n\n'
            f'讨论链接: {hn_link}\n\n'
            f'{title}'
        )

        result = _upsert_article(
            conn, SHOWHN_FEED_NAME, SHOWHN_FEED_URL, 2,
            title, link, published, raw
        )
        if result == 'inserted':
            inserted += 1
        elif result == 'updated':
            updated += 1
        else:
            skipped += 1

    conn.close()
    total = inserted + updated + skipped
    print(f'     ✅ {total} 条Show HN (过去{SHOWHN_DAYS}天，按points排序): {inserted} 新增, {updated} 更新, {skipped} 跳过')
    return inserted + updated


# ── Reddit ────────────────────────────────────────────────────────────────────

REDDIT_SUBREDDITS = [
    ('jd-reddit-localllama', 'LocalLLaMA',      1),
    ('jd-reddit-ml',         'MachineLearning',  2),
    ('jd-reddit-artificial', 'artificial',       2),
]
REDDIT_TAKE = 15   # top N per subreddit by score
REDDIT_DAYS = 7

def fetch_reddit_hot() -> int:
    """Fetch top posts from AI subreddits via Reddit JSON API, with top comments."""
    proxies = {'http': os.environ.get('HTTP_PROXY', ''),
               'https': os.environ.get('HTTPS_PROXY', '')} if os.environ.get('HTTP_PROXY') else None
    headers = {**HEADERS, 'User-Agent': 'jd-intel-bot/1.0 (research aggregator)'}
    conn = sqlite3.connect(DB_PATH)
    total_ins = total_upd = 0

    for feed_name, subreddit, tier in REDDIT_SUBREDDITS:
        print(f'  📡 Reddit r/{subreddit}…')
        try:
            r = requests.get(
                f'https://www.reddit.com/r/{subreddit}/top.json',
                params={'t': 'week', 'limit': 50},
                headers=headers, timeout=15, proxies=proxies)
            r.raise_for_status()
            posts = r.json()['data']['children']
        except Exception as e:
            print(f'     ❌ {e}')
            continue

        # Filter to last N days, sort by score
        cutoff = datetime.now(timezone.utc) - timedelta(days=REDDIT_DAYS)
        posts = [p['data'] for p in posts
                 if datetime.fromtimestamp(p['data']['created_utc'], tz=timezone.utc) > cutoff]
        posts.sort(key=lambda p: p.get('score', 0), reverse=True)
        posts = posts[:REDDIT_TAKE]

        inserted = updated = 0
        for p in posts:
            title     = (p.get('title') or '').strip()
            permalink = p.get('permalink', '')
            link      = f"https://www.reddit.com{permalink}"
            score     = p.get('score', 0)
            n_comments= p.get('num_comments', 0)
            selftext  = (p.get('selftext') or '')[:800]
            author    = p.get('author', '')
            flair     = p.get('link_flair_text') or ''
            ts        = p.get('created_utc', 0)
            ext_url   = p.get('url', '') if not p.get('is_self') else link

            if not title:
                continue
            try:
                published = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            except Exception:
                published = datetime.now(timezone.utc)

            # Fetch top comments
            comment_texts = []
            try:
                cr = requests.get(
                    f'https://www.reddit.com{permalink}.json',
                    params={'limit': 10, 'depth': 1, 'sort': 'top'},
                    headers=headers, timeout=10, proxies=proxies)
                if cr.status_code == 200:
                    comment_data = cr.json()
                    if len(comment_data) > 1:
                        for c in comment_data[1]['data']['children'][:10]:
                            body = (c['data'].get('body') or '').strip()
                            if body and body != '[deleted]' and len(body) > 20:
                                comment_texts.append(body[:300])
            except Exception:
                pass
            time.sleep(0.5)

            flair_tag = f'[{flair}] ' if flair else ''
            self_block = f'\n\nOP内容: {selftext}' if selftext else ''
            comments_block = ''
            if comment_texts:
                comments_block = '\n\n精选讨论观点:\n' + '\n'.join(f'• {c}' for c in comment_texts)

            raw = (
                f'[r/{subreddit}] {flair_tag}[⬆{score}分] [💬{n_comments}评论] [作者:u/{author}]'
                f'{self_block}{comments_block}'
            ).strip()

            result = _upsert_article(conn, feed_name, f'https://www.reddit.com/r/{subreddit}',
                                     tier, title, ext_url, published, raw)
            if result == 'inserted': inserted += 1
            elif result == 'updated': updated += 1

        total_ins += inserted
        total_upd += updated
        print(f'     ✅ {len(posts)} 帖: {inserted} 新增, {updated} 更新')
        time.sleep(1)

    conn.close()
    return total_ins + total_upd


# ── dev.to ────────────────────────────────────────────────────────────────────

DEVTO_FEED_NAME = 'jd-devto-ai'
DEVTO_FEED_URL  = 'https://dev.to'
DEVTO_TAKE      = 20

def fetch_devto_hot() -> int:
    """Fetch top dev.to AI articles by reactions via public API."""
    print('  📡 dev.to top AI articles…')
    proxies = {'http': os.environ.get('HTTP_PROXY', ''),
               'https': os.environ.get('HTTPS_PROXY', '')} if os.environ.get('HTTP_PROXY') else None
    try:
        r = requests.get('https://dev.to/api/articles',
            params={'tag': 'ai', 'top': 7, 'per_page': 30},
            headers={**HEADERS, 'Accept': 'application/json'},
            timeout=15, proxies=proxies)
        r.raise_for_status()
        articles = r.json()
    except Exception as e:
        print(f'     ❌ {e}')
        return 0

    # Sort by reactions + comments
    articles.sort(key=lambda a: a.get('positive_reactions_count', 0) * 2 + a.get('comments_count', 0), reverse=True)
    articles = articles[:DEVTO_TAKE]

    conn = sqlite3.connect(DB_PATH)
    inserted = updated = 0

    for a in articles:
        title    = (a.get('title') or '').strip()
        link     = a.get('url', '')
        reactions= a.get('positive_reactions_count', 0)
        comments = a.get('comments_count', 0)
        desc     = (a.get('description') or '')[:500]
        author   = (a.get('user') or {}).get('name', '')
        tags     = ', '.join(a.get('tag_list') or [])
        pub_str  = a.get('published_at') or a.get('created_at') or ''

        if not title or not link:
            continue
        try:
            published = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
        except Exception:
            published = datetime.now(timezone.utc)

        raw = (
            f'[dev.to] [❤{reactions}赞] [💬{comments}评论] [作者:{author}] [tags:{tags}]\n\n{desc}'
        ).strip()

        result = _upsert_article(conn, DEVTO_FEED_NAME, DEVTO_FEED_URL, 2,
                                 title, link, published, raw)
        if result == 'inserted': inserted += 1
        elif result == 'updated': updated += 1

    conn.close()
    print(f'     ✅ {len(articles)} 篇: {inserted} 新增, {updated} 更新')
    return inserted + updated


# ── HuggingFace Blog upvote enrichment ───────────────────────────────────────

HF_FEED_NAME = 'jd-huggingface-blog'
HF_BLOG_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,*/*',
    'Accept-Language': 'en-US,en;q=0.9',
}


def fetch_hf_upvotes() -> int:
    """Enrich HuggingFace Blog articles with upvote counts + page description.

    Reads articles from the last 30 days that don't yet have an upvote tag,
    fetches each page, extracts upvote count + og:description meta,
    builds a rich raw_content, and resets criteria_score for re-evaluation.
    Returns the number of articles updated.
    """
    print('  📡 HuggingFace Blog (enriching upvotes + descriptions)...')
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT id, article_title, article_link, raw_content
        FROM articles
        WHERE feed_name = ?
          AND published_date >= date('now', '-30 days')
        ORDER BY published_date DESC
        LIMIT 50
    """, (HF_FEED_NAME,)).fetchall()

    updated = 0
    for row in rows:
        art_id, title, link, raw = row
        raw = raw or ''

        # Already enriched with upvote tag and meaningful content — skip
        if '👍' in raw and len(raw) > 80:
            continue

        try:
            resp = requests.get(link, headers=HF_BLOG_HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            print(f'     ⚠️  {link[:60]}: {e}')
            time.sleep(0.5)
            continue

        html = resp.text

        # Extract upvote count
        m = re.search(r'upvotes&quot;:(\d+)', html)
        upvotes = int(m.group(1)) if m else 0

        # Extract og:description for scoring context
        m2 = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']{10,600})["\']', html)
        if not m2:
            m2 = re.search(r'<meta[^>]+content=["\']([^"\']{10,600})["\'][^>]+property=["\']og:description["\']', html)
        desc = m2.group(1).strip() if m2 else ''

        new_raw = f'[👍{upvotes}赞] {title}\n\n{desc}'.strip()[:5000]

        conn.execute("""
            UPDATE articles
            SET raw_content = ?, criteria_score = NULL, criteria_reason = NULL
            WHERE id = ?
        """, (new_raw, art_id))
        conn.commit()
        updated += 1
        time.sleep(0.4)   # be gentle with HF servers

    conn.close()
    print(f'     ✅ 更新了 {updated} 篇 HuggingFace 文章的点赞数和摘要')
    return updated


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    flags = set(sys.argv[1:])
    run_all = not flags

    print('=' * 50)
    print('🔥 JD热帖抓取')
    print('=' * 50)

    total = 0
    if run_all or '--v2ex'     in flags: total += fetch_v2ex_hot()
    if run_all or '--sspai'    in flags: total += fetch_sspai_hot()
    if run_all or '--showhn'   in flags: total += fetch_showhn()
    if run_all or '--lobsters' in flags: total += fetch_lobsters()
    if run_all or '--reddit'   in flags: total += fetch_reddit_hot()
    if run_all or '--devto'    in flags: total += fetch_devto_hot()
    if run_all or '--hf'       in flags: total += fetch_hf_upvotes()

    print(f'\n📦 完成，共更新 {total} 篇\n')
