"""
retail_convergence.py
零售产业链收敛分析 — 按刘强东10节甘蔗理论分段，每段独立跑收敛聚类

Usage:
    python retail_convergence.py [--days 60] [--min-score 50] [--dry-run]
    python retail_convergence.py --segment transaction --dry-run
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from openai import OpenAI

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ai_rss.db')

# ── 刘强东10节甘蔗 ─────────────────────────────────────────────────────────
# (key, label, emoji, description, feeds_set, keywords)
GANMIE_SEGMENTS = [
    (
        'design', '设计', '✏️',
        '消费者洞察 · 产品设计 · 品牌塑造 · 用户体验研究',
        {'jd-nngroup', 'jd-ux-collective', 'jd-smashing-magazine', 'jd-woshipm', 'jd-manual-wechat'},
        ['design', 'UX', 'user research', 'brand'],
    ),
    (
        'manufacturing', '制造', '🏭',
        '智能制造 · 硬件生产 · 机器人产线 · 工业自动化',
        {'jd-ieee-spectrum-robotics', 'jd-the-robot-report', 'jd-fierce-electronics', 'jd-cleantechnica'},
        ['manufacturing', 'production', 'factory', 'hardware'],
    ),
    (
        'pricing', '定价', '🏷️',
        '动态定价 · 竞争定价策略 · 利润率管理 · 价格感知',
        {'jd-digital-commerce', 'jd-practical-ecom', 'jd-modern-retail', 'jd-retail-dive', 'jd-ebrun', 'jd-36kr'},
        ['pricing', 'price', 'margin', 'discount'],
    ),
    (
        'marketing', '营销', '📣',
        '广告投放 · 内容营销 · 用户获取 · CRM · 会员体系 · 创意生成',
        {'jd-adexchanger', 'jd-digiday', 'jd-techcrunch-ai', 'jd-venturebeat-ai', 'jd-36kr-ai', 'jd-leiphone'},
        ['marketing', 'advertising', 'campaign', 'CRM'],
    ),
    (
        'transaction', '交易', '🛒',
        '商品发现 · 搜索推荐 · 购物车转化 · 平台撮合 · 个性化',
        {
            'jd-arxiv-ir', 'jd-eugeneyan', 'jd-amazon-science', 'jd-walmart-tech',
            'jd-shopify', 'jd-shopee-blog', 'jd-grab-engineering', 'jd-instacart-tech',
            'jd-alizila', 'jd-meituan-tech', 'jd-digital-commerce', 'jd-practical-ecom',
            'jd-restofworld', 'jd-krasia',
        },
        ['recommendation', 'search', 'conversion', 'marketplace', 'personalization'],
    ),
    (
        'warehousing', '仓储', '📦',
        '仓库管理系统 · 库存优化 · 自动化拣货 · 机器人仓储',
        {'jd-dc-velocity', 'jd-supplychainbrain', 'jd-logistics-viewpoints', 'jd-the-robot-report', 'jd-ieee-spectrum-robotics'},
        ['warehouse', 'inventory', 'fulfillment', 'picking', 'WMS'],
    ),
    (
        'delivery', '配送', '🚚',
        '最后一公里 · 即时配送 · 路由优化 · 跨境物流 · 无人配送',
        {
            'jd-supply-chain-dive', 'jd-freightwaves', 'jd-loadstar',
            'jd-logistics-viewpoints', 'jd-dc-velocity',
            'jd-pandaily', 'jd-scmp-tech', 'jd-techinasia',
        },
        ['delivery', 'logistics', 'last mile', 'shipping', 'routing'],
    ),
    (
        'aftersales', '售后服务', '🎧',
        '退换货 · 客户服务 · AI客服 · 质保体系 · 用户留存',
        {'jd-meituan-tech', 'jd-modern-retail', 'jd-retail-dive', 'jd-manual-wechat', 'jd-manual-report'},
        ['customer service', 'returns', 'after-sales', 'support', 'retention'],
    ),
    (
        'finance', '金融服务', '💳',
        '支付通道 · 先买后付 · 消费信贷 · 风控 · 数字钱包',
        {
            'jd-finextra', 'jd-pymnts', 'jd-stripe-blog',
            'jd-payments-dive', 'jd-digital-transactions',
            'jd-sift-blog', 'jd-atlantic-council-cbdc', 'jd-coin-center',
        },
        ['payment', 'fintech', 'BNPL', 'credit', 'fraud', 'wallet'],
    ),
    (
        'data_tech', '数据/技术', '🤖',
        'AI/ML · 大模型应用 · 推荐算法 · 数据平台 · 云基础设施',
        {
            'jd-arxiv-ir', 'jd-arxiv-lg', 'jd-amazon-science', 'jd-walmart-tech',
            'jd-alizila', 'jd-instacart-tech', 'jd-bloomberg-tech', 'jd-mit-tech-review',
            'jd-36kr-ai', 'jd-leiphone', 'jd-huxiu', 'jd-yicai',
            'jd-pandaily', 'jd-technode', 'jd-36kr-global',
            'jd-ir-jd', 'jd-ir-pdd', 'jd-ir-alibaba',
        },
        ['AI', 'machine learning', 'data', 'algorithm', 'LLM', 'model'],
    ),
]


def build_convergence_prompt(segment_label, articles_json):
    return (
        "你是一位零售行业情报分析师，专注于识别多来源独立印证同一趋势的收敛信号。\n\n"
        "以下是来自不同来源的文章列表，它们都与零售产业链「" + segment_label + "」环节有关：\n\n"
        + articles_json + "\n\n"
        "请识别其中2-5个最值得关注的收敛主题。收敛的判断标准：\n"
        "- 至少2篇文章（来自不同机构/来源）独立指向同一底层趋势或变化\n"
        "- 不是同一新闻的转载，而是不同视角/数据对同一方向的印证\n\n"
        "对每个收敛主题，输出以下字段：\n"
        "- theme_label: 简短主题标签（10字以内）\n"
        "- article_indices: 参与收敛的文章编号列表（从0开始）\n"
        "- why_convergent: 为什么这些文章构成收敛信号（100字以内）\n"
        "- synthesis_text: 给京东CTO的情报综合（150字以内，直接说对京东意味着什么）\n"
        "- strategic_question: 这个信号给京东团队留下的核心问题（一句话）\n"
        "- recommended_action: 建议行动（团队+动作+时间窗口，一句话）\n"
        "- convergence_score: 收敛强度评分0-100\n\n"
        "仅输出JSON数组，如无收敛信号返回[]。"
        ' 示例: [{"theme_label":"...","article_indices":[0,2],"why_convergent":"...","synthesis_text":"...","strategic_question":"...","recommended_action":"...","convergence_score":85}]'
    )


def get_client():
    api_key = os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('OPENAI_API_KEY')
    base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.deepseek.com/v1')
    return OpenAI(api_key=api_key, base_url=base_url)


def fetch_segment_articles(conn, segment_feeds, days, min_score):
    placeholders = ','.join('?' * len(segment_feeds))
    rows = conn.execute(
        "SELECT id, feed_name, article_title, article_link, "
        "published_date, criteria_score, criteria_reason, criteria, signal_tier "
        "FROM articles "
        "WHERE feed_name IN (" + placeholders + ") "
        "AND criteria_score >= ? "
        "AND published_date >= date('now', '-" + str(days) + " days') "
        "ORDER BY criteria_score DESC LIMIT 30",
        list(segment_feeds) + [min_score]
    ).fetchall()
    return rows


def build_article_list(rows, source_map):
    articles = []
    for i, row in enumerate(rows):
        label = source_map.get(row['feed_name'], {}).get('label', row['feed_name'])
        reason = row['criteria_reason'] or ''
        articles.append({
            'index': i,
            'title': row['article_title'],
            'source': label,
            'feed_name': row['feed_name'],
            'score': row['criteria_score'],
            'reason': reason[:200] if reason else '',
            'link': row['article_link'],
            'date': (row['published_date'] or '')[:10],
        })
    return articles


def run_convergence(client, segment_label, articles, dry_run=False):
    if len(articles) < 2:
        print(f'  [{segment_label}] only {len(articles)} articles, skip')
        return []
    if dry_run:
        print(f'  [{segment_label}] DRY RUN — {len(articles)} articles, skip API call')
        return []
    print(f'  [{segment_label}] calling DeepSeek with {len(articles)} articles...')
    try:
        articles_json = json.dumps(articles, ensure_ascii=False, indent=2)
        prompt = build_convergence_prompt(segment_label, articles_json)
        client_obj = client
        resp = client_obj.chat.completions.create(
            model='deepseek-chat',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.3,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        clusters = json.loads(raw)
        print(f'    -> {len(clusters)} convergence themes')
        return clusters
    except Exception as e:
        print(f'    x failed: {e}')
        return []


def save_clusters(conn, seg_key, seg_label, clusters, rows, source_map):
    saved = 0
    try:
        from app_simple import STANDPOINT_MAP
    except Exception:
        STANDPOINT_MAP = {}

    for cluster in clusters:
        indices = cluster.get('article_indices', [])
        matched = [rows[i] for i in indices if i < len(rows)]
        if len(matched) < 2:
            continue
        feed_names = [r['feed_name'] for r in matched]
        standpoints = list({STANDPOINT_MAP.get(f, '') for f in feed_names if STANDPOINT_MAP.get(f)})

        existing = conn.execute(
            "SELECT id FROM intelligence_clusters WHERE theme_label=? AND scope=? "
            "AND created_at >= datetime('now','-3 days')",
            (cluster['theme_label'], seg_key)
        ).fetchone()
        if existing:
            print(f'    (skip duplicate) {cluster["theme_label"]}')
            continue

        conn.execute(
            "INSERT INTO intelligence_clusters "
            "(theme_label, article_ids, article_titles, article_feed_names, "
            "article_links, article_scores, domains, standpoints, "
            "source_count, convergence_score, why_convergent, synthesis_text, "
            "strategic_question, recommended_action, created_at, scope) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                cluster['theme_label'],
                json.dumps([r['id'] for r in matched]),
                json.dumps([r['article_title'] for r in matched], ensure_ascii=False),
                json.dumps(feed_names),
                json.dumps([r['article_link'] for r in matched]),
                json.dumps([r['criteria_score'] for r in matched]),
                json.dumps([seg_label]),
                json.dumps(standpoints, ensure_ascii=False),
                len(matched),
                cluster.get('convergence_score', 70),
                cluster.get('why_convergent', ''),
                cluster.get('synthesis_text', ''),
                cluster.get('strategic_question', ''),
                cluster.get('recommended_action', ''),
                datetime.now(timezone.utc).isoformat(),
                seg_key,
            )
        )
        saved += 1
        print(f'    saved: {cluster["theme_label"]} (score={cluster.get("convergence_score")})')

    conn.commit()
    return saved


def ensure_scope_column(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(intelligence_clusters)").fetchall()]
    if 'scope' not in cols:
        conn.execute("ALTER TABLE intelligence_clusters ADD COLUMN scope TEXT DEFAULT ''")
        conn.commit()
        print('[init] added scope column to intelligence_clusters')


def main():
    parser = argparse.ArgumentParser(description='Retail 10-segment convergence analysis')
    parser.add_argument('--days',      type=int, default=60)
    parser.add_argument('--min-score', type=int, default=50)
    parser.add_argument('--segment',   type=str, default=None, help='Run single segment key')
    parser.add_argument('--dry-run',   action='store_true')
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ensure_scope_column(conn)

    try:
        from jd_config import JD_SOURCES
        source_map = {s['name']: s for s in JD_SOURCES}
    except Exception:
        source_map = {}

    client = None if args.dry_run else get_client()

    segments_to_run = GANMIE_SEGMENTS
    if args.segment:
        segments_to_run = [s for s in GANMIE_SEGMENTS if s[0] == args.segment]
        if not segments_to_run:
            print(f'Unknown segment: {args.segment}')
            print('Available:', [s[0] for s in GANMIE_SEGMENTS])
            sys.exit(1)

    total_saved = 0
    for seg_key, seg_label, seg_emoji, seg_desc, seg_feeds, _ in segments_to_run:
        print(f'\n{seg_emoji} [{seg_label}] {seg_desc}')
        rows = fetch_segment_articles(conn, seg_feeds, args.days, args.min_score)
        print(f'  {len(rows)} articles in scope')
        if args.dry_run:
            for r in rows:
                lbl = source_map.get(r['feed_name'], {}).get('label', r['feed_name'])
                print(f'    [{r["criteria_score"]}] {lbl}: {r["article_title"][:70]}')
        articles = build_article_list(rows, source_map)
        clusters = run_convergence(client, seg_label, articles, args.dry_run)
        if clusters and not args.dry_run:
            total_saved += save_clusters(conn, seg_key, seg_label, clusters, rows, source_map)

    conn.close()
    print(f'\ndone. {total_saved} clusters saved.')


if __name__ == '__main__':
    main()
