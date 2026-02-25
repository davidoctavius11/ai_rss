#!/usr/bin/env python3
"""
AI筛选RSS聚合服务 - 使用数据库中的AI评分和筛选理由
"""

import os
import time
import sqlite3
from flask import Flask, Response
from datetime import datetime, timezone, timedelta
import config
from generator import RSSGenerator

app = Flask(__name__)

CACHE_DURATION = 30 * 60  # 30分钟缓存
cache = {"feed_xml": None, "timestamp": 0, "article_count": 0}

# Timeliness policy
RECENCY_DAYS = 90
EVERGREEN_SCORE = 80
FILTER_THRESHOLD = 50
MAX_FETCH = 500  # fetch more then filter for recency/evergreen

def get_ai_filtered_articles(threshold=FILTER_THRESHOLD, limit=100):
    """
    从数据库获取经过AI筛选的文章
    threshold: 最低分数阈值（默认60分）
    limit: 最多返回的文章数量
    """
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'ai_rss.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    articles = []
    
    # 1. 获取评分≥threshold的文章（先多取，后按时效/常青过滤）
    c.execute('''
        SELECT 
            article_title, 
            article_link, 
            published_date, 
            raw_content,
            criteria_score,
            criteria_reason,
            feed_name
        FROM articles 
        WHERE criteria_score >= ?
        AND criteria_reason IS NOT NULL
        AND criteria_reason != ''
        ORDER BY criteria_score DESC, published_date DESC 
        LIMIT ?
    ''', (threshold, MAX_FETCH))
    
    scored_articles = []
    for row in c.fetchall():
        article = _row_to_article(row)
        scored_articles.append(article)
    
    # 2. Timeliness filter: keep recent items (<= RECENCY_DAYS)
    #    or keep evergreen items with score >= EVERGREEN_SCORE
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENCY_DAYS)
    filtered = []
    for a in scored_articles:
        if a['score'] >= EVERGREEN_SCORE or a['published'] >= cutoff:
            filtered.append(a)

    # 3. Sort by recency, then score (so RSS shows latest first)
    filtered.sort(key=lambda x: (x['published'], x['score']), reverse=True)

    articles.extend(filtered[:limit])
    
    conn.close()
    return articles

def _row_to_article(row):
    """将数据库行转换为文章字典"""
    try:
        # 解析发布日期
        if row['published_date']:
            date_str = row['published_date']
            # 优先使用 fromisoformat（支持时区）
            try:
                published = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except ValueError:
                if 'T' in date_str:
                    # ISO格式：2026-02-24T17:50:29.061238
                    if '.' in date_str:
                        published = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
                    else:
                        published = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
                else:
                    # 简单格式：2026-02-24 17:50:29
                    published = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            # 确保所有日期都有时区信息
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
        else:
            published = datetime.now(timezone.utc)
    except ValueError:
        # 如果解析失败，使用当前时间
        published = datetime.now(timezone.utc)
    
    # 使用AI筛选理由，如果没有则使用默认
    ai_reason = row['criteria_reason'] or f"AI评分: {row['criteria_score']}分" if row['criteria_score'] else f"来自高质量源: {row['feed_name']}"
    
    return {
        'title': row['article_title'],
        'link': row['article_link'],
        'published': published,
        'summary': row['raw_content'] or '',
        'ai_reason': ai_reason,
        'source': row['feed_name'],
        'score': row['criteria_score'] or 0
    }

def get_scoring_stats():
    """获取评分统计信息"""
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'ai_rss.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 总体统计
    c.execute('''
        SELECT 
            COUNT(*) as total,
            COUNT(criteria_score) as scored,
            AVG(criteria_score) as avg_score,
            SUM(CASE WHEN criteria_score >= ? THEN 1 ELSE 0 END) as kept,
            SUM(CASE WHEN criteria_score < ? THEN 1 ELSE 0 END) as rejected
        FROM articles
    ''', (FILTER_THRESHOLD, FILTER_THRESHOLD))
    
    total, scored, avg_score, kept, rejected = c.fetchone()
    
    # 各源统计
    c.execute('''
        SELECT 
            feed_name,
            COUNT(*) as total,
            AVG(criteria_score) as avg_score,
            SUM(CASE WHEN criteria_score >= 60 THEN 1 ELSE 0 END) as kept
        FROM articles
        WHERE criteria_score IS NOT NULL
        GROUP BY feed_name
        ORDER BY avg_score DESC
    ''')
    
    feed_stats = []
    for row in c.fetchall():
        feed_stats.append({
            'name': row[0],
            'total': row[1],
            'avg_score': row[2],
            'kept': row[3]
        })
    
    conn.close()
    
    return {
        'total_articles': total,
        'scored_articles': scored,
        'avg_score': avg_score,
        'kept_articles': kept,
        'rejected_articles': rejected,
        'scoring_rate': scored / total * 100 if total > 0 else 0,
        'feed_stats': feed_stats
    }

@app.route('/')
def home():
    stats = get_scoring_stats()
    
    feed_stats_html = ""
    for feed in stats['feed_stats'][:10]:  # 只显示前10个源
        feed_stats_html += f"<li>{feed['name']}: {feed['kept']}/{feed['total']} 篇 (平均分: {feed['avg_score']:.1f})</li>"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>AI筛选RSS聚合服务</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #333; }}
            .stats {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .feed-list {{ background: #fff; padding: 15px; border-radius: 5px; border: 1px solid #ddd; }}
        </style>
    </head>
    <body>
        <h1>🤖 AI筛选RSS聚合服务</h1>
        <p>✅ 服务运行中 - 使用数据库中的AI评分和筛选理由</p>
        
        <div class="stats">
            <h3>📊 数据库统计</h3>
            <p>📰 总文章数: {stats['total_articles']} 篇</p>
            <p>🎯 已评分文章: {stats['scored_articles']} 篇 ({stats['scoring_rate']:.1f}%)</p>
            <p>📈 平均评分: {stats['avg_score']:.1f} 分</p>
        <p>✅ 保留文章: {stats['kept_articles']} 篇 (≥{FILTER_THRESHOLD}分)</p>
        <p>❌ 淘汰文章: {stats['rejected_articles']} 篇 (<{FILTER_THRESHOLD}分)</p>
        </div>
        
        <div class="feed-list">
            <h3>📡 订阅源评分统计 (前10个)</h3>
            <ul>{feed_stats_html}</ul>
        </div>
        
        <p>📱 订阅地址: <a href="/feed">/feed</a> 或 <a href="/feed.xml">/feed.xml</a></p>
        <p>🌐 永久地址: https://rss.borntofly.ai/feed.xml</p>
        <p>⚙️ 当前使用: AI评分筛选模式 (阈值: {FILTER_THRESHOLD}分)</p>
    </body>
    </html>
    """

def get_feed_content(force_refresh=False):
    global cache
    current_time = time.time()
    
    if force_refresh or cache["feed_xml"] is None or (current_time - cache["timestamp"] > CACHE_DURATION):
        print(f"\n🔄 [{datetime.now().strftime('%H:%M:%S')}] 从数据库获取增强版文章列表...")
        
        # 获取增强版文章
        articles = get_ai_filtered_articles(threshold=FILTER_THRESHOLD, limit=100)
        
        if articles and len(articles) > 0:
            # 统计文章类型
            scored_articles = [a for a in articles if a.get('score', 0) >= FILTER_THRESHOLD]
            hq_articles = [a for a in articles if a.get('score', 0) < FILTER_THRESHOLD]
            
            print(f"📊 获取到 {len(articles)} 篇文章:")
            print(f"  ✅ AI筛选文章: {len(scored_articles)} 篇 (≥60分)")
            print(f"  ⭐ 高质量源补充: {len(hq_articles)} 篇")
            
            # 显示前5篇文章的信息
            for i, article in enumerate(articles[:5]):
                score_info = f"评分: {article['score']}分" if article['score'] >= 60 else "高质量源补充"
                print(f"  {i+1}. {article['title'][:50]}...")
                print(f"     类型: {score_info} | 理由: {article['ai_reason'][:60]}...")
            
            generator = RSSGenerator(config.MY_AGGREGATED_FEED_TITLE)
            feed_xml = generator.generate_xml_string(articles)
            cache["feed_xml"] = feed_xml
            cache["timestamp"] = current_time
            cache["article_count"] = len(articles)
            print(f"✅ RSS源生成成功，{len(articles)} 篇文章")
        else:
            print("⚠️ 没有找到符合条件的文章")
            generator = RSSGenerator(config.MY_AGGREGATED_FEED_TITLE)
            feed_xml = generator.generate_xml_string([])
            cache["feed_xml"] = feed_xml
            cache["timestamp"] = current_time
            cache["article_count"] = 0
    
    return cache["feed_xml"]

@app.route('/feed')
def feed_route():
    from flask import request
    force_refresh = request.args.get('refresh') == '1'
    return Response(get_feed_content(force_refresh=force_refresh), mimetype='application/rss+xml')

@app.route('/feed.xml')
def feed_xml_route():
    from flask import request
    force_refresh = request.args.get('refresh') == '1'
    return Response(get_feed_content(force_refresh=force_refresh), mimetype='application/rss+xml')

@app.route('/debug')
def debug():
    stats = get_scoring_stats()
    return {
        "feeds": len(config.RSS_FEEDS),
        "total_articles": stats['total_articles'],
        "scored_articles": stats['scored_articles'],
        "avg_score": stats['avg_score'],
        "kept_articles": stats['kept_articles'],
        "cache_articles": cache['article_count'],
        "cache_time": cache['timestamp']
    }

@app.route('/run-judge')
def run_judge():
    """手动运行AI评分（需要密码保护，这里简化）"""
    import subprocess
    try:
        result = subprocess.run(['python3', 'criteria_judge.py', '--threshold', '60'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        return f"<pre>AI评分已运行:\n{result.stdout}</pre>"
    except Exception as e:
        return f"<pre>运行失败: {e}</pre>"

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 AI筛选RSS聚合服务启动")
    print("=" * 60)
    print(f"📡 已配置RSS源: {len(config.RSS_FEEDS)} 个")
    
    # 显示数据库统计
    stats = get_scoring_stats()
    print(f"📊 数据库统计:")
    print(f"  📰 总文章数: {stats['total_articles']} 篇")
    print(f"  🎯 已评分文章: {stats['scored_articles']} 篇 ({stats['scoring_rate']:.1f}%)")
    print(f"  📈 平均评分: {stats['avg_score']:.1f} 分")
    print(f"  ✅ 保留文章: {stats['kept_articles']} 篇 (≥60分)")
    print(f"  ❌ 淘汰文章: {stats['rejected_articles']} 篇 (<60分)")
    
    print(f"\n📱 本地地址: http://localhost:5006/feed")
    print(f"🌐 永久地址: https://rss.borntofly.ai/feed.xml")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5006, debug=False)
