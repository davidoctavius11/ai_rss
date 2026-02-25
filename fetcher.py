#!/usr/bin/env python3
"""
AI RSS 抓取模块 - 增量版
每次只抓取最新文章，避免重复和浪费
"""

import feedparser
import requests
from datetime import datetime
import time
import sqlite3
import os

# 过滤非法XML控制字符
def _clean_xml_bytes(data: bytes) -> bytes:
    return bytes(
        b for b in data
        if b in (9, 10, 13) or b >= 32
    )

# ========== 数据库配置 ==========
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ai_rss.db')

def init_db():
    """确保数据库和表存在"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_name TEXT,
            feed_url TEXT,
            feed_priority TEXT DEFAULT 'medium',
            article_title TEXT,
            article_link TEXT UNIQUE,
            published_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            content TEXT,
            raw_content TEXT,
            fulltext_fetched INTEGER DEFAULT 0,
            criteria TEXT,
            criteria_score REAL,
            criteria_reason TEXT,
            summary TEXT,
            is_read INTEGER DEFAULT 0
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_article_link ON articles(article_link)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_published_date ON articles(published_date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_feed_name ON articles(feed_name)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_last_seen ON articles(last_seen)')
    conn.commit()
    conn.close()

def get_latest_published_time(feed_name):
    """获取某个源最新的文章发布时间"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT MAX(published_date) FROM articles 
        WHERE feed_name = ? AND published_date IS NOT NULL
    ''', (feed_name,))
    result = c.fetchone()[0]
    conn.close()
    return result

def save_articles_to_db(articles_list, feed_name, feed_url, criteria=""):
    """保存文章列表到数据库（增量）"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    saved_count = 0
    now = datetime.now()
    
    for article in articles_list:
        try:
            # 先检查是否已存在
            c.execute('SELECT id FROM articles WHERE article_link = ?', (article.get('link', ''),))
            existing = c.fetchone()
            
            if existing:
                # 已存在，更新 last_seen
                c.execute('''
                    UPDATE articles 
                    SET last_seen = ? 
                    WHERE id = ?
                ''', (now, existing[0]))
            else:
                # 不存在，插入新文章
                c.execute('''
                    INSERT INTO articles 
                    (feed_name, feed_url, article_title, article_link, published_date, raw_content, criteria, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    feed_name,
                    feed_url,
                    article.get('title', '无标题'),
                    article.get('link', ''),
                    article.get('published', datetime.now()),
                    article.get('summary', '')[:2000],
                    criteria,
                    now
                ))
                saved_count += 1
                
        except Exception as e:
            print(f"    ⚠️ 保存失败: {e}")
    
    conn.commit()
    conn.close()
    return saved_count

# ========== RSS抓取核心（增量版）=========

def fetch_articles_from_feed(feed_url, feed_name, max_retries=3, max_entries=30):
    """
    增量抓取RSS源 - 只抓取最新文章
    
    参数:
        feed_url: RSS源的URL地址
        feed_name: 源的名字（用于日志输出）
        max_retries: 网络请求失败时的最大重试次数
        max_entries: 每次最多处理多少篇（防止某些源一次性推送太多）
    
    返回:
        新增文章数量
    """
    
    # 获取这个源最新的文章时间
    latest_time = get_latest_published_time(feed_name)
    if latest_time:
        print(f"  ├─ 📅 上次最新文章: {latest_time}")
    
    new_articles = []
    
    for attempt in range(max_retries):
        try:
            # 设置请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
            }
            
            print(f"  ├─ 抓取 {feed_name} (尝试 {attempt + 1}/{max_retries})...")
            response = requests.get(feed_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # 解析RSS（必要时清洗非法字符）
            content = response.content
            feed_data = feedparser.parse(content)
            if feed_data.bozo:
                print(f"  ├─ 警告: 解析有小问题，尝试清洗非法字符...")
                cleaned = _clean_xml_bytes(content)
                if cleaned != content:
                    feed_data = feedparser.parse(cleaned)
            
            if feed_data.bozo:
                print(f"  ├─ 警告: 解析仍有问题，但继续...")
            
            total_entries = len(feed_data.entries)
            print(f"  ├─ RSS包含 {total_entries} 篇文章")
            
            # 只处理最新的 max_entries 篇
            entries_to_process = feed_data.entries[:max_entries]
            
            # 提取文章信息，只保留比 latest_time 新的
            new_count = 0
            for entry in entries_to_process:
                # 处理发布时间
                published_time = None
                for time_field in ['published_parsed', 'updated_parsed', 'created_parsed']:
                    if hasattr(entry, time_field) and getattr(entry, time_field):
                        published_time = datetime.fromtimestamp(time.mktime(getattr(entry, time_field)))
                        break
                
                if not published_time:
                    published_time = datetime.now()
                
                # 增量判断：如果有上次时间，且这篇文章更旧，跳过
                if latest_time:
                    # 将latest_time字符串转换为datetime对象进行比较
                    try:
                        latest_dt = datetime.strptime(latest_time, '%Y-%m-%d %H:%M:%S')
                        if published_time <= latest_dt:
                            continue
                    except ValueError:
                        # 如果时间格式不匹配，跳过比较
                        pass
                
                # 构建文章字典
                article = {
                    'title': entry.get('title', '无标题'),
                    'link': entry.get('link', ''),
                    'published': published_time,
                    'summary': entry.get('summary', entry.get('description', ''))[:2000],
                }
                new_articles.append(article)
                new_count += 1
            
            print(f"  ├─ 🔍 发现 {new_count} 篇新文章")
            
            # 抓取成功，跳出重试循环
            break
            
        except requests.exceptions.Timeout:
            print(f"  ├─ 超时")
            if attempt < max_retries - 1:
                time.sleep(3)
        except requests.exceptions.RequestException as e:
            print(f"  ├─ 网络错误: {e}")
            break
        except Exception as e:
            print(f"  ├─ 解析错误: {e}")
            break
    
    # ========== 保存到数据库 ==========
    if new_articles:
        try:
            # 从config.py获取criteria
            try:
                from config import RSS_FEEDS
                criteria = ""
                for feed in RSS_FEEDS:
                    if feed['name'] == feed_name:
                        criteria = feed.get('criteria', '')
                        break
            except ImportError:
                criteria = ""
            
            # 保存到数据库
            saved = save_articles_to_db(new_articles, feed_name, feed_url, criteria)
            print(f"  ├─ 💾 新增 {saved} 篇")
            
        except Exception as e:
            print(f"  ├─ ⚠️ 数据库保存失败: {e}")
    else:
        print(f"  ├─ ✨ 没有新文章")
    
    return len(new_articles)


# ========== 全文抓取模块（增量感知）=========

def fetch_full_text_for_recent(limit=50, max_age_days=7):
    """
    为最近未抓取全文的文章补全正文
    只处理最近 max_age_days 天内的文章
    """
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 只处理最近的文章，避免抓取太旧的
    cutoff_date = datetime.now().timestamp() - (max_age_days * 24 * 3600)
    
    c.execute('''
        SELECT id, article_link, article_title, feed_name
        FROM articles 
        WHERE (content IS NULL OR content = '' OR fulltext_fetched = 0)
        AND article_link IS NOT NULL
        AND article_link != ''
        AND (published_date IS NULL OR strftime('%s', published_date) > ?)
        ORDER BY 
            CASE WHEN fulltext_fetched = -1 THEN 1 ELSE 0 END,
            published_date DESC 
        LIMIT ?
    ''', (cutoff_date, limit))
    
    articles = c.fetchall()
    
    if not articles:
        print(f"  ├─ 📄 没有需要抓取全文的文章")
        conn.close()
        return 0
    
    print(f"  ├─ 📄 需要抓取全文: {len(articles)} 篇")
    
    try:
        from bs4 import BeautifulSoup
        from readability import Document
        import trafilatura
    except ImportError:
        print(f"  ├─ ⚠️ 缺少依赖库")
        conn.close()
        return 0
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }
    
    success_count = 0
    for article_id, url, title, feed_name in articles:
        print(f"   抓取: {feed_name} - {title[:40]}...")
        
        full_text = None
        
        # 策略1: trafilatura
        try:
            downloaded = trafilatura.fetch_url(url, headers=headers)
            if downloaded:
                text = trafilatura.extract(downloaded, include_comments=False)
                if text and len(text) > 200:
                    full_text = text
        except Exception:
            pass
        
        # 策略2: readability
        if not full_text:
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                doc = Document(resp.text)
                soup = BeautifulSoup(doc.summary(), 'html.parser')
                text = soup.get_text()
                if len(text) > 200:
                    full_text = text
            except Exception:
                pass
        
        if full_text:
            c.execute('''
                UPDATE articles 
                SET content = ?, fulltext_fetched = 1 
                WHERE id = ?
            ''', (full_text[:30000], article_id))
            conn.commit()
            success_count += 1
            print(f"      ✅ 成功")
        else:
            c.execute('UPDATE articles SET fulltext_fetched = -1 WHERE id = ?', (article_id,))
            conn.commit()
            print(f"      ❌ 失败")
        
        time.sleep(1)
    
    conn.close()
    print(f"  ├─ ✅ 完成: {success_count}/{len(articles)}")
    return success_count


# ========== 清理旧文章（可选）=========

def cleanup_old_articles(days=30):
    """删除超过 days 天未出现的文章（即源已删除的旧文）"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    cutoff = datetime.now().timestamp() - (days * 24 * 3600)
    c.execute('''
        DELETE FROM articles 
        WHERE strftime('%s', last_seen) < ?
    ''', (cutoff,))
    
    deleted = c.rowcount
    conn.commit()
    conn.close()
    print(f"🧹 清理了 {deleted} 篇超过 {days} 天未出现的旧文章")
    return deleted


# ========== 批量抓取所有源 ==========

def fetch_all_feeds(max_entries_per_feed=30):
    """抓取所有配置的源（增量模式）"""
    try:
        from config import RSS_FEEDS
    except ImportError:
        print("❌ 找不到 config.py")
        return
    
    def _is_enabled(feed):
        return feed.get("enabled", True) is not False

    print("=" * 60)
    print(f"🚀 开始增量抓取 {len(RSS_FEEDS)} 个源")
    print("=" * 60)
    
    total_new = 0
    for i, feed in enumerate(RSS_FEEDS, 1):
        if not _is_enabled(feed):
            print(f"\n[{i}/{len(RSS_FEEDS)}] {feed['name']} (已禁用，跳过)")
            continue
        print(f"\n[{i}/{len(RSS_FEEDS)}] {feed['name']}")
        new = fetch_articles_from_feed(
            feed['url'], 
            feed['name'], 
            max_entries=max_entries_per_feed
        )
        total_new += new
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print(f"✅ 抓取完成，共新增 {total_new} 篇文章")
    print("=" * 60)
    return total_new


# ========== 命令行入口 ==========

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--fulltext":
            print("📄 运行全文抓取...")
            fetch_full_text_for_recent(limit=50)
        elif sys.argv[1] == "--cleanup":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            cleanup_old_articles(days)
        elif sys.argv[1] == "--init":
            init_db()
            print("✅ 数据库初始化完成")
        else:
            print("用法: python fetcher.py [--fulltext|--cleanup [天数]|--init]")
    else:
        # 默认：增量抓取所有源
        fetch_all_feeds(max_entries_per_feed=30)
