#!/usr/bin/env python3
"""
全文抓取模块 - 解决RSS只有摘要的问题
使用多个备选方案，确保拿到完整正文
"""

import argparse
import os
import re
import sqlite3
import time
import requests
from bs4 import BeautifulSoup
from readability import Document
import trafilatura

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ai_rss.db')

def fetch_full_text(url, retry=2):
    """
    多策略全文抓取：
    1. trafilatura (最干净，专门提取正文)
    2. readability (备选)
    3. beautifulsoup 暴力提取 (兜底)
    """
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 策略1: trafilatura - 精度最高
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            if text and len(text) > 500:
                print(f"  ✅ trafilatura 成功: {len(text)} 字符")
                return text
    except Exception as e:
        print(f"  ⚠️ trafilatura 失败: {e}")
    
    # 策略2: readability - 通用性好
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        doc = Document(response.text)
        text = doc.summary()
        # 清理HTML标签
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text()
        if len(text) > 500:
            print(f"  ✅ readability 成功: {len(text)} 字符")
            return text
    except Exception as e:
        print(f"  ⚠️ readability 失败: {e}")
    
    # 策略3: 暴力提取 - 死马当活马医
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        # 移除脚本和样式
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        if len(text) > 500:
            print(f"  ✅ 暴力提取 成功: {len(text)} 字符")
            return text[:10000]  # 截断
    except Exception as e:
        print(f"  ⚠️ 暴力提取 失败: {e}")
    
    return None

def update_articles_with_fulltext(limit=50, force=False, feed_name=None, days=None):
    """
    为content为空或太短的文章补全全文
    force=True: 强制重新抓取
    feed_name: 仅处理指定源（精确匹配）
    days: 仅处理最近N天内的文章
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    where = ["article_link LIKE 'http%'"]
    params = []

    if not force:
        where.append("(content IS NULL OR length(content) < 200 OR fulltext_fetched = 0)")

    if feed_name:
        where.append("feed_name = ?")
        params.append(feed_name)

    if days is not None:
        where.append("published_date >= datetime('now', ?)")
        params.append(f"-{int(days)} days")

    sql = f'''
        SELECT id, article_title, article_link
        FROM articles
        WHERE {' AND '.join(where)}
        ORDER BY published_date DESC
        LIMIT ?
    '''
    params.append(limit)
    c.execute(sql, params)
    articles = c.fetchall()

    print(f"📄 发现 {len(articles)} 篇文章需要抓取全文")

    success_count = 0
    for article in articles:
        title = article['article_title'] or ''
        link = article['article_link']
        article_id = article['id']
        print(f"  抓取: {title[:50]}...")
        print(f"  链接: {link}")

        full_text = fetch_full_text(link)

        if full_text:
            c.execute(
                "UPDATE articles SET content = ?, fulltext_fetched = 1 WHERE id = ?",
                (full_text, article_id)
            )
            conn.commit()
            success_count += 1
            print(f"  ✅ 成功: {len(full_text)} 字符")
        else:
            c.execute(
                "UPDATE articles SET fulltext_fetched = 0 WHERE id = ?",
                (article_id,)
            )
            conn.commit()
            print(f"  ❌ 失败: 无法抓取全文")

        time.sleep(1)  # 礼貌性延迟

    conn.close()
    print(f"✅ 全文抓取完成: {success_count}/{len(articles)} 成功")
    return success_count

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="全文抓取工具")
    parser.add_argument("--limit", type=int, default=20, help="最多处理多少篇")
    parser.add_argument("--force", action="store_true", help="强制重抓")
    parser.add_argument("--feed", type=str, default=None, help="仅处理指定源名称")
    parser.add_argument("--days", type=int, default=None, help="仅处理最近N天")
    args = parser.parse_args()

    update_articles_with_fulltext(
        limit=args.limit,
        force=args.force,
        feed_name=args.feed,
        days=args.days,
    )
