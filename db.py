#!/usr/bin/env python3
"""
AI RSS 数据库操作模块
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ai_rss.db')

def init_db():
    """初始化数据库和表"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 创建文章表
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
    
    # 创建索引
    c.execute('CREATE INDEX IF NOT EXISTS idx_article_link ON articles(article_link)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_published_date ON articles(published_date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_criteria_score ON articles(criteria_score)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_fulltext_fetched ON articles(fulltext_fetched)')
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")

def save_articles(articles_list, feed_name, feed_url, criteria=""):
    """保存文章列表到数据库"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    saved_count = 0
    for article in articles_list:
        try:
            c.execute('''
                INSERT OR IGNORE INTO articles 
                (feed_name, feed_url, article_title, article_link, published_date, raw_content, criteria)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                feed_name,
                feed_url,
                article.get('title', '无标题'),
                article.get('link', ''),
                article.get('published', datetime.now()),
                article.get('summary', ''),
                criteria
            ))
            if c.rowcount > 0:
                saved_count += 1
        except Exception as e:
            print(f"    ⚠️ 保存失败: {e}")
    
    conn.commit()
    conn.close()
    return saved_count

def get_recent_articles(limit=50, min_score=None):
    """获取最近的文章"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = '''
        SELECT * FROM articles 
        WHERE 1=1
    '''
    params = []
    
    if min_score is not None:
        query += ' AND criteria_score >= ?'
        params.append(min_score)
    
    query += ' ORDER BY published_date DESC LIMIT ?'
    params.append(limit)
    
    c.execute(query, params)
    articles = c.fetchall()
    conn.close()
    return articles

if __name__ == '__main__':
    init_db()