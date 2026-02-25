#!/usr/bin/env python3
import sqlite3
import os
from datetime import datetime
from feedgen.feed import FeedGenerator
import pytz

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ai_rss.db')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')

def generate_standard_rss(min_score=40, limit=100):
    """用 feedgen 生成符合 RSS 2.0 标准的 XML"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
        SELECT 
            feed_name,
            article_title,
            article_link,
            published_date,
            summary,
            raw_content,
            criteria_score,
            criteria_reason
        FROM articles
        WHERE criteria_score >= ?
        ORDER BY published_date DESC
        LIMIT ?
    ''', (min_score, limit))
    
    articles = c.fetchall()
    conn.close()
    
    if not articles:
        print("⚠️ 没有符合条件的文章")
        return None
    
    # 创建 Feed
    fg = FeedGenerator()
    fg.title('AI RSS · 精选科技资讯')
    fg.description('AI自动筛选，只保留高质量文章')
    fg.link(href='https://ai-rss.iocean.me/feed.xml', rel='self')
    fg.language('zh-CN')
    fg.lastBuildDate(datetime.now(pytz.timezone('Asia/Shanghai')))
    fg.generator('AI RSS Generator')
    
    for article in articles:
        fe = fg.add_entry()
        fe.title(article['article_title'])
        fe.link(href=article['article_link'])
        fe.guid(article['article_link'], permalink=True)
        
        # 处理发布时间
        if article['published_date']:
            pub_date = article['published_date']
            if isinstance(pub_date, str):
                try:
                    pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                except:
                    pub_date = datetime.now()
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=pytz.UTC)
            fe.pubDate(pub_date)
        
        # 安全地获取字段值
        summary_text = article['summary'] if article['summary'] else ''
        raw_content_text = article['raw_content'] if article['raw_content'] else ''
        content_preview = summary_text or raw_content_text[:300] or '暂无摘要'
        reason_text = article['criteria_reason'] or 'AI自动筛选'
        score = article['criteria_score'] or 0
        feed_name = article['feed_name'] or '未知来源'
        
        # 生成内容
        content_html = f'''
        <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 15px;">
            <div style="background: #f0f7ff; padding: 20px; border-radius: 12px; border-left: 4px solid #3498db; margin-bottom: 20px;">
                <p style="font-size: 1.2em; color: #2c3e50; font-weight: 600; margin-top: 0;">🤖 AI精选 · {score}分</p>
                <p style="color: #34495e; line-height: 1.6; font-size: 1.1em;">{content_preview}</p>
                <p style="color: #7f8c8d; font-size: 0.95em; border-top: 1px solid #d0e0f0; padding-top: 15px; margin-bottom: 0;">
                    📌 审阅：{reason_text}<br/>
                    📰 来源：{feed_name}
                </p>
            </div>
        </div>
        '''
        
        fe.content(content_html, type='html')
        fe.author(name=feed_name)
        # 修复 category 格式
        fe.category(term='AI精选', label='人工智能精选')
    
    # 生成 RSS 文件
    rss_path = os.path.join(OUTPUT_DIR, 'feed.xml')
    fg.rss_file(rss_path, pretty=True)
    
    print(f"✅ 标准 RSS 生成成功！")
    print(f"📁 位置: {rss_path}")
    print(f"📊 文章数: {len(articles)} 篇 (≥{min_score}分)")
    return rss_path

if __name__ == '__main__':
    generate_standard_rss(min_score=40, limit=100)
