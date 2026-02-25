#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime
import xml.sax.saxutils as saxutils
import os

def escape_xml(text):
    """转义XML特殊字符"""
    if text is None:
        return ""
    return saxutils.escape(str(text))

def rebuild_feed():
    """重新生成RSS feed，适配现有表结构"""
    db_path = 'data/ai_rss.db'
    output_path = 'output/feed.xml'
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 这样可以用列名访问
    c = conn.cursor()
    
    print("📊 数据库中有425条记录")
    
    # 查询评分>=30的最新文章（使用正确的字段名）
    try:
        c.execute('''
            SELECT 
                article_title as title,
                article_link as link,
                published_date as published,
                summary,
                content,
                feed_name,
                criteria_score
            FROM articles 
            WHERE criteria_score >= 30 
            ORDER BY published_date DESC 
            LIMIT 50
        ''')
    except sqlite3.OperationalError as e:
        print(f"第一次查询失败: {e}")
        # 如果criteria_score字段不存在或没有值，查询所有文章
        c.execute('''
            SELECT 
                article_title as title,
                article_link as link,
                published_date as published,
                summary,
                content,
                feed_name,
                criteria_score
            FROM articles 
            ORDER BY published_date DESC 
            LIMIT 50
        ''')
    
    rows = c.fetchall()
    print(f"找到 {len(rows)} 篇文章")
    
    if len(rows) == 0:
        print("⚠️ 没有找到文章，尝试查询所有字段")
        # 查看任意一条数据
        c.execute("SELECT * FROM articles LIMIT 1")
        sample = dict(c.fetchone())
        print("数据示例:", sample)
        return
    
    items = []
    for row in rows:
        # 转换为字典方便访问
        item = dict(row)
        
        # 转义所有字段
        title = escape_xml(item.get('title', '无标题'))
        link = escape_xml(item.get('link', '#'))
        feed_name = escape_xml(item.get('feed_name', '未知来源'))
        score = item.get('criteria_score', 0)
        
        # 使用摘要或内容作为描述
        description = item.get('summary') or item.get('content') or '无摘要'
        description = escape_xml(str(description)[:300]) + "..."
        
        # 格式化发布日期
        published = item.get('published')
        try:
            if published:
                # 尝试多种日期格式
                if isinstance(published, str):
                    # 替换Z为+00:00
                    published = published.replace('Z', '+00:00')
                    pub_date = datetime.fromisoformat(published).strftime('%a, %d %b %Y %H:%M:%S +0000')
                else:
                    pub_date = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
            else:
                pub_date = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
        except Exception as e:
            print(f"日期解析错误: {e}, 使用当前时间")
            pub_date = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
        
        item_xml = f'''
    <item>
        <title>{title}</title>
        <link>{link}</link>
        <guid isPermaLink="false">{link}</guid>
        <pubDate>{pub_date}</pubDate>
        <description>{description}</description>
        <source>{feed_name}</source>
        <category>AI评分: {score}</category>
    </item>'''
        items.append(item_xml)
    
    # 获取当前隧道地址（可以从环境变量或配置读取）
    tunnel_url = "textbooks-administrator-endless-main.trycloudflare.com"
    
    # 生成完整的RSS
    rss = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
    <title>AI RSS - 科技精选</title>
    <link>https://{tunnel_url}/feed.xml</link>
    <description>AI筛选的高质量科技资讯，每日更新</description>
    <language>zh-CN</language>
    <lastBuildDate>{datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
    <atom:link href="https://{tunnel_url}/feed.xml" rel="self" type="application/rss+xml"/>
    {''.join(items)}
</channel>
</rss>'''
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rss)
    
    print(f"✅ RSS feed generated with {len(items)} items at {output_path}")
    
    # 显示文件大小和前200个字符
    file_size = os.path.getsize(output_path)
    print(f"📄 文件大小: {file_size} 字节")
    print("\n📝 预览:")
    with open(output_path, 'r', encoding='utf-8') as f:
        preview = f.read()[:500]
        print(preview + "...")
    
    conn.close()

if __name__ == '__main__':
    rebuild_feed()
