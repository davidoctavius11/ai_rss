import os
import time
from flask import Flask, Response
from datetime import datetime, timezone
import config
from fetcher import fetch_articles_from_feed
from filter import DeepSeekFilter
from generator import RSSGenerator

app = Flask(__name__)

CACHE_DURATION = 30 * 60
cache = {"feed_xml": None, "timestamp": 0, "article_count": 0, "cost": 0.0}

def fetch_and_filter_all():
    print(f"\n🔄 [{datetime.now().strftime('%H:%M:%S')}] 开始更新RSS源...")
    all_articles = []
    total_cost = 0.0
    
    try:
        deepseek_filter = DeepSeekFilter()
    except Exception as e:
        print(f"❌ DeepSeek初始化失败: {e}")
        return None, 0, 0.0
    
    for rss_feed in config.RSS_FEEDS:
        print(f"\n📡 处理: {rss_feed['name']}")
        articles = fetch_articles_from_feed(rss_feed['url'], rss_feed['name'])
        if not articles:
            print(f"   ⚠️ 抓取失败，跳过")
            continue
        print(f"   📥 抓取到 {len(articles)} 篇文章")
        test_articles = articles[:10]
        kept, cost = deepseek_filter.batch_filter(test_articles, rss_feed['criteria'], delay=0.3)
        all_articles.extend(kept)
        total_cost += cost
        print(f"   ✅ 筛选后保留 {len(kept)} 篇")
    
    all_articles.sort(key=lambda x: x.get('published', datetime.now(timezone.utc)), reverse=True)
    print(f"\n📊 全部处理完成: 保留 {len(all_articles)} 篇, 成本 ¥{total_cost:.4f}")
    return all_articles, len(all_articles), total_cost

@app.route('/')
def home():
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>ai_rss</title></head>
    <body>
        <h1>🤖 智能RSS聚合服务</h1>
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
        print("⏳ 缓存过期，重新抓取并筛选...")
        articles, count, cost = fetch_and_filter_all()
        
        if articles and len(articles) > 0:
            generator = RSSGenerator(config.MY_AGGREGATED_FEED_TITLE)
            feed_xml = generator.generate_xml_string(articles)
            cache["feed_xml"] = feed_xml
            cache["timestamp"] = current_time
            cache["article_count"] = len(articles)
            cache["cost"] += cost
            print(f"✅ RSS源生成成功，{len(articles)} 篇文章")
        else:
            generator = RSSGenerator(config.MY_AGGREGATED_FEED_TITLE)
            feed_xml = generator.generate_xml_string([])
            cache["feed_xml"] = feed_xml
            cache["timestamp"] = current_time
            cache["article_count"] = 0
            print("⚠️ 没有筛选到任何文章")
    
    return cache["feed_xml"]

@app.route('/feed')
def feed():
    return Response(get_feed_content(), mimetype='application/rss+xml')

@app.route('/feed.xml')
def feed_xml():
    return Response(get_feed_content(), mimetype='application/rss+xml')

@app.route('/debug')
def debug():
    return {
        "feeds": len(config.RSS_FEEDS),
        "feed_list": [f['name'] for f in config.RSS_FEEDS],
        "cache_articles": cache['article_count'],
        "cache_time": cache['timestamp'],
        "total_cost": cache['cost']
    }

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 智能RSS聚合服务启动")
    print("=" * 60)
    print(f"📡 已配置RSS源: {len(config.RSS_FEEDS)} 个")
    for i, feed in enumerate(config.RSS_FEEDS):
        print(f"   {i+1}. {feed['name']}")
    print(f"\n📱 本地地址: http://localhost:5003/feed")
    print(f"🌐 永久地址: https://rss.borntofly.ai/feed.xml")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5003, debug=False)