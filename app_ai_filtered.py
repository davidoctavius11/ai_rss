#!/usr/bin/env python3
"""
AI筛选RSS聚合服务 - 使用数据库中的AI评分和筛选理由
"""

import json
import os
import time
import sqlite3
from flask import Flask, Response, send_from_directory
from datetime import datetime, timezone, timedelta
import config
from generator import RSSGenerator

app = Flask(__name__)

CACHE_DURATION = 0  # 禁用缓存，始终生成最新RSS
cache = {"feed_xml": None, "timestamp": 0, "article_count": 0}

# Timeliness policy
RECENCY_DAYS = 90
EVERGREEN_SCORE = 80
FILTER_THRESHOLD = 50
MAX_FETCH = 2000  # fetch more then filter for recency/evergreen

def get_ai_filtered_articles(threshold=FILTER_THRESHOLD, limit=None):
    """
    从数据库获取经过AI筛选的文章
    threshold: 最低分数阈值（默认50分）
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
            id,
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
        ORDER BY published_date DESC, criteria_score DESC 
        LIMIT ?
    ''', (threshold, MAX_FETCH))
    
    scored_articles = []
    for row in c.fetchall():
        article = _row_to_article(row)
        article['id'] = row['id']
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

    # attach multi-perspective summaries if available
    if filtered:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c2 = conn.cursor()
        links = [a['link'] for a in filtered]
        placeholders = ",".join(["?"] * len(links))
        try:
            c2.execute(f'''
                SELECT article_link, summary, cluster_json
                FROM multi_perspectives
                WHERE article_link IN ({placeholders})
            ''', links)
            mp_rows = c2.fetchall()
        except Exception:
            c2.execute(f'''
                SELECT article_link, summary
                FROM multi_perspectives
                WHERE article_link IN ({placeholders})
            ''', links)
            mp_rows = c2.fetchall()
        mp_map = {r['article_link']: r for r in mp_rows}
        conn.close()
        for a in filtered:
            if a['link'] in mp_map:
                r = mp_map[a['link']]
                a['multi_perspective'] = r['summary']
                a['cluster_json'] = r['cluster_json'] if 'cluster_json' in r.keys() else None
            # expose internal summary page
            a['internal_link'] = f"https://rss.borntofly.ai/item/{a['id']}"

        # Build reverse map: cluster member link → seed info
        # so non-seed articles can show a "Part of story" pointer
        try:
            mp_conn = sqlite3.connect(db_path)
            mp_conn.row_factory = sqlite3.Row
            mp_c = mp_conn.cursor()
            mp_c.execute('SELECT article_link, article_title, cluster_json FROM multi_perspectives WHERE cluster_json IS NOT NULL')
            member_map = {}
            for r in mp_c.fetchall():
                try:
                    for item in json.loads(r['cluster_json']):
                        if item['link'] != r['article_link']:
                            member_map[item['link']] = {
                                'seed_link': r['article_link'],
                                'seed_title': r['article_title'],
                            }
                except Exception:
                    pass
            mp_conn.close()
        except Exception:
            member_map = {}

        for a in filtered:
            if not a.get('multi_perspective') and a['link'] in member_map:
                a['cluster_member_of'] = member_map[a['link']]

        # Seeds (with synthesis) float to top; within each group keep recency+score order
        filtered.sort(
            key=lambda x: (1 if x.get('multi_perspective') else 0, x['published'], x['score']),
            reverse=True
        )

    if limit is None:
        articles.extend(filtered)
    else:
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
    conn.row_factory = sqlite3.Row
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
            SUM(CASE WHEN criteria_score >= ? THEN 1 ELSE 0 END) as kept
        FROM articles
        WHERE criteria_score IS NOT NULL
        GROUP BY feed_name
        ORDER BY avg_score DESC
    ''', (FILTER_THRESHOLD,))
    
    feed_stats = []
    for row in c.fetchall():
        feed_stats.append({
            'name': row[0],
            'total': row[1],
            'avg_score': row[2],
            'kept': row[3]
        })

    # 计算进入RSS的有效文章数（时效 + 常青）
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
        ORDER BY published_date DESC, criteria_score DESC
        LIMIT ?
    ''', (FILTER_THRESHOLD, MAX_FETCH))
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENCY_DAYS)
    eligible = 0
    for row in c.fetchall():
        a = _row_to_article(row)
        if a['score'] >= EVERGREEN_SCORE or a['published'] >= cutoff:
            eligible += 1
    
    conn.close()
    
    return {
        'total_articles': total,
        'scored_articles': scored,
        'avg_score': avg_score,
        'kept_articles': kept,
        'rejected_articles': rejected,
        'scoring_rate': scored / total * 100 if total > 0 else 0,
        'feed_stats': feed_stats,
        'eligible_articles': eligible
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
            <p>🧭 进入RSS: {stats['eligible_articles']} 篇 (≤{RECENCY_DAYS}天 或 ≥{EVERGREEN_SCORE}分)</p>
            <p>📤 RSS输出: {cache['article_count']} 篇 (无上限)</p>
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
        articles = get_ai_filtered_articles(threshold=FILTER_THRESHOLD, limit=None)
        
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
    # Always refresh on /feed to avoid stale caches in RSS apps
    return Response(get_feed_content(force_refresh=True), mimetype='application/rss+xml')

@app.route('/feed.xml')
def feed_xml_route():
    from flask import request
    # Always refresh on /feed.xml to avoid stale caches in RSS apps
    return Response(get_feed_content(force_refresh=True), mimetype='application/rss+xml')

@app.route('/item/<int:article_id>')
def item_detail(article_id):
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'ai_rss.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''
        SELECT id, feed_name, article_title, article_link, published_date, raw_content,
               criteria_score, criteria_reason
        FROM articles WHERE id = ?
    ''', (article_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return Response("Not found", status=404)

    # multi-perspective summary + cluster (if exists)
    mp = None
    cluster_items = []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT summary, cluster_json FROM multi_perspectives WHERE article_link = ?', (row['article_link'],))
        r = c.fetchone()
        conn.close()
        if r:
            mp = r['summary']
            if r['cluster_json']:
                cluster_items = json.loads(r['cluster_json'])
    except Exception:
        mp = None
        cluster_items = []

    title = row['article_title']
    source = row['feed_name']
    link = row['article_link']
    reason = row['criteria_reason'] or "无筛选理由"
    score = row['criteria_score']
    content = row['raw_content'] or ""
    published = row['published_date']

    if mp:
        cluster_html = ""
        if cluster_items:
            items_html = "".join(
                f'<li><a href="{item["link"]}" target="_blank">[{item["source"]}] {item["title"]}</a></li>'
                for item in cluster_items
            )
            cluster_html = f'<h3>📰 本故事综合了 {len(cluster_items)} 篇报道</h3><ul style="line-height:1.8">{items_html}</ul>'
        mp_formatted = mp.replace('\n', '<br>')
        mp_block = f"""
        <div style="background:#f0f7ff;border-left:4px solid #0066cc;padding:16px 20px;margin:20px 0;border-radius:4px">
          <h3 style="margin-top:0">🧠 多视角故事总结</h3>
          {cluster_html}
          <div style="margin-top:12px;word-wrap:break-word;overflow-wrap:break-word">{mp_formatted}</div>
        </div>"""
    else:
        mp_block = ""
    html = f"""
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{title}</title>
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               max-width: 760px; margin: 20px auto; padding: 0 16px;
               line-height: 1.7; color: #222; }}
        h1 {{ font-size: 1.3em; line-height: 1.4; }}
        a {{ word-break: break-all; }}
        p, li, div {{ word-wrap: break-word; overflow-wrap: break-word; }}
      </style>
    </head>
    <body>
      <h1>{title}</h1>
      <p><b>来源：</b>{source}</p>
      <p><b>发布时间：</b>{published}</p>
      <p><b>评分：</b>{score}</p>
      <p><b>筛选理由：</b>{reason}</p>
      {mp_block}
      <h3>摘要</h3>
      <p>{content}</p>
      <p><a href="{link}" target="_blank">阅读原文</a></p>
    </body>
    </html>
    """
    return Response(html, mimetype='text/html')

@app.route('/podcast.xml')
def podcast_feed():
    podcast_path = os.path.join(os.path.dirname(__file__), 'output', 'podcast', 'podcast.xml')
    if not os.path.exists(podcast_path):
        return Response("", mimetype='application/rss+xml')
    with open(podcast_path, 'r', encoding='utf-8') as f:
        return Response(f.read(), mimetype='application/rss+xml')

@app.route('/podcast/audio/<path:filename>')
def podcast_audio(filename):
    audio_dir = os.path.join(os.path.dirname(__file__), 'output', 'podcast', 'audio')
    return send_from_directory(audio_dir, filename, as_attachment=False)

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
        result = subprocess.run(['python3', 'criteria_judge.py', '--threshold', '50'], 
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
    print(f"  ✅ 保留文章: {stats['kept_articles']} 篇 (≥{FILTER_THRESHOLD}分)")
    print(f"  ❌ 淘汰文章: {stats['rejected_articles']} 篇 (<{FILTER_THRESHOLD}分)")
    
    print(f"\n📱 本地地址: http://localhost:5006/feed")
    print(f"🌐 永久地址: https://rss.borntofly.ai/feed.xml")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5006, debug=False)
