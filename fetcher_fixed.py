#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import feedparser
import sqlite3
import requests
from datetime import datetime
import time
import sys
import os

def parse_date(date_str):
    """统一将各种日期格式转换为字符串"""
    if not date_str:
        return datetime.now().isoformat()
    
    # 如果已经是datetime对象
    if isinstance(date_str, datetime):
        return date_str.isoformat()
    
    # 如果是字符串，尝试解析
    try:
        # 处理常见的RSS日期格式
        # Sun, 22 Feb 2026 20:37:45 GMT
        if 'GMT' in date_str:
            # 去掉GMT并解析
            dt = datetime.strptime(date_str.replace(' GMT', ''), '%a, %d %b %Y %H:%M:%S')
            return dt.isoformat()
        # 2026-02-22 15:00:00  +0800
        elif '+0800' in date_str:
            dt = datetime.strptime(date_str.split('+')[0].strip(), '%Y-%m-%d %H:%M:%S')
            return dt.isoformat()
        else:
            # 尝试直接解析ISO格式
            return datetime.fromisoformat(date_str).isoformat()
    except:
        # 如果都失败，返回当前时间
        return datetime.now().isoformat()

def fetch_articles():
    """抓取文章的主函数，修复了日期比较bug"""
    conn = sqlite3.connect('data/ai_rss.db')
    c = conn.cursor()
    
    # 获取所有源配置
    try:
        from config import RSS_FEEDS
        feeds = RSS_FEEDS
    except ImportError:
        print("⚠️ 无法导入config.py，使用测试源")
        feeds = [
            {"name": "InfoQ", "url": "https://www.infoq.cn/feed", "priority": "high"},
            {"name": "36氪", "url": "https://www.36kr.com/feed", "priority": "medium"},
        ]
    
    print(f"\n✅ 开始抓取 {len(feeds)} 个源")
    total_new = 0
    
    for i, feed in enumerate(feeds, 1):
        if feed.get("enabled", True) is False:
            print(f"\n[{i}/{len(feeds)}] {feed.get('name')} (已禁用，跳过)")
            continue
        feed_name = feed["name"]
        feed_url = feed["url"]
        
        print(f"\n[{i}/{len(feeds)}] {feed_name}")
        
        try:
            # 获取该源的最新文章时间
            c.execute('''
                SELECT MAX(published_date) FROM articles 
                WHERE feed_name = ?
            ''', (feed_name,))
            result = c.fetchone()
            latest_time = result[0] if result and result[0] else None
            print(f"  ├─ 📅 上次最新文章: {latest_time}")
            
            # 抓取RSS
            print(f"  ├─ 抓取 {feed_url}")
            feed_data = feedparser.parse(feed_url)
            
            if hasattr(feed_data, 'status') and feed_data.status != 200:
                print(f"  ├─ ⚠️ HTTP状态码: {feed_data.status}")
            
            entries = feed_data.entries[:30]  # 取最新30条
            print(f"  ├─ RSS包含 {len(entries)} 篇文章")
            
            new_count = 0
            
            for entry in entries:
                # 提取数据
                title = entry.get('title', '')
                link = entry.get('link', '')
                
                # 关键修复：统一转换为字符串格式
                published = parse_date(entry.get('published', ''))
                
                # 增量判断：现在都是字符串，可以比较了
                if latest_time and published <= latest_time:
                    # print(f"  ├─ 跳过旧文章: {title[:30]}...")
                    continue
                
                # 插入数据库
                try:
                    c.execute('''
                        INSERT OR REPLACE INTO articles 
                        (feed_name, article_title, article_link, published_date, 
                         last_seen, fulltext_fetched)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        feed_name, 
                        title, 
                        link, 
                        published,
                        datetime.now().isoformat(),
                        0
                    ))
                    new_count += 1
                    print(f"  ├─ ✅ 新增: {title[:50]}...")
                    
                except Exception as e:
                    print(f"  ├─ ❌ 插入失败: {e}")
                    print(f"      链接: {link}")
            
            # 提交该源的结果
            conn.commit()
            print(f"  ├─ ✨ 新增 {new_count} 篇文章")
            total_new += new_count
            
        except Exception as e:
            print(f"  ├─ ❌ 处理出错: {e}")
            conn.rollback()
    
    print(f"\n🎉 全部完成，共新增 {total_new} 篇文章")
    conn.close()
    return total_new

def fetch_fulltext():
    """抓取全文"""
    conn = sqlite3.connect('data/ai_rss.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT id, article_link FROM articles 
        WHERE fulltext_fetched = 0 AND article_link IS NOT NULL
        LIMIT 50
    ''')
    
    articles = c.fetchall()
    print(f"\n📖 需要抓取全文: {len(articles)} 篇")
    
    for article_id, link in articles:
        try:
            print(f"   抓取: {link}")
            # 这里添加您的全文抓取逻辑
            c.execute('''
                UPDATE articles 
                SET fulltext_fetched = 1, 
                    last_seen = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), article_id))
            conn.commit()
        except Exception as e:
            print(f"   ❌ 抓取失败: {e}")
            conn.rollback()
    
    conn.close()

if __name__ == '__main__':
    print("🚀 启动修复版 fetcher（日期比较已修复）")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--fulltext':
        fetch_fulltext()
    else:
        fetch_articles()
    
    print("✅ 完成")
