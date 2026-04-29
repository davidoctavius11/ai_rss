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

# ── 8大业务域 ──────────────────────────────────────────────────────────────
# (key, label, emoji, description, feeds_set, keywords)
GANMIE_SEGMENTS = [
    (
        'search_content', '搜索与内容社区', '🔍',
        '搜索推荐 · 内容发现 · 个性化 · UX设计 · 用户研究 · 技术社区信号',
        {
            'jd-arxiv-ir', 'jd-eugeneyan', 'jd-amazon-science', 'jd-walmart-tech',
            'jd-instacart-tech', 'jd-grab-engineering', 'jd-shopify', 'jd-shopee-blog',
            'jd-nngroup', 'jd-ux-collective', 'jd-woshipm', 'jd-hackernews',
            'jd-meituan-tech', 'jd-digital-commerce',
        },
        ['search', 'recommendation', 'content', 'discovery', 'personalization', 'UX', 'design'],
    ),
    (
        'advertising', '广告营销', '📣',
        '程序化广告 · 内容营销 · 用户获取 · CRM · 创意生成 · 品牌传播',
        {
            'jd-adexchanger', 'jd-digiday', 'jd-techcrunch-ai', 'jd-venturebeat-ai',
            'jd-36kr-ai', 'jd-leiphone', 'jd-36kr-funding',
        },
        ['advertising', 'marketing', 'campaign', 'CRM', 'brand', 'growth'],
    ),
    (
        'smart_retail', '智能零售', '🛒',
        '电商平台 · 动态定价 · 购物车转化 · 竞品动态 · 跨境电商',
        {
            'jd-modern-retail', 'jd-retail-dive', 'jd-digital-commerce', 'jd-practical-ecom',
            'jd-ebrun', 'jd-36kr', 'jd-restofworld', 'jd-krasia', 'jd-alizila',
            'jd-ir-jd', 'jd-ir-pdd', 'jd-ir-alibaba',
            'jd-pandaily', 'jd-techinasia', 'jd-scmp-tech', 'jd-36kr-global',
            'jd-yicai', 'jd-huxiu',
        },
        ['retail', 'ecommerce', 'pricing', 'marketplace', 'platform', 'conversion'],
    ),
    (
        'finance', '金融与支付', '💳',
        '支付通道 · 先买后付 · 消费信贷 · 风控 · 数字钱包 · 稳定币',
        {
            'jd-finextra', 'jd-pymnts', 'jd-stripe-blog',
            'jd-payments-dive', 'jd-digital-transactions',
            'jd-sift-blog', 'jd-atlantic-council-cbdc', 'jd-coin-center',
        },
        ['payment', 'fintech', 'BNPL', 'credit', 'fraud', 'wallet'],
    ),
    (
        'logistics', '物流与供应链', '🚚',
        '仓储自动化 · 最后一公里 · 即时配送 · 路由优化 · 跨境物流',
        {
            'jd-dc-velocity', 'jd-supplychainbrain', 'jd-logistics-viewpoints',
            'jd-supply-chain-dive', 'jd-freightwaves', 'jd-loadstar',
            'jd-the-robot-report', 'jd-ieee-spectrum-robotics',
        },
        ['warehouse', 'logistics', 'last mile', 'delivery', 'shipping', 'fulfillment', 'supply chain'],
    ),
    (
        'robotics', '具身智能与机器人', '🦾',
        '仿人机器人 · 工业自动化 · 感知规划 · 具身AI · 操控系统',
        {
            'jd-ieee-spectrum-robotics', 'jd-the-robot-report',
            'jd-mit-tech-review', 'jd-import-ai', 'jd-bloomberg-tech',
        },
        ['robot', 'embodied', 'manipulation', 'autonomous', 'humanoid', 'motor', 'dexterous'],
    ),
    (
        'hardware', '智能硬件', '🔧',
        '芯片 · 消费电子 · 智能设备 · IoT · 新能源 · 通信模组',
        {
            'jd-fierce-electronics', 'jd-cleantechnica', 'jd-electrek',
            'jd-electrive', 'jd-rcr-wireless', 'jd-canary-media',
        },
        ['chip', 'hardware', 'electronics', 'IoT', 'device', 'energy', 'EV', 'semiconductor'],
    ),
    (
        'ai_infra', 'AI基础设施', '⚡',
        '大模型 · 推理优化 · 训练平台 · AI Agent · 开发工具链 · 数据平台',
        {
            'jd-arxiv-lg', 'jd-chip-huyen', 'jd-interconnects', 'jd-karpathy',
            'jd-lillog', 'jd-fastai', 'jd-import-ai', 'jd-a16z',
            'jd-latent-space', 'jd-simonwillison', 'jd-langchain-blog',
            'jd-swyx', 'jd-the-gradient', 'jd-towards-ds', 'jd-lesswrong',
            'jd-techcrunch-ai', 'jd-venturebeat-ai', 'jd-mit-tech-review',
            'jd-bloomberg-tech', 'jd-qbitai',
        },
        ['AI', 'LLM', 'model', 'inference', 'training', 'agent', 'platform', 'infrastructure'],
    ),
]


def build_convergence_prompt(segment_label, articles_json):
    example = (
        '{"theme_label":"多模态搜索商品化",'
        '"article_indices":[0,2],'
        '"why_convergent":"Amazon发布Nova多模态搜索API，学术论文同步验证属性级细粒度嵌入方案，产品与研究双路印证。",'
        '"synthesis_text":"多模态搜索从实验室走向产品，京东商品图文数据优势需转化为多模态索引能力，否则竞对将率先建立体验壁垒。",'
        '"strategic_question":"我们的搜索是否已具备视频/图像级理解能力？",'
        '"recommended_action":"搜索算法团队 — 启动多模态嵌入POC — 一个月内",'
        '"convergence_score":85,'
        '"shipped_product":"Amazon Nova多模态嵌入API — 已面向开发者开放，支持图文视频联合检索",'
        '"value_experience":"用户可用图片或视频直接搜商品，减少关键词输入摩擦，提升发现效率",'
        '"value_cost":"向量化索引替代关键词召回可降低查询成本约30%，减少无效流量",'
        '"value_efficiency":"多模态嵌入使商品理解精度提升，降低人工标注依赖",'
        '"maturity":"growing",'
        '"leader_names":"Amazon、阿里通义万象",'
        '"leader_type":"competitor",'
        '"reaction":"act",'
        '"lean_in_teams":"搜索推荐算法团队、AIGC平台"}'
    )
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
        "- why_convergent: 为什么这些文章构成收敛信号（80字以内）\n"
        "- synthesis_text: 给京东CTO的情报综合（120字以内，直接说对京东意味着什么）\n"
        "- strategic_question: 这个信号给京东团队留下的核心问题（一句话）\n"
        "- recommended_action: 建议行动（团队+动作+时间窗口，一句话）\n"
        "- convergence_score: 收敛强度评分0-100\n"
        "- shipped_product: 已实际发布给终端用户的具体产品/技术/服务名称及一句话描述（尚未商业化则填'尚未商业化'）\n"
        "- value_experience: 该产品/技术对用户体验（体验）的影响，1-2句，要具体\n"
        "- value_cost: 对成本结构（成本）的影响，1-2句，要具体\n"
        "- value_efficiency: 对运营效率（效率）的影响，1-2句，要具体\n"
        "- maturity: 成熟度，只能是 early（早期探索）/ growing（快速扩张）/ mature（成熟落地）之一\n"
        "- leader_names: 领跑者公司/团队名称，2-3个，逗号分隔\n"
        "- leader_type: 领跑者与京东关系，只能是 competitor / partner / neutral / mixed 之一\n"
        "- reaction: 京东建议态度，只能是 ignore / monitor / act 之一\n"
        "- lean_in_teams: 建议介入或给出判断的京东团队，2-3个，逗号分隔\n\n"
        "仅输出JSON数组，如无收敛信号返回[]。\n"
        "示例单条格式：\n[" + example + "]"
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
            max_tokens=4000,
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

    ACTION_FIELDS = [
        'shipped_product', 'value_experience', 'value_cost', 'value_efficiency',
        'maturity', 'leader_names', 'leader_type', 'reaction', 'lean_in_teams',
    ]

    for cluster in clusters:
        indices = cluster.get('article_indices', [])
        matched = [rows[i] for i in indices if i < len(rows)]
        if len(matched) < 2:
            continue
        feed_names = [r['feed_name'] for r in matched]
        standpoints = list({STANDPOINT_MAP.get(f, '') for f in feed_names if STANDPOINT_MAP.get(f)})

        action_data = json.dumps(
            {k: cluster.get(k, '') for k in ACTION_FIELDS},
            ensure_ascii=False
        )

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
            "strategic_question, recommended_action, created_at, scope, action_data) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
                action_data,
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
    if 'action_data' not in cols:
        conn.execute("ALTER TABLE intelligence_clusters ADD COLUMN action_data TEXT DEFAULT ''")
        conn.commit()
        print('[init] added action_data column to intelligence_clusters')


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
