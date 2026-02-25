import os
import time
import sqlite3
from flask import Flask, Response
from datetime import datetime, timezone
import config
from generator import RSSGenerator

app = Flask(__name__)

CACHE_DURATION = 30 * 60
cache = {"feed_xml": None, "timestamp": 0, "article_count": 0, "cost": 0.0}

def get_articles_from_db(feed_name, limit=50):
    """从数据库获取指定源的最新文章"""
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'ai_rss.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
        SELECT article_title, article_link, published_date, raw_content
        FROM articles 
        WHERE feed_name = ? 
        ORDER BY published_date DESC 
        LIMIT ?
    ''', (feed_name, limit))
    
    articles = []
    for row in c.fetchall():
        try:
            if row['published_date']:
                date_str = row['published_date']
                if 'T' in date_str:
                    if '.' in date_str:
                        published = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
                    else:
                        published = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
                else:
                    published = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
            else:
                published = datetime.now(timezone.utc)
        except ValueError:
            published = datetime.now(timezone.utc)
        
        article = {
            'title': row['article_title'],
            'link': row['article_link'],
            'published': published,
            'summary': row['raw_content'] or ''
        }
        articles.append(article)
    
    conn.close()
    return articles

def fetch_all_articles():
    print(f"\n🔄 [{datetime.now().strftime('%H:%M:%S')}] 开始获取文章...")
    all_articles = []
    
    for rss_feed in config.RSS_FEEDS:
        print(f"\n📡 处理: {rss_feed['name']}")
        articles = get_articles_from_db(rss_feed['name'], limit=5)
        if not articles:
            print(f"   ⚠️ 数据库中没有文章，跳过")
            continue
        print(f"   📥 从数据库获取到 {len(articles)} 篇文章")
        all_articles.extend(articles)
    
    for article in all_articles:
        if 'published' not in article:
            article['published'] = datetime.now(timezone.utc)
        elif article['published'].tzinfo is None:
            article['published'] = article['published'].replace(tzinfo=timezone.utc)
    
    all_articles.sort(key=lambda x: x['published'], reverse=True)
    print(f"\n📊 全部处理完成: 获取 {len(all_articles)} 篇")
    return all_articles, len(all_articles), 0.0

@app.route('/')
def home():
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>ai_rss</title></head>
    <body>
        <h1>🤖 智能RSS聚合服务（简化版）</h1>
        <p>✅ 服务运行中</p>
        <p>📡 订阅源数量: {len(config.RSS_FEEDS)} 个</p>
        <p>📰 当前缓存文章: {cache['article_count']} 篇</p>
        <p>💰 累计API成本: ¥{cache['cost']:.4f}</p>
        <p>📱 订阅地址: <a href="/feed">/feed</a> 或 <a href="/feed.xml">/feed.xml</a></p>
        <p>🌐 永久地址: https://rss.borntofly.ai/feed.xml</p>
    </body>
    </html>
    """

def get_feed_content():
    global cache
    current_time = time.time()
    
    if cache["feed_xml"] is None or (current_time - cache["timestamp"] > CACHE_DURATION):
        print("⏳ 缓存过期，重新获取文章...")
        articles, count, cost = fetch_all_articles()
        
        if articles and len(articles) > 0:
            generator = RSSGenerator(
                config.MY_AGGREGATED_FEED_TITLE,
                feed_link="https://rss.borntofly.ai/feed.xml",
                feed_description="AI智能筛选的资讯聚合 - 通过DeepSeek API筛选高质量内容"
            )
            feed_xml = generator.generate_xml_string(articles)
            cache["feed_xml"] = feed_xml
            cache["timestamp"] = current_time
            cache["article_count"] = len(articles)
            cache["cost"] += cost
            print(f"✅ RSS源生成成功，{len(articles)} 篇文章")
        else:
            generator = RSSGenerator(
                config.MY_AGGREGATED_FEED_TITLE,
                feed_link="https://rss.borntofly.ai/feed.xml",
                feed_description="AI智能筛选的资讯聚合 - 通过DeepSeek API筛选高质量内容"
            )
            feed_xml = generator.generate_xml_string([])
            cache["feed_xml"] = feed_xml
            cache["timestamp"] = current_time
            cache["article_count"] = 0
            print("⚠️ 没有获取到任何文章")
    
    return cache["feed_xml"]

@app.route('/feed')
def feed_route():
    return Response(get_feed_content(), mimetype='application/rss+xml')

@app.route('/feed.xml')
def feed_xml_route():
    return Response(get_feed_content(), mimetype='application/rss+xml')

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 智能RSS聚合服务（简化版）启动")
    print("=" * 60)
    print(f"📡 已配置RSS源: {len(config.RSS_FEEDS)} 个")
    print(f"\n📱 本地地址: http://localhost:5005/feed")
    print(f"🌐 永久地址: https://rss.borntofly.ai/feed.xml")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5005, debug=False)