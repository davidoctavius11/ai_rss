import os
import time
import sqlite3
import json
from flask import Flask, Response, request
from datetime import datetime, timezone
import config
from generator import RSSGenerator
from jd_config import JD_SOURCES, CATEGORY_LABELS, TIER_LABELS, X_ENDORSER_WEIGHTS

app = Flask(__name__)

CACHE_DURATION = 30 * 60
cache = {"feed_xml": None, "timestamp": 0, "article_count": 0, "cost": 0.0}
jd_cache = {"feed_xml": None, "timestamp": 0, "article_count": 0}
jd_t1_cache = {"feed_xml": None, "timestamp": 0, "article_count": 0}
jd_t2_cache = {"feed_xml": None, "timestamp": 0, "article_count": 0}

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ai_rss.db')
JD_SOURCE_MAP = {s["name"]: s for s in JD_SOURCES}

# Maps twitter feed_name → (display name, emoji, role_desc)
TWITTER_PERSON_MAP = {
    'jd-twitter-karpathy':     ('Andrej Karpathy',  '🤖', 'ex-Tesla/OpenAI · AI工程'),
    'jd-twitter-ylecun':       ('Yann LeCun',       '🧠', 'Meta FAIR首席AI科学家'),
    'jd-twitter-sama':         ('Sam Altman',       '🏢', 'OpenAI CEO'),
    'jd-twitter-GaryMarcus':   ('Gary Marcus',      '⚠️', 'AI批评者 · 认知科学'),
    'jd-twitter-emollick':     ('Ethan Mollick',    '📚', 'Wharton · AI与未来工作'),
    'jd-twitter-drjimfan':     ('Jim Fan',          '🦾', 'NVIDIA · 具身AI'),
    'jd-twitter-fchollet':     ('François Chollet', '🧩', 'ARC-AGI作者'),
    'jd-twitter-xlr8harder':   ('Derrick Harris',   '⚡', 'AI基础设施观察'),
    'jd-twitter-demishassabis':('Demis Hassabis',   '🔬', 'Google DeepMind CEO'),
    'jd-twitter-darioamodei':  ('Dario Amodei',     '🔒', 'Anthropic CEO'),
    'jd-twitter-ilyasut':      ('Ilya Sutskever',   '🧬', 'SSI'),
    'jd-twitter-gdb':          ('Greg Brockman',    '🏗', 'OpenAI'),
    'jd-twitter-jeffdean':     ('Jeff Dean',        '⚙️', 'Google'),
    'jd-twitter-AndrewYNg':    ('Andrew Ng',        '📊', 'AI教育者'),
    'jd-twitter-rasbt':        ('Sebastian Raschka','🔬', 'Lightning AI · ML研究'),
    'jd-twitter-kaifulee':     ('Kai-Fu Lee',       '🌏', '创新工场'),
    'jd-twitter-pmarca':       ('Marc Andreessen',  '💰', 'a16z'),
    'jd-twitter-naval':        ('Naval Ravikant',   '💡', '天使投资人'),
    'jd-twitter-chamath':      ('Chamath',          '📈', '社会资本'),
    'jd-twitter-sarahguo':     ('Sarah Guo',        '🚀', 'Conviction Capital'),
    'jd-twitter-eladgil':      ('Elad Gil',         '💼', 'AI天使投资人'),
    'jd-twitter-martin_casado':('Martin Casado',    '☁️', 'a16z · 云计算'),
}

# Maps feed_name → standpoint label (shown in grey next to source link on cards)
STANDPOINT_MAP = {
    # 关键玩家官方信源
    **{k: '关键玩家' for k in [
        'jd-openai-blog','jd-deepmind-blog','jd-google-ai-blog','jd-meta-engineering',
        'jd-microsoft-research','jd-huggingface-blog','jd-qwenlm','jd-nvidia-developer',
        'jd-aws-aiml','jd-meituan-tech','jd-amazon-science','jd-walmart-tech',
        'jd-shopify','jd-grab-engineering','jd-shopee-blog','jd-instacart-tech',
        'jd-databricks','jd-alizila',
    ]},
    # 资本动向与投资人观点
    **{k: '资本动向' for k in [
        'jd-a16z','jd-sequoia','jd-lightspeed','jd-ycombinator','jd-elad-gil',
        'jd-tomasz-tunguz','jd-benedict-evans','jd-paul-graham','jd-nathan-benaich',
        'jd-crunchbase-news',
    ]},
    # 顶尖研究者与工程师
    **{k: '顶尖研究者' for k in [
        'jd-chip-huyen','jd-interconnects','jd-karpathy','jd-lillog','jd-eugeneyan',
        'jd-swyx','jd-fastai','jd-import-ai','jd-the-gradient','jd-synced',
        'jd-nngroup','jd-sre-weekly','jd-ieee-spectrum-robotics','jd-stripe-blog',
        'jd-arxiv-ir','jd-arxiv-lg',
        'jd-simonwillison','jd-latent-space','jd-towards-ds','jd-lesswrong',
        # Twitter/X — 顶尖研究者
        'jd-twitter-karpathy','jd-twitter-ylecun','jd-twitter-drjimfan','jd-twitter-fchollet',
        'jd-twitter-ilyasut','jd-twitter-AndrewYNg','jd-twitter-rasbt',
        'jd-twitter-emollick','jd-twitter-GaryMarcus','jd-twitter-xlr8harder',
    ]},
    # 关键玩家（补充）
    **{k: '关键玩家' for k in [
        'jd-langchain-blog',
        # Twitter/X — 关键玩家
        'jd-twitter-sama','jd-twitter-demishassabis',
        'jd-twitter-darioamodei','jd-twitter-gdb','jd-twitter-jeffdean','jd-twitter-kaifulee',
    ]},
    # 资本动向（Twitter补充）
    **{k: '资本动向' for k in [
        'jd-twitter-pmarca','jd-twitter-naval',
        'jd-twitter-sarahguo','jd-twitter-eladgil',
        'jd-twitter-martin_casado','jd-twitter-chamath',
    ]},
    # 人工投稿
    **{k: '科技媒体' for k in ['jd-manual-wechat']},
    **{k: '技术社区'  for k in ['jd-manual-community']},  # Discord/Reddit/HN/WeChat群
    **{k: '内部情报'  for k in ['jd-manual-report']},     # 内部报告/会议纪要
    # 产品技术社区
    **{k: '技术社区' for k in [
        'jd-github-blog','jd-ux-collective','jd-smashing-magazine','jd-infoq',
        'jd-woshipm','jd-hackernews',
    ]},
    # 中国科技媒体
    **{k: '科技媒体' for k in [
        'jd-qbitai',
    ]},
    # 中外科技媒体
    **{k: '科技媒体' for k in [
        'jd-techcrunch-ai','jd-verge-ai','jd-venturebeat-ai','jd-mit-tech-review',
        'jd-wired','jd-platformer','jd-bloomberg-tech','jd-stratechery',
        'jd-mittr-china','jd-restofworld',
        'jd-36kr','jd-36kr-ai','jd-36kr-funding','jd-36kr-global',
        'jd-leiphone','jd-huxiu','jd-pingwest','jd-ebrun',
        'jd-technode','jd-pandaily','jd-scmp-tech','jd-techinasia',
    ]},
    # 中国媒体（scraper来源）
    **{k: '科技媒体' for k in [
        'jd-jiqizhixin','jd-latepost','jd-geekpark','jd-yicai','jd-ifanr','jd-ruanyifeng',
    ]},
    **{k: '政策与专利' for k in [
        'jd-miit','jd-cac',
    ]},
    # 行业媒体和研究
    **{k: '行业媒体' for k in [
        'jd-modern-retail','jd-digital-commerce','jd-retail-dive','jd-practical-ecom',
        'jd-krasia','jd-supply-chain-dive','jd-logistics-viewpoints','jd-dc-velocity',
        'jd-freightwaves','jd-loadstar','jd-supplychainbrain',
        'jd-adexchanger','jd-digiday','jd-finextra','jd-pymnts','jd-sift-blog',
        'jd-payments-dive','jd-digital-transactions',
        'jd-naavik','jd-the-robot-report','jd-cleantechnica','jd-carbon-brief','jd-trellis',
        'jd-canary-media',
        'jd-stat-health-tech','jd-medcity-news','jd-mobihealthnews',
        'jd-rcr-wireless','jd-electrek','jd-electrive','jd-fierce-electronics',
        'jd-google-security','jd-cloudflare-security',
    ]},
    # 科技媒体（新增）
    **{k: '科技媒体' for k in [
        'jd-axios-ai','jd-ars-technica',
    ]},
    # 关键玩家（新增）
    **{k: '关键玩家' for k in [
        'jd-huggingface-blog',
    ]},
    # 政策监管 + 专利情报（合并：均属法律约束下的强制披露信号）
    **{k: '政策与专利' for k in [
        'jd-eu-digital','jd-eu-ai-act','jd-ftc-tech','jd-nist-ai',
        'jd-atlantic-council-cbdc','jd-coin-center',
    ]},
    # 资本动向：VC观点 + 投资人博客 + 财报一手 + 财经分析媒体（均属资本视角信号）
    **{k: '资本动向' for k in [
        'jd-ir-jd','jd-ir-pdd','jd-ir-alibaba',
        'jd-earnings-analysis',
        'jd-sa-earnings','jd-wsj-markets',
    ]},
}

# feed_name → primary business domain tag shown on article cards
FEED_DOMAIN_MAP = {
    # 搜索与内容社区
    'jd-arxiv-ir':              '搜索与内容社区',
    'jd-eugeneyan':             '搜索与内容社区',
    'jd-amazon-science':        '搜索与内容社区',
    'jd-walmart-tech':          '搜索与内容社区',
    'jd-instacart-tech':        '搜索与内容社区',
    'jd-grab-engineering':      '搜索与内容社区',
    'jd-shopify':               '搜索与内容社区',
    'jd-shopee-blog':           '搜索与内容社区',
    'jd-nngroup':               '搜索与内容社区',
    'jd-ux-collective':         '搜索与内容社区',
    'jd-woshipm':               '搜索与内容社区',
    'jd-hackernews':            '搜索与内容社区',
    'jd-meituan-tech':          '搜索与内容社区',
    # 广告营销
    'jd-adexchanger':           '广告营销',
    'jd-digiday':               '广告营销',
    'jd-36kr-funding':          '广告营销',
    # 智能零售
    'jd-modern-retail':         '智能零售',
    'jd-retail-dive':           '智能零售',
    'jd-digital-commerce':      '智能零售',
    'jd-practical-ecom':        '智能零售',
    'jd-ebrun':                 '智能零售',
    'jd-36kr':                  '智能零售',
    'jd-restofworld':           '智能零售',
    'jd-krasia':                '智能零售',
    'jd-alizila':               '智能零售',
    'jd-ir-jd':                 '智能零售',
    'jd-ir-pdd':                '智能零售',
    'jd-ir-alibaba':            '智能零售',
    'jd-pandaily':              '智能零售',
    'jd-techinasia':            '智能零售',
    'jd-scmp-tech':             '智能零售',
    'jd-36kr-global':           '智能零售',
    'jd-yicai':                 '智能零售',
    'jd-huxiu':                 '智能零售',
    # 金融与支付
    'jd-finextra':              '金融与支付',
    'jd-pymnts':                '金融与支付',
    'jd-sift-blog':             '金融与支付',
    'jd-stripe-blog':           '金融与支付',
    'jd-payments-dive':         '金融与支付',
    'jd-digital-transactions':  '金融与支付',
    'jd-atlantic-council-cbdc': '金融与支付',
    'jd-coin-center':           '金融与支付',
    # 物流与供应链
    'jd-supply-chain-dive':     '物流与供应链',
    'jd-dc-velocity':           '物流与供应链',
    'jd-logistics-viewpoints':  '物流与供应链',
    'jd-freightwaves':          '物流与供应链',
    'jd-loadstar':              '物流与供应链',
    'jd-supplychainbrain':      '物流与供应链',
    # 具身智能与机器人
    'jd-the-robot-report':      '具身智能与机器人',
    'jd-ieee-spectrum-robotics':'具身智能与机器人',
    # 智能硬件
    'jd-fierce-electronics':    '智能硬件',
    'jd-cleantechnica':         '智能硬件',
    'jd-electrek':              '智能硬件',
    'jd-electrive':             '智能硬件',
    'jd-rcr-wireless':          '智能硬件',
    'jd-canary-media':          '智能硬件',
    # AI基础设施
    'jd-arxiv-lg':              'AI基础设施',
    'jd-chip-huyen':            'AI基础设施',
    'jd-interconnects':         'AI基础设施',
    'jd-karpathy':              'AI基础设施',
    'jd-lillog':                'AI基础设施',
    'jd-fastai':                'AI基础设施',
    'jd-import-ai':             'AI基础设施',
    'jd-a16z':                  'AI基础设施',
    'jd-latent-space':          'AI基础设施',
    'jd-simonwillison':         'AI基础设施',
    'jd-langchain-blog':        'AI基础设施',
    'jd-swyx':                  'AI基础设施',
    'jd-the-gradient':          'AI基础设施',
    'jd-towards-ds':            'AI基础设施',
    'jd-lesswrong':             'AI基础设施',
    'jd-qbitai':                'AI基础设施',
    'jd-techcrunch-ai':         'AI基础设施',
    'jd-venturebeat-ai':        'AI基础设施',
    'jd-mit-tech-review':       'AI基础设施',
    'jd-bloomberg-tech':        'AI基础设施',
    'jd-36kr-ai':               'AI基础设施',
    'jd-leiphone':              'AI基础设施',
}

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

def _parse_pub_date(date_str):
    if not date_str:
        return datetime.now(timezone.utc)
    try:
        if 'T' in date_str:
            fmt = '%Y-%m-%dT%H:%M:%S.%f' if '.' in date_str else '%Y-%m-%dT%H:%M:%S'
        else:
            fmt = '%Y-%m-%d %H:%M:%S'
        dt = datetime.strptime(date_str, fmt)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except ValueError:
        return datetime.now(timezone.utc)


def get_jd_articles_from_db(tier_filter=None, team_filter=None, limit=200,
                             shortlist=False):
    """Fetch jd- articles sorted by score desc. Optionally filter by signal_tier or team.
    shortlist=True: top 30 scored articles from last 14 days (score >= 55).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    base = """
        SELECT id, feed_name, article_title, article_link, published_date,
               raw_content, criteria_score, criteria_reason, criteria, signal_tier
        FROM articles
        WHERE feed_name LIKE 'jd-%'
    """
    params = []
    if shortlist:
        base += " AND criteria_score IS NOT NULL AND criteria_score >= 55 AND published_date >= date('now', '-14 days')"
    if tier_filter:
        base += " AND signal_tier = ?"
        params.append(tier_filter)
    if team_filter:
        base += " AND criteria LIKE ?"
        params.append(f'%{team_filter}%')
    base += " ORDER BY criteria_score DESC, published_date DESC LIMIT ?"
    params.append(30 if shortlist else limit)
    c.execute(base, params)
    rows = c.fetchall()
    conn.close()
    return rows


def _rows_to_rss_articles(rows):
    articles = []
    for row in rows:
        src = JD_SOURCE_MAP.get(row['feed_name'], {})
        score = row['criteria_score']
        reason = row['criteria_reason'] or ''
        score_str = f"[{int(score)}分] " if score is not None else ""
        articles.append({
            'title': f"{score_str}{row['article_title']}",
            'link': row['article_link'],
            'published': _parse_pub_date(row['published_date']),
            'summary': f"{reason}\n\n{row['raw_content'] or ''}",
            'source': src.get('label', row['feed_name']),
        })
    return articles


TEAM_PLATE_COLORS = {
    '国内业务': '#2563eb', '本地生活': '#2563eb', '国际业务': '#2563eb', '内容': '#2563eb',
    '营销产品': '#059669', '生态产品': '#059669', '设计用研': '#059669',
    '流量策略': '#d97706', '搜推业务': '#d97706',
    '智能零售': '#7c3aed', '搜推技术': '#7c3aed', 'AI Infra': '#7c3aed', '智能客服': '#7c3aed',
    '交易产研': '#0891b2', '财经': '#0891b2', '商品': '#0891b2',
    '安全风控': '#0891b2', '数据资产': '#0891b2', '营销&用户系统': '#0891b2',
    '技术保障': '#4b5563', '效能与中间件': '#4b5563', '数据库与存储': '#4b5563', '数据计算': '#4b5563',
    '商业智能': '#dc2626', '产品架构/技术架构': '#dc2626',
}

ALL_TEAMS = list(TEAM_PLATE_COLORS.keys())

PLATE_GROUPS = [
    # (plate_name, teams, color, objective)
    ('业务产研', ['国内业务', '本地生活', '国际业务', '内容'], '#2563eb',
     '落地各重点板块和业务场景，通过产研能力建设驱动零售业务高速增长'),
    ('产品体验', ['营销产品', '生态产品', '设计用研'], '#059669',
     '以用户体验为中心，持续提升用户活跃和业务转化，并赋能经营能力'),
    ('流量策略', ['流量策略', '搜推业务'], '#d97706',
     '通过统一化策略，整合全链路人-货-场的流量机制，提升流量价值'),
    ('智能板块', ['智能零售', '搜推技术', 'AI Infra', '智能客服'], '#7c3aed',
     '建设智能算法、数据和基础引擎，全面支持零售创新应用落地核心场域'),
    ('应用架构', ['交易产研', '财经', '商品', '安全风控', '数据资产', '营销&用户系统'], '#0891b2',
     '通过应用架构、端架构、数据架构全面升级，提升技术效率、支持业务发展创新'),
    ('基础设施', ['技术保障', '效能与中间件', '数据库与存储', '数据计算'], '#4b5563', ''),
    ('战略规划', ['商业智能', '产品架构/技术架构'], '#dc2626', ''),
]

# team name → plate name  (built from PLATE_GROUPS)
TEAM_TO_PLATE = {
    team: plate_name
    for plate_name, teams, *_ in PLATE_GROUPS
    for team in teams
}


def _team_badges_html(primary_teams, cc_teams):
    if not primary_teams and not cc_teams:
        return ''
    badges = []
    for t in (primary_teams or [])[:2]:
        badges.append(
            f'<span title="主责团队" '
            f'style="background:#f3f4f6;color:#6b7280;border:1px solid #e5e7eb;'
            f'padding:1px 7px;border-radius:8px;font-size:10px;font-weight:500;'
            f'margin-right:3px">⚡ {t}</span>'
        )
    for t in (cc_teams or [])[:3]:
        badges.append(
            f'<span title="抄送知悉" '
            f'style="background:#f9fafb;color:#9ca3af;border:1px solid #f3f4f6;'
            f'padding:1px 7px;border-radius:8px;font-size:10px;font-weight:400;'
            f'margin-right:3px">👁 {t}</span>'
        )
    return '<div style="margin-top:5px">' + ''.join(badges) + '</div>'


def _get_team_stats():
    """Return {team: {primary: N, cc: N}} by parsing criteria JSON from DB."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT criteria FROM articles WHERE feed_name LIKE 'jd-%' AND criteria LIKE '%primary_teams%'")
    counts = {t: {'primary': 0, 'cc': 0} for t in ALL_TEAMS}
    for (crit,) in c.fetchall():
        try:
            bd = json.loads(crit)
            for t in bd.get('primary_teams', []):
                if t in counts:
                    counts[t]['primary'] += 1
            for t in bd.get('cc_teams', []):
                if t in counts:
                    counts[t]['cc'] += 1
        except Exception:
            pass
    conn.close()
    return counts


def _score_color(score):
    if score is None:
        return '#888'
    if score >= 75:
        return '#c0392b'
    if score >= 55:
        return '#e67e22'
    if score >= 35:
        return '#27ae60'
    return '#7f8c8d'


def _score_bar(score):
    if score is None:
        return '<span style="color:#888">未打分</span>'
    pct = min(100, max(0, int(score)))
    color = _score_color(score)
    return (f'<div style="display:inline-flex;align-items:center;gap:8px">'
            f'<div style="width:80px;height:8px;background:#eee;border-radius:4px">'
            f'<div style="width:{pct}%;height:100%;background:{color};border-radius:4px"></div></div>'
            f'<strong style="color:{color}">{pct}</strong></div>')


def _get_source_stats():
    """Per-source article counts and avg score from DB."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT feed_name,
               COUNT(*) total,
               COUNT(criteria_score) scored,
               ROUND(AVG(criteria_score), 0) avg_score,
               COUNT(CASE WHEN criteria_score >= 70 THEN 1 END) high
        FROM articles
        WHERE feed_name LIKE 'jd-%'
        GROUP BY feed_name
        ORDER BY high DESC, avg_score DESC
    """)
    rows = c.fetchall()
    conn.close()
    return {r['feed_name']: dict(r) for r in rows}


def render_jd_browser(rows, title, feed_url, active_team=None, shortlist=False, page='home'):
    total = len(rows)
    scored = sum(1 for r in rows if r['criteria_score'] is not None)
    high = sum(1 for r in rows if (r['criteria_score'] or 0) >= 70)

    # ── Article cards ────────────────────────────────────────────────────
    cards = []
    for row in rows:
        src = JD_SOURCE_MAP.get(row['feed_name'], {})
        label = src.get('label', row['feed_name'])
        category = src.get('category', '')
        tier = row['signal_tier'] or src.get('tier', 2)
        score = row['criteria_score']
        reason = row['criteria_reason'] or ''

        breakdown_html = ''
        teams_html = ''
        action_html = ''
        domain_badge = ''
        if row['criteria']:
            try:
                bd = json.loads(row['criteria'])
                # Score breakdown row
                parts = []
                for k, v, max_v in [('相关性', bd.get('relevance'), 40),
                                     ('来源', bd.get('source_tier'), 25),
                                     ('新鲜度', bd.get('novelty'), 25),
                                     ('收敛', bd.get('convergence'), 10)]:
                    if v is not None:
                        parts.append(f'<span style="margin-right:10px;color:#666">{k}&nbsp;<strong>{v}</strong><span style="color:#ccc">/{max_v}</span></span>')
                if bd.get('github_bonus'):
                    parts.append(f'<span style="color:#6f42c1">⭐GitHub +{bd["github_bonus"]}</span>')
                breakdown_html = '<div style="margin-top:6px;font-size:11px;color:#777">' + ''.join(parts) + '</div>'
                teams_html = _team_badges_html(
                    bd.get('primary_teams') or bd.get('relevant_teams', []),
                    bd.get('cc_teams', [])
                )
                # Action note — the key output for team leads
                note = bd.get('action_note', '')
                if note:
                    action_html = (
                        f'<div style="margin-top:10px;padding:9px 12px;'
                        f'background:#fffbeb;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;'
                        f'font-size:12px;color:#92400e;line-height:1.6">'
                        f'<span style="font-weight:600;margin-right:4px">📋 团队行动</span>{note}</div>'
                    )
                domain = bd.get('domain')
                if domain:
                    domain_badge = (
                        f'<span style="background:#1a1a2e;color:#e2e8f0;'
                        f'padding:3px 10px;border-radius:10px;font-size:11px;font-weight:600;'
                        f'letter-spacing:.3px">🗂 {domain}</span>'
                    )
            except Exception:
                pass

        pub = _parse_pub_date(row['published_date']).strftime('%Y-%m-%d %H:%M')

        # ── 3 tags: domain / plate / standpoint ──────────────────────────
        def _pill(text, bg, color, border):
            return (f'<span style="font-size:10px;background:{bg};color:{color};'
                    f'border:1px solid {border};padding:1px 7px;border-radius:6px;'
                    f'margin-right:4px;font-weight:500;white-space:nowrap">{text}</span>')

        tag_pills = []
        # 1. business domain
        d_label = FEED_DOMAIN_MAP.get(row['feed_name'], '')
        if d_label:
            tag_pills.append(_pill(d_label, '#f3f4f6', '#374151', '#e5e7eb'))
        # 2. team plate (use first primary_team → plate name)
        plate_label = ''
        if row['criteria']:
            try:
                _bd = json.loads(row['criteria'])
                _pt = (_bd.get('primary_teams') or _bd.get('relevant_teams') or [])
                if _pt:
                    plate_label = TEAM_TO_PLATE.get(_pt[0], '')
            except Exception:
                pass
        if plate_label:
            p_color = next((c for pn, pt, c, *_ in PLATE_GROUPS if pn == plate_label), '#6b7280')
            tag_pills.append(_pill(plate_label, p_color + '12', p_color, p_color + '40'))
        # 3. standpoint
        sp_label = STANDPOINT_MAP.get(row['feed_name'], '')
        if sp_label:
            tag_pills.append(_pill(sp_label, '#f0f9ff', '#0369a1', '#bae6fd'))

        tags_row = (
            '<div style="margin-top:6px;display:flex;flex-wrap:wrap;align-items:center;gap:0">'
            + ''.join(tag_pills) + '</div>'
        ) if tag_pills else ''

        cards.append(f"""
        <div style="border:1px solid #e5e7eb;border-left:4px solid {_score_color(score)};
                    border-radius:8px;padding:16px 18px;margin-bottom:12px;background:white;
                    box-shadow:0 1px 3px rgba(0,0,0,.05)">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
                <div style="flex:1;min-width:0">
                    <div style="margin-bottom:8px">{domain_badge if domain_badge else ''}</div>
                    <a href="{row['article_link']}" target="_blank"
                       style="font-size:14px;font-weight:600;color:#111827;text-decoration:none;line-height:1.5;display:block">
                       {row['article_title']}
                    </a>
                    <div style="margin-top:6px;font-size:11px;color:#9ca3af">{label} · {pub}</div>
                    {tags_row}
                    {action_html}
                    {f'<div style="margin-top:8px;font-size:11px;color:#6b7280;line-height:1.5;border-top:1px solid #f3f4f6;padding-top:7px">{reason}</div>' if reason and not action_html else ''}
                    {breakdown_html}
                </div>
                <div style="text-align:center;min-width:64px;flex-shrink:0">
                    {_score_bar(score)}
                    <div style="font-size:10px;color:#9ca3af;margin-top:3px">情报分</div>
                </div>
            </div>
        </div>""")

    card_list = '\n'.join(cards) if cards else '<p style="color:#9ca3af;padding:40px;text-align:center">暂无数据 — 请先运行 jd_fetch_score.py</p>'
    if shortlist:
        banner = (
            '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;'
            'padding:12px 16px;margin-bottom:16px;font-size:13px;color:#1e40af;line-height:1.7">'
            '<strong>📋 今日简报候选</strong> — 过去14天评分≥55分，共 <strong>' + str(len(rows)) + '</strong> 篇。'
            '请3位审阅者各自标出值得纳入总裁简报的文章（目标10~20篇）。'
            '重点看 <strong>📋 团队行动</strong> 栏，判断该信号是否需要CTO层面响应。'
            '</div>'
        )
        cards_html = banner + card_list
    else:
        cards_html = card_list

    # ── Sidebar: scoring rules ───────────────────────────────────────────
    scoring_rules_html = """
    <div class="sidebar-card">
      <div class="sidebar-title">📐 情报评分规则</div>
      <table style="width:100%;border-collapse:collapse;font-size:12px">
        <thead>
          <tr style="border-bottom:1px solid #e5e7eb">
            <th style="text-align:left;padding:4px 0;color:#6b7280;font-weight:500">维度</th>
            <th style="text-align:right;padding:4px 0;color:#6b7280;font-weight:500">满分</th>
          </tr>
        </thead>
        <tbody>
          <tr><td style="padding:5px 0;color:#374151;font-weight:600">京东业务相关性</td><td style="text-align:right;font-weight:700;color:#c0392b">40</td></tr>
          <tr><td style="padding:5px 0;color:#374151">来源层级</td><td style="text-align:right;font-weight:600;color:#1a1a2e">25</td></tr>
          <tr><td style="padding:5px 0;color:#374151">新鲜度/原创性</td><td style="text-align:right;font-weight:600;color:#1a1a2e">25</td></tr>
          <tr><td style="padding:5px 0;color:#374151">信号收敛性</td><td style="text-align:right;font-weight:600;color:#1a1a2e">10</td></tr>
          <tr style="border-top:1px solid #e5e7eb">
            <td style="padding:5px 0;color:#7c3aed">arXiv GitHub⭐≥500</td>
            <td style="text-align:right;font-weight:600;color:#7c3aed">+10</td>
          </tr>
        </tbody>
      </table>
      <div style="margin-top:10px;font-size:11px;color:#6b7280;line-height:1.6">
        <span style="display:inline-block;width:10px;height:10px;background:#c0392b;border-radius:2px;margin-right:4px"></span>≥75 高优先级<br>
        <span style="display:inline-block;width:10px;height:10px;background:#e67e22;border-radius:2px;margin-right:4px"></span>55–74 中优先级<br>
        <span style="display:inline-block;width:10px;height:10px;background:#27ae60;border-radius:2px;margin-right:4px"></span>35–54 低优先级
      </div>
    </div>"""

    # ── Sidebar: distribution stats — all computed from the same `rows` ──
    # 1. Business domain distribution
    domain_counter = {}
    for row in rows:
        if not row['criteria']:
            continue
        try:
            domain = json.loads(row['criteria']).get('domain')
            if domain:
                domain_counter[domain] = domain_counter.get(domain, 0) + 1
        except Exception:
            pass
    domain_sorted = sorted(domain_counter.items(), key=lambda x: -x[1])
    domain_total = sum(domain_counter.values()) or 1
    domain_rows = ''
    for domain, n in domain_sorted[:14]:
        pct = int(n / domain_total * 100)
        domain_rows += (
            f'<div style="margin-bottom:5px">'
            f'<div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px">'
            f'<span style="color:#374151;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:140px" title="{domain}">{domain}</span>'
            f'<span style="color:#9ca3af;flex-shrink:0;margin-left:4px">{n}</span></div>'
            f'<div style="height:3px;background:#f3f4f6;border-radius:2px">'
            f'<div style="height:100%;width:{max(pct,2)}%;background:#1a1a2e;border-radius:2px"></div></div>'
            f'</div>'
        )

    domain_stats_html = f"""
    <div class="sidebar-card">
      <div class="sidebar-title">🗂 业务领域分布</div>
      {domain_rows if domain_rows else '<div style="font-size:11px;color:#9ca3af">评分完成后显示</div>'}
    </div>"""

    # 2. Standpoint distribution — from same rows
    standpoint_counts = {}
    for row in rows:
        sp = STANDPOINT_MAP.get(row['feed_name'], '')
        if sp:
            standpoint_counts[sp] = standpoint_counts.get(sp, 0) + 1
    sp_total = sum(standpoint_counts.values()) or 1
    sp_order = ['关键玩家','资本动向','顶尖研究者','技术社区','科技媒体','行业媒体','政策与专利']
    sp_colors = {'关键玩家':'#7c3aed','资本动向':'#059669','顶尖研究者':'#d97706',
                 '技术社区':'#6366f1','科技媒体':'#2563eb','行业媒体':'#0891b2','政策监管':'#dc2626',
                 '内部情报':'#be185d'}
    sp_rows = ''
    for sp in sp_order:
        n = standpoint_counts.get(sp, 0)
        if not n:
            continue
        pct = int(n / sp_total * 100)
        color = sp_colors.get(sp, '#9ca3af')
        sp_rows += (
            f'<div style="margin-bottom:5px">'
            f'<div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px">'
            f'<span style="color:#374151">{sp}</span>'
            f'<span style="color:#9ca3af">{n}</span></div>'
            f'<div style="height:3px;background:#f3f4f6;border-radius:2px">'
            f'<div style="height:100%;width:{max(pct,2)}%;background:{color};border-radius:2px"></div></div>'
            f'</div>'
        )

    standpoint_stats_html = f"""
    <div class="sidebar-card" style="margin-top:16px">
      <div class="sidebar-title">🎯 观点立场分布</div>
      {sp_rows if sp_rows else '<div style="font-size:11px;color:#9ca3af">暂无数据</div>'}
    </div>"""

    # ── Sidebar: team filter + stats — from same rows ───────────────────
    team_stats_rows = {t: {'primary': 0, 'cc': 0} for t in ALL_TEAMS}
    for row in rows:
        if not row['criteria']:
            continue
        try:
            bd = json.loads(row['criteria'])
            for t in bd.get('primary_teams', []):
                if t in team_stats_rows:
                    team_stats_rows[t]['primary'] += 1
            for t in bd.get('cc_teams', []):
                if t in team_stats_rows:
                    team_stats_rows[t]['cc'] += 1
        except Exception:
            pass
    team_stats = team_stats_rows
    team_rows = []
    team_rows.append(
        f'<div style="margin-bottom:8px">'
        f'<a href="/jd" style="font-size:11px;color:{"#1a1a2e" if not active_team else "#9ca3af"};'
        f'text-decoration:none;font-weight:{"700" if not active_team else "400"}">全部团队</a></div>'
    )
    for plate_name, plate_teams, plate_color, *_ in PLATE_GROUPS:
        plate_primary = sum(team_stats.get(t, {}).get('primary', 0) for t in plate_teams)
        plate_cc      = sum(team_stats.get(t, {}).get('cc', 0) for t in plate_teams)
        team_rows.append(
            f'<div style="font-size:10px;color:#9ca3af;font-weight:600;margin:10px 0 4px;'
            f'text-transform:uppercase;letter-spacing:.4px;display:flex;justify-content:space-between;align-items:center">'
            f'<span>{plate_name}</span>'
            f'<span style="font-weight:400;font-size:9px;letter-spacing:0;color:#bbb">'
            f'⚡{plate_primary}&nbsp;👁{plate_cc}</span></div>'
        )
        for t in plate_teams:
            is_active = active_team == t
            st = team_stats.get(t, {})
            p_n, cc_n = st.get('primary', 0), st.get('cc', 0)
            bar_total = max(p_n + cc_n, 1)
            p_pct = int(p_n / bar_total * 100)
            team_rows.append(
                f'<div style="margin-bottom:5px">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px">'
                f'<a href="/jd?team={t}" style="font-size:11px;color:{plate_color};text-decoration:none;'
                f'font-weight:{"700" if is_active else "500"};'
                f'background:{"" if not is_active else plate_color + "15"};'
                f'padding:1px 5px;border-radius:3px">{t}</a>'
                f'<span style="font-size:10px;white-space:nowrap;margin-left:4px">'
                f'<span style="color:{plate_color};font-weight:600" title="需行动">⚡{p_n}</span>'
                f'&nbsp;<span style="color:#9ca3af" title="知悉即可">👁{cc_n}</span></span>'
                f'</div>'
                + (
                    f'<div style="height:3px;background:#f3f4f6;border-radius:2px;overflow:hidden" title="⚡{p_n} 需行动 / 👁{cc_n} 知悉">'
                    f'<div style="height:100%;width:{p_pct}%;background:{plate_color};border-radius:2px"></div>'
                    f'</div>'
                    if (p_n + cc_n) > 0 else ''
                )
                + f'</div>'
            )

    # Sector-level summary (5 working sectors, not individual teams)
    sector_rows = []
    for plate_name, plate_teams, plate_color, *_ in PLATE_GROUPS:
        plate_primary = sum(team_stats.get(t, {}).get('primary', 0) for t in plate_teams)
        plate_cc      = sum(team_stats.get(t, {}).get('cc', 0) for t in plate_teams)
        total_sig = plate_primary + plate_cc
        if total_sig == 0:
            continue
        p_pct = int(plate_primary / total_sig * 100)
        sector_rows.append(
            f'<div style="margin-bottom:6px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;font-size:11px;margin-bottom:2px">'
            f'<span style="color:{plate_color};font-weight:600">{plate_name}</span>'
            f'<span style="color:#9ca3af;font-size:10px">⚡{plate_primary} 👁{plate_cc}</span></div>'
            f'<div style="height:4px;background:#f3f4f6;border-radius:2px">'
            f'<div style="height:100%;width:{max(p_pct,2)}%;background:{plate_color};border-radius:2px;opacity:.8"></div></div>'
            f'</div>'
        )

    team_filter_html = f"""
    <div class="sidebar-card" style="margin-top:16px">
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:10px">
        <div class="sidebar-title" style="margin-bottom:0">🏢 团队板块覆盖</div>
        <div style="font-size:9px;color:#9ca3af">⚡行动&nbsp;👁知悉</div>
      </div>
      {''.join(sector_rows)}
    </div>"""

    active_home = 'active' if page == 'home' else ''
    active_archive = 'active' if page == 'all' else ''

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
  * {{ box-sizing:border-box }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
          background:#f3f4f6; color:#1a1a2e }}
  .header {{ background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
             color:white; padding:20px 32px }}
  .header h1 {{ margin:0 0 4px; font-size:20px; font-weight:700 }}
  .header .meta {{ font-size:12px; opacity:.65 }}
  .nav {{ background:#16213e; padding:0 32px; display:flex; align-items:center }}
  .nav a {{ color:rgba(255,255,255,.65); text-decoration:none; padding:10px 14px;
            font-size:13px; border-bottom:2px solid transparent; display:inline-block }}
  .nav a:hover, .nav a.active {{ color:white; border-bottom-color:#e74c3c }}
  .nav .rss {{ margin-left:auto; font-size:12px; opacity:.5 }}
  .nav .rss:hover {{ opacity:1 }}
  .outer {{ display:flex; gap:20px; max-width:1200px; margin:20px auto; padding:0 20px }}
  .feed {{ flex:1; min-width:0 }}
  .sidebar {{ width:240px; flex-shrink:0 }}
  .sidebar-card {{ background:white; border:1px solid #e5e7eb; border-radius:8px;
                   padding:14px 16px; box-shadow:0 1px 3px rgba(0,0,0,.04) }}
  .sidebar-title {{ font-size:12px; font-weight:700; color:#374151;
                    margin-bottom:10px; text-transform:uppercase; letter-spacing:.5px }}
  .topstats {{ display:flex; gap:10px; margin-bottom:16px }}
  .stat {{ background:white; border-radius:8px; padding:12px 16px; border:1px solid #e5e7eb;
           flex:1; text-align:center; box-shadow:0 1px 2px rgba(0,0,0,.04) }}
  .stat .n {{ font-size:22px; font-weight:700; color:#1a1a2e }}
  .stat .l {{ font-size:10px; color:#9ca3af; margin-top:2px }}
  @media(max-width:768px) {{ .sidebar {{ display:none }} .outer {{ padding:0 12px }} }}
</style>
</head>
<body>
<div class="header">
  <h1>🏪 JD全球前沿情报系统</h1>
  <div class="meta">京东集团CTO部门 · 总裁简报原材料 · 按情报分排序</div>
</div>
{_jd_nav("all" if active_archive else "")}
<div class="outer">
  <div class="feed">
    <div class="topstats">
      <div class="stat"><div class="n">{total}</div><div class="l">全部文章</div></div>
      <div class="stat"><div class="n">{scored}</div><div class="l">已打分</div></div>
      <div class="stat"><div class="n">{high}</div><div class="l">高分 ≥70</div></div>
      <div class="stat"><div class="n">{total - scored}</div><div class="l">待打分</div></div>
    </div>
    {cards_html}
  </div>
  <div class="sidebar">
    {scoring_rules_html}
    {domain_stats_html}
    {standpoint_stats_html}
    {team_filter_html}
  </div>
</div>
</body>
</html>"""


def _get_jd_rss(tier_filter, cache_obj, feed_url, feed_title):
    global jd_cache, jd_t1_cache, jd_t2_cache
    current_time = time.time()
    if cache_obj["feed_xml"] is None or (current_time - cache_obj["timestamp"] > CACHE_DURATION):
        rows = get_jd_articles_from_db(tier_filter=tier_filter, limit=100)
        articles = _rows_to_rss_articles(rows)
        gen = RSSGenerator(feed_title, feed_link=feed_url,
                           feed_description="京东零售AI情报 — 按情报分排序")
        cache_obj["feed_xml"] = gen.generate_xml_string(articles)
        cache_obj["timestamp"] = current_time
        cache_obj["article_count"] = len(articles)
    return cache_obj["feed_xml"]


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


# ── JD Intelligence routes ────────────────────────────────────────────────────

def _jd_nav(active: str) -> str:
    """Return the shared nav bar. active: 'retail'|'buzz'|'capital'|'sources'|'all'"""
    def _a(key, href, label):
        cls = ' class="active"' if key == active else ''
        return f'<a href="{href}"{cls}>{label}</a>'
    return (
        '<div class="nav">'
        + _a('retail',  '/jd/retail',   '🏭 产业共识')
        + _a('buzz',    '/jd/buzz',     '🔥 社区热议')
        + _a('capital', '/jd/capital',  '💰 资金流向')
        + _a('sources', '/jd/sources',  '📡 情报源')
        + _a('all',     '/jd/all',      '🗃 全部归档')
        + '<a href="/jd/feed.xml" style="margin-left:auto;color:rgba(255,255,255,.65);'
          'text-decoration:none;padding:10px 14px;font-size:13px">RSS ↗</a>'
        + '</div>'
    )


# ── Community/thread feed registry ──────────────────────────────────────────
# Only include thread/discussion platforms here (not editorial media).
# Format: feed_name → (display_label, accent_color, bg_color, border_color)
_COMMUNITY_FEEDS = {
    'jd-huggingface-blog': ('HuggingFace Blog', '#6b21a8', '#fdf4ff', '#e9d5ff'),
    'jd-reddit-ml':        ('Reddit r/ML',       '#dc2626', '#fef2f2', '#fecaca'),
    'jd-reddit-localllama':('Reddit r/LocalLLaMA','#ea580c','#fff7ed', '#fed7aa'),
    'jd-reddit-artificial':('Reddit r/artificial','#b45309','#fffbeb', '#fde68a'),
    'jd-producthunt-ai':   ('Product Hunt AI',   '#db2777', '#fdf2f8', '#fbcfe8'),
    'jd-devto-ai':         ('dev.to · AI',       '#1d4ed8', '#eff6ff', '#bfdbfe'),
    'jd-juejin-ai':        ('掘金 Juejin',        '#0891b2', '#ecfeff', '#a5f3fc'),
    'jd-v2ex':             ('V2EX',              '#059669', '#ecfdf5', '#a7f3d0'),
    'jd-sspai':            ('少数派 SSPAI',        '#7c3aed', '#f5f3ff', '#ddd6fe'),
    'jd-linux-do':         ('Linux.do',          '#16a34a', '#f0fdf4', '#bbf7d0'),
    'jd-lobsters-ai':      ('Lobste.rs · AI',    '#b45309', '#fffbeb', '#fde68a'),
    'jd-hn-showhn':        ('Show HN',           '#d97706', '#fffbeb', '#fef3c7'),
}

# Chinese thread communities (subset of _COMMUNITY_FEEDS)
CN_FEEDS = ['jd-juejin-ai', 'jd-v2ex', 'jd-sspai', 'jd-linux-do']

# Feeds sorted by engagement metric (replies/upvotes) rather than AI score
_ENGAGEMENT_SORT_FEEDS = {
    'jd-v2ex', 'jd-lobsters-ai', 'jd-hn-showhn', 'jd-sspai', 'jd-huggingface-blog'
}
_ENGAGEMENT_SORTED_FEEDS = _ENGAGEMENT_SORT_FEEDS  # alias for display logic

def _parse_reply_count(raw: str) -> int:
    """Extract engagement count from raw_content for community feeds."""
    import re as _re2
    # HuggingFace upvotes: [👍42赞]
    m = _re2.search(r'👍(\d+)赞', raw or '')
    if m:
        return int(m.group(1))
    # V2EX replies
    m = _re2.search(r'回复:(\d+)条', raw or '')
    if m:
        return int(m.group(1))
    # Lobste.rs / HN votes+comments
    m = _re2.search(r'💬(\d+)评论', raw or '')
    if m:
        return int(m.group(1))
    # Reddit comments
    m = _re2.search(r'comments=(\d+)', raw or '')
    if m:
        return int(m.group(1))
    # Generic upvote pattern
    m = _re2.search(r'⬆(\d+)', raw or '')
    if m:
        return int(m.group(1))
    return 0

def _clean_reason_for_display(reason: str, limit: int = 160) -> str:
    """Strip scoring noise from criteria_reason for clean display."""
    import re as _re3
    if not reason:
        return ''
    # Remove score prefix like "85分：" or "评分85："
    reason = _re3.sub(r'^[\d]+分[：:]?\s*', '', reason)
    reason = _re3.sub(r'^评分[\d]+[：:]?\s*', '', reason)
    reason = reason.strip()
    return reason[:limit] + '…' if len(reason) > limit else reason

# Low-signal markers used by _is_product_innovation()
_LOW_SIGNAL_MARKERS = [
    '纯学术', '无产品路径', '无落地', '无商业价值', '仅有愿景', '概念演示',
    '纯PR稿', '广告', '软文', '主流媒体已广泛覆盖', '人人皆知',
    '纯理论推导', '无实证', '数学推导', '消融实验',
]

def _is_product_innovation(reason: str, score) -> bool:
    """Return True if article passes product innovation bar (not low-signal)."""
    if not reason:
        return True
    if score is not None and float(score) < 40:
        return False
    low_count = sum(1 for s in _LOW_SIGNAL_MARKERS if s.lower() in reason.lower())
    return low_count < 2

def _community_feed_section(fn: str, items: list, label: str,
                             accent: str, bg: str, border: str) -> str:
    """Render one community feed card section."""
    import re as _re4
    if not items:
        return ''

    # Sort label
    if fn == 'jd-huggingface-blog':
        sort_label = '按 Upvotes 降序 · 近30天'
    elif fn in _ENGAGEMENT_SORTED_FEEDS:
        sort_label = '按讨论热度 · 近30天'
    else:
        sort_label = '按AI相关性 · 近30天'

    cards = ''
    for item in items[:15]:
        title = item.get('article_title') or ''
        link  = item.get('article_link') or '#'
        pub   = item.get('published_date', '')[:10]
        score = item.get('criteria_score')
        raw   = item.get('raw_content', '') or ''

        # Popularity badge
        eng = _parse_reply_count(raw)
        if eng > 0:
            if fn == 'jd-huggingface-blog':
                eng_icon, eng_label = '👍', f'{eng} upvotes'
            elif fn == 'jd-v2ex':
                eng_icon, eng_label = '💬', f'{eng} 回复'
            elif fn in ('jd-lobsters-ai', 'jd-hn-showhn'):
                eng_icon, eng_label = '⬆', f'{eng} 分'
            elif fn == 'jd-sspai':
                eng_icon, eng_label = '❤', f'{eng} 赞'
            else:
                eng_icon, eng_label = '💬', str(eng)
            eng_s = (f'<span style="background:#fef3c7;color:#92400e;border:1px solid #fde68a;'
                     f'border-radius:4px;padding:1px 6px;font-size:10px;font-weight:600;'
                     f'margin-left:6px">{eng_icon} {eng_label}</span>')
        else:
            eng_s = ''

        # Score badge
        score_s = ''
        if score is not None:
            sc = int(score)
            sc_color = '#059669' if sc >= 70 else '#d97706' if sc >= 50 else '#6b7280'
            score_s = (f'<span style="background:#f0fdf4;color:{sc_color};border:1px solid #bbf7d0;'
                       f'border-radius:4px;padding:1px 5px;font-size:10px;font-weight:600">'
                       f'{sc}分</span>')

        # Chinese summary from criteria_reason
        reason = _clean_reason_for_display(item.get('criteria_reason') or '', limit=160)
        reason_html = (
            f'<div style="font-size:11px;color:#6b7280;line-height:1.6;margin-top:5px;'
            f'padding:5px 8px;border-left:2px solid #e5e7eb;background:#f9fafb;">'
            f'{reason}</div>'
        ) if reason else ''

        cards += (
            f'<div style="padding:8px 0;border-top:1px solid #f3f4f6">'
            f'<div style="display:flex;align-items:flex-start;gap:6px;flex-wrap:wrap">'
            f'<a href="{link}" target="_blank" style="font-size:12px;font-weight:600;'
            f'color:#111827;text-decoration:none;line-height:1.5;flex:1;min-width:0">'
            f'{title}</a>'
            f'<div style="display:flex;align-items:center;gap:4px;flex-shrink:0">'
            f'{score_s}{eng_s}</div>'
            f'</div>'
            f'{reason_html}'
            f'<div style="font-size:10px;color:#9ca3af;margin-top:3px">{pub}</div>'
            f'</div>'
        )

    return (
        f'<div style="background:{bg};border:1px solid {border};border-radius:8px;'
        f'padding:14px 16px;margin-bottom:16px">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">'
        f'<span style="font-size:13px;font-weight:700;color:{accent}">{label}</span>'
        f'<span style="font-size:10px;color:#9ca3af">{sort_label}</span>'
        f'</div>'
        f'{cards}'
        f'</div>'
    )


@app.route('/jd')
def jd_home():
    from flask import redirect as _redirect
    return _redirect('/jd/retail')


@app.route('/jd/_old_home')
def jd_home_old():
    """
    Cluster-based briefing view (archived — main entry is now /jd/retail).
    """
    from flask import request
    team = request.args.get('team', '').strip() or None

    # Team filter: show article list for that team (unchanged behavior)
    if team:
        rows = get_jd_articles_from_db(tier_filter=None, team_filter=team, shortlist=True)
        return render_jd_browser(rows, f"JD情报 · {team}", None,
                                 active_team=team, shortlist=True)

    # ── Default: cluster-based briefing ──────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS intelligence_clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme_label TEXT NOT NULL, article_ids TEXT NOT NULL,
            article_titles TEXT NOT NULL, article_feed_names TEXT NOT NULL,
            article_links TEXT NOT NULL, article_scores TEXT NOT NULL,
            domains TEXT, standpoints TEXT, source_count INTEGER DEFAULT 0,
            convergence_score INTEGER DEFAULT 0, why_convergent TEXT,
            synthesis_text TEXT, strategic_question TEXT,
            recommended_action TEXT, created_at TEXT NOT NULL
        )
    """)
    conn.commit()

    clusters = conn.execute(
        "SELECT * FROM intelligence_clusters ORDER BY convergence_score DESC"
    ).fetchall()

    # Unclustered high-scoring articles from last 14 days
    clustered_ids = []
    for c in clusters:
        try: clustered_ids.extend(json.loads(c['article_ids']))
        except: pass

    if clustered_ids:
        ph = ','.join('?' * len(clustered_ids))
        lone_rows = conn.execute(f"""
            SELECT id, feed_name, article_title, article_link,
                   published_date, criteria_score, criteria_reason, criteria, signal_tier
            FROM articles
            WHERE feed_name LIKE 'jd-%'
              AND criteria_score >= 70
              AND published_date >= date('now', '-14 days')
              AND id NOT IN ({ph})
            ORDER BY criteria_score DESC LIMIT 15
        """, clustered_ids).fetchall()
    else:
        lone_rows = conn.execute("""
            SELECT id, feed_name, article_title, article_link,
                   published_date, criteria_score, criteria_reason, criteria, signal_tier
            FROM articles
            WHERE feed_name LIKE 'jd-%'
              AND criteria_score >= 70
              AND published_date >= date('now', '-14 days')
            ORDER BY criteria_score DESC LIMIT 15
        """).fetchall()

    last_run_row = conn.execute(
        "SELECT created_at FROM intelligence_clusters ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    last_run = last_run_row['created_at'][:16].replace('T', ' ') + ' UTC' if last_run_row else None
    conn.close()

    return _render_briefing(clusters, lone_rows, last_run)


def _render_briefing(clusters, lone_rows, last_run):
    """Render the cluster-based briefing homepage."""

    SP_COLORS = {
        '关键玩家':'#7c3aed','资本动向':'#059669','顶尖研究者':'#d97706',
        '技术社区':'#6366f1','科技媒体':'#2563eb','行业媒体':'#0891b2','政策与专利':'#dc2626',
        '内部情报':'#be185d',
    }

    def _sp_pill(sp):
        c = SP_COLORS.get(sp, '#6b7280')
        return (f'<span style="font-size:10px;background:{c}18;color:{c};'
                f'border:1px solid {c}44;padding:2px 8px;border-radius:5px;'
                f'font-weight:600;white-space:nowrap;margin-right:4px">{sp}</span>')

    # Build cluster cards
    cluster_cards_html = []
    for c in clusters:
        try:
            titles     = json.loads(c['article_titles'])
            links      = json.loads(c['article_links'])
            feed_names = json.loads(c['article_feed_names'])
            scores     = json.loads(c['article_scores'])
            standpoints= json.loads(c['standpoints'])
        except:
            continue

        sp_pills = ''.join(_sp_pill(sp) for sp in standpoints)

        art_items = ''.join(
            f'<div style="padding:5px 0;border-top:1px solid #f3f4f6;display:flex;gap:8px;align-items:flex-start">'
            f'<span style="font-size:10px;color:white;background:{SP_COLORS.get(STANDPOINT_MAP.get(fn,""),"#9ca3af")};'
            f'padding:1px 6px;border-radius:3px;white-space:nowrap;flex-shrink:0;margin-top:1px">'
            f'{STANDPOINT_MAP.get(fn,"—")}</span>'
            f'<a href="{lnk}" target="_blank" style="font-size:12px;color:#374151;text-decoration:none;line-height:1.4">'
            f'{t}</a>'
            f'<span style="font-size:10px;color:#9ca3af;white-space:nowrap;margin-left:auto;flex-shrink:0">{sc}分</span>'
            f'</div>'
            for t, lnk, fn, sc in zip(titles, links, feed_names, scores)
        )

        action_html = (
            f'<div style="margin-top:10px;padding:8px 12px;background:#fffbeb;'
            f'border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;'
            f'font-size:12px;color:#92400e;line-height:1.6">'
            f'<strong>📋 建议行动 </strong>{c["recommended_action"]}</div>'
        ) if c['recommended_action'] else ''

        sq = f'<span style="font-size:11px;background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;padding:2px 10px;border-radius:5px;font-weight:600;margin-left:6px">{c["strategic_question"]}</span>' if c['strategic_question'] else ''

        score_color = '#c0392b' if c['convergence_score'] >= 80 else '#e67e22'

        cluster_cards_html.append(f"""
        <div style="border:1px solid #e5e7eb;border-left:4px solid #7c3aed;border-radius:8px;
                    background:white;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.05)">
          <div style="padding:15px 18px 12px;display:flex;gap:12px;align-items:flex-start">
            <div style="flex:1;min-width:0">
              <div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-bottom:6px">
                <span style="font-size:15px;font-weight:700;color:#1a1a2e">🔗 {c['theme_label']}</span>
                {sq}
              </div>
              <div style="margin-bottom:8px">{sp_pills}</div>
              {f'<div style="font-size:13px;color:#374151;line-height:1.7;margin-bottom:6px">{c["synthesis_text"]}</div>' if c['synthesis_text'] else ''}
              {action_html}
            </div>
            <div style="text-align:center;min-width:52px;flex-shrink:0">
              <div style="font-size:20px;font-weight:800;color:{score_color}">{c['convergence_score']}</div>
              <div style="font-size:9px;color:#9ca3af">收敛分</div>
              <div style="font-size:9px;color:#9ca3af;margin-top:2px">{c['source_count']}篇</div>
            </div>
          </div>
          <div style="padding:0 18px 12px;border-top:1px solid #f9fafb">
            {art_items}
          </div>
        </div>""")

    no_clusters_msg = (
        '<div style="padding:50px;text-align:center;background:white;border-radius:8px;'
        'border:1px solid #e5e7eb;color:#9ca3af">'
        '<div style="font-size:28px;margin-bottom:10px">🔍</div>'
        '<div style="font-weight:600;margin-bottom:6px">暂无收敛集群</div>'
        '<div style="font-size:12px;line-height:1.8">运行 <code>python3 jd_intelligence_synthesis.py</code> 生成收敛分析<br>'
        '需要至少50篇已评分文章</div></div>'
    ) if not clusters else ''

    # Lone high-score articles
    lone_cards = []
    for row in lone_rows:
        src   = JD_SOURCE_MAP.get(row['feed_name'], {})
        label = src.get('label', row['feed_name'])
        sp    = STANDPOINT_MAP.get(row['feed_name'], '')
        sp_c  = SP_COLORS.get(sp, '#9ca3af')
        score = row['criteria_score'] or 0
        s_col = '#c0392b' if score >= 75 else '#e67e22'
        reason= row['criteria_reason'] or ''
        pub   = _parse_pub_date(row['published_date']).strftime('%m-%d %H:%M')

        # action note from criteria JSON
        action_note = ''
        if row['criteria']:
            try:
                bd = json.loads(row['criteria'])
                note = bd.get('action_note', '')
                if note:
                    action_note = (f'<div style="margin-top:6px;padding:6px 10px;background:#fffbeb;'
                                   f'border-left:3px solid #f59e0b;border-radius:0 4px 4px 0;'
                                   f'font-size:11px;color:#92400e;line-height:1.5">'
                                   f'<strong>📋 </strong>{note}</div>')
            except: pass

        reason_html = f'<div style="margin-top:4px;font-size:11px;color:#6b7280;line-height:1.5">{reason[:140]}</div>' if reason else ''
        lone_cards.append(
            f'<div style="padding:12px 16px;border-bottom:1px solid #f3f4f6;'
            f'display:flex;align-items:flex-start;gap:10px">'
            f'<div style="flex:1;min-width:0">'
            f'<a href="{row["article_link"]}" target="_blank" style="font-size:13px;font-weight:600;'
            f'color:#111827;text-decoration:none;line-height:1.4;display:block">{row["article_title"]}</a>'
            f'<div style="margin-top:4px;display:flex;align-items:center;gap:6px;flex-wrap:wrap">'
            f'<span style="font-size:10px;color:#9ca3af">{label} · {pub}</span>'
            f'<span style="font-size:10px;color:white;background:{sp_c};padding:1px 6px;border-radius:3px">{sp or "—"}</span>'
            f'</div>'
            f'{reason_html}'
            f'{action_note}'
            f'</div>'
            f'<div style="text-align:center;flex-shrink:0;min-width:36px">'
            f'<div style="font-size:16px;font-weight:700;color:{s_col}">{score}</div>'
            f'</div></div>'
        )

    lone_html = ''.join(lone_cards) if lone_cards else (
        '<div style="padding:20px;text-align:center;font-size:12px;color:#9ca3af">暂无孤立高分信号</div>'
    )

    run_ts = f'上次分析 {last_run}' if last_run else '尚未运行 — 执行 python3 jd_intelligence_synthesis.py'

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>JD情报简报</title>
<style>
  * {{ box-sizing:border-box }}
  body {{ margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f3f4f6;color:#1a1a2e }}
  .header {{ background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);color:white;padding:20px 32px }}
  .header h1 {{ margin:0 0 4px;font-size:20px;font-weight:700 }}
  .meta {{ font-size:12px;opacity:.65 }}
  .nav {{ background:#16213e;padding:0 32px;display:flex;align-items:center;gap:4px }}
  .nav a {{ color:rgba(255,255,255,.55);text-decoration:none;padding:10px 14px;font-size:13px;border-bottom:2px solid transparent;display:inline-block }}
  .nav a:hover,.nav a.active {{ color:white;border-bottom-color:#e74c3c }}
  .outer {{ display:flex;gap:20px;max-width:1200px;margin:20px auto;padding:0 20px }}
  .feed {{ flex:1;min-width:0 }}
  .sidebar {{ width:200px;flex-shrink:0 }}
  .sidebar-card {{ background:white;border:1px solid #e5e7eb;border-radius:8px;padding:14px 16px;margin-bottom:12px }}
  .sidebar-title {{ font-size:11px;font-weight:700;color:#374151;margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px }}
  .section-title {{ font-size:12px;font-weight:700;color:#374151;text-transform:uppercase;letter-spacing:.5px;margin:20px 0 10px;display:flex;align-items:center;gap:8px }}
  @media(max-width:768px){{ .sidebar{{display:none}} .outer{{padding:0 12px}} }}
</style>
</head>
<body>
<div class="header">
  <h1>🏪 JD全球前沿情报系统</h1>
  <div class="meta">京东集团CTO部门 · 总裁简报原材料 · 收敛信号优先</div>
</div>
{_jd_nav("")}
<div class="outer">
  <div class="feed">
    <!-- Stats bar -->
    <div style="display:flex;gap:10px;margin-bottom:16px">
      <div style="background:white;border-radius:8px;padding:12px 16px;border:1px solid #e5e7eb;flex:1;text-align:center">
        <div style="font-size:22px;font-weight:700;color:#7c3aed">{len(clusters)}</div>
        <div style="font-size:10px;color:#9ca3af;margin-top:2px">收敛集群</div>
      </div>
      <div style="background:white;border-radius:8px;padding:12px 16px;border:1px solid #e5e7eb;flex:1;text-align:center">
        <div style="font-size:22px;font-weight:700;color:#e67e22">{len(lone_rows)}</div>
        <div style="font-size:10px;color:#9ca3af;margin-top:2px">孤立强信号</div>
      </div>
      <div style="background:white;border-radius:8px;padding:12px 16px;border:1px solid #e5e7eb;flex:2;display:flex;align-items:center">
        <div style="font-size:11px;color:#6b7280">{run_ts}</div>
      </div>
    </div>

    <!-- Clusters -->
    <div class="section-title">
      <span style="background:#7c3aed;color:white;padding:2px 8px;border-radius:4px">{len(clusters)}</span>
      收敛集群 — 多源独立验证的底层趋势
    </div>
    {''.join(cluster_cards_html)}
    {no_clusters_msg}

    <!-- Lone signals -->
    <div class="section-title" style="margin-top:24px">
      <span style="background:#e67e22;color:white;padding:2px 8px;border-radius:4px">{len(lone_rows)}</span>
      孤立高分信号 ≥70分 · 尚无独立对照信源
    </div>
    <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
      {lone_html}
    </div>
  </div>

  <div class="sidebar">
    <div class="sidebar-card">
      <div class="sidebar-title">📐 收敛分说明</div>
      <div style="font-size:11px;color:#6b7280;line-height:1.7">
        均分 × 立场多样性 × Tier1加成 × 时间集中度<br><br>
        <span style="color:#7c3aed;font-weight:600">紫色边框</span> = 收敛集群<br>
        <span style="color:#e67e22;font-weight:600">橙色数字</span> = 孤立高分
      </div>
    </div>
  </div>
</div>
</body>
</html>"""

@app.route('/jd/all')
def jd_all():
    from flask import request
    team = request.args.get('team', '').strip() or None
    rows = get_jd_articles_from_db(tier_filter=None, team_filter=team, limit=300)
    title = f"全部情报 · {team}" if team else "全部情报归档"
    return render_jd_browser(rows, title, None, active_team=team, page='all')

@app.route('/jd/tier1')
def jd_tier1():
    rows = get_jd_articles_from_db(tier_filter=1, limit=100)
    return render_jd_browser(rows, "JD情报 · Tier 1 风向标", "/jd/tier1/feed.xml")

@app.route('/jd/tier2')
def jd_tier2():
    rows = get_jd_articles_from_db(tier_filter=2, limit=100)
    return render_jd_browser(rows, "JD情报 · Tier 2 确认信号", "/jd/tier2/feed.xml")

@app.route('/jd/intelligence')
def jd_intelligence():
    """
    Intelligence convergence layer — clusters of articles where multiple
    independent standpoints point at the same underlying shift, plus
    lone strong signals that haven't clustered yet.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Ensure table exists (created by jd_intelligence_synthesis.py on first run,
    # but we create it here too so the page loads cleanly before any synthesis run)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS intelligence_clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme_label TEXT NOT NULL,
            article_ids TEXT NOT NULL,
            article_titles TEXT NOT NULL,
            article_feed_names TEXT NOT NULL,
            article_links TEXT NOT NULL,
            article_scores TEXT NOT NULL,
            domains TEXT,
            standpoints TEXT,
            source_count INTEGER DEFAULT 0,
            convergence_score INTEGER DEFAULT 0,
            why_convergent TEXT,
            synthesis_text TEXT,
            strategic_question TEXT,
            recommended_action TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()

    # ── Load clusters (most recent run, sorted by convergence score) ─────────
    clusters = conn.execute("""
        SELECT * FROM intelligence_clusters
        ORDER BY convergence_score DESC, created_at DESC
    """).fetchall()

    # ── Lone strong signals: scored ≥75 in last 14d, not in any cluster ──────
    if clusters:
        clustered_ids_raw = []
        for c in clusters:
            try:
                clustered_ids_raw.extend(json.loads(c['article_ids']))
            except Exception:
                pass
        if clustered_ids_raw:
            placeholders = ','.join('?' * len(clustered_ids_raw))
            lone_rows = conn.execute(f"""
                SELECT id, feed_name, article_title, article_link,
                       published_date, criteria_score, criteria_reason, criteria, signal_tier
                FROM articles
                WHERE feed_name LIKE 'jd-%'
                  AND criteria_score >= 75
                  AND published_date >= date('now', '-14 days')
                  AND id NOT IN ({placeholders})
                ORDER BY criteria_score DESC
                LIMIT 20
            """, clustered_ids_raw).fetchall()
        else:
            lone_rows = []
    else:
        lone_rows = conn.execute("""
            SELECT id, feed_name, article_title, article_link,
                   published_date, criteria_score, criteria_reason, criteria, signal_tier
            FROM articles
            WHERE feed_name LIKE 'jd-%'
              AND criteria_score >= 75
              AND published_date >= date('now', '-14 days')
            ORDER BY criteria_score DESC
            LIMIT 20
        """).fetchall()

    # Last run timestamp
    last_run_row = conn.execute(
        "SELECT created_at FROM intelligence_clusters ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    last_run = last_run_row['created_at'][:16].replace('T', ' ') + ' UTC' if last_run_row else None

    conn.close()

    # ── Standpoint pill colors ────────────────────────────────────────────────
    SP_COLORS = {
        '关键玩家':  '#7c3aed',
        '资本动向':  '#059669',
        '顶尖研究者':'#d97706',
        '技术社区':  '#6366f1',
        '科技媒体':  '#2563eb',
        '行业媒体':  '#0891b2',
        '政策与专利':'#dc2626',
        '内部情报':  '#be185d',
    }

    def _sp_pill(sp):
        c = SP_COLORS.get(sp, '#6b7280')
        return (f'<span style="font-size:10px;background:{c}18;color:{c};'
                f'border:1px solid {c}44;padding:2px 8px;border-radius:5px;'
                f'font-weight:600;white-space:nowrap;margin-right:4px">{sp}</span>')

    def _score_ring(score):
        if score is None:
            return '<div style="font-size:18px;font-weight:700;color:#d1d5db">—</div>'
        color = '#c0392b' if score >= 75 else ('#e67e22' if score >= 55 else '#27ae60')
        return (f'<div style="font-size:22px;font-weight:800;color:{color};'
                f'line-height:1">{score}</div>'
                f'<div style="font-size:9px;color:#9ca3af;margin-top:2px">收敛分</div>')

    # ── Render cluster cards ──────────────────────────────────────────────────
    cluster_cards = []
    for c in clusters:
        try:
            titles     = json.loads(c['article_titles'])
            links      = json.loads(c['article_links'])
            feed_names = json.loads(c['article_feed_names'])
            scores     = json.loads(c['article_scores'])
            standpoints= json.loads(c['standpoints'])
        except Exception:
            continue

        sp_pills = ''.join(_sp_pill(sp) for sp in standpoints)

        # Article mini-list inside the cluster card
        art_items = []
        for t, lnk, fn, sc in zip(titles, links, feed_names, scores):
            sp  = STANDPOINT_MAP.get(fn, '')
            sp_c = SP_COLORS.get(sp, '#9ca3af')
            src = JD_SOURCE_MAP.get(fn, {}).get('label', fn)
            art_items.append(
                f'<div style="padding:6px 0;border-top:1px solid #f3f4f6;display:flex;align-items:flex-start;gap:8px">'
                f'<span style="font-size:10px;color:white;background:{sp_c};'
                f'padding:1px 6px;border-radius:4px;white-space:nowrap;flex-shrink:0;margin-top:1px">{sp or "—"}</span>'
                f'<div style="flex:1;min-width:0">'
                f'<a href="{lnk}" target="_blank" style="font-size:12px;color:#111827;'
                f'text-decoration:none;line-height:1.4;display:block">{t}</a>'
                f'<span style="font-size:10px;color:#9ca3af">{src} · {sc}分</span>'
                f'</div></div>'
            )
        art_list = ''.join(art_items)

        action_html = ''
        if c['recommended_action']:
            action_html = (
                f'<div style="margin-top:12px;padding:9px 12px;'
                f'background:#fffbeb;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;'
                f'font-size:12px;color:#92400e;line-height:1.6">'
                f'<span style="font-weight:600;margin-right:4px">📋 建议行动</span>{c["recommended_action"]}</div>'
            )

        sq_badge = ''
        if c['strategic_question']:
            sq_badge = (
                f'<span style="font-size:11px;background:#eff6ff;color:#1d4ed8;'
                f'border:1px solid #bfdbfe;padding:2px 10px;border-radius:5px;'
                f'font-weight:600">{c["strategic_question"]}</span>'
            )

        cluster_cards.append(f"""
        <div style="border:1px solid #e5e7eb;border-left:4px solid #7c3aed;
                    border-radius:8px;background:white;margin-bottom:16px;
                    box-shadow:0 1px 4px rgba(0,0,0,.06);overflow:hidden">
          <!-- Header -->
          <div style="padding:16px 18px 12px;display:flex;align-items:flex-start;gap:12px">
            <div style="flex:1;min-width:0">
              <div style="font-size:16px;font-weight:700;color:#1a1a2e;margin-bottom:8px;line-height:1.4">
                🔗 {c['theme_label']}
              </div>
              <div style="display:flex;flex-wrap:wrap;gap:0;align-items:center;margin-bottom:8px">
                {sp_pills}
                {sq_badge}
              </div>
              {f'<div style="font-size:11px;color:#6b7280;font-style:italic;margin-bottom:8px">收敛依据：{c["why_convergent"]}</div>' if c['why_convergent'] else ''}
              {f'<div style="font-size:13px;color:#374151;line-height:1.7;margin-top:6px">{c["synthesis_text"]}</div>' if c['synthesis_text'] else ''}
              {action_html}
            </div>
            <div style="text-align:center;min-width:60px;flex-shrink:0">
              {_score_ring(c['convergence_score'])}
              <div style="font-size:9px;color:#9ca3af;margin-top:4px">{c['source_count']} 篇</div>
            </div>
          </div>
          <!-- Article list (collapsed look) -->
          <div style="border-top:1px solid #f3f4f6;padding:0 18px 12px;margin-top:4px">
            <div style="font-size:10px;font-weight:600;color:#9ca3af;text-transform:uppercase;
                        letter-spacing:.5px;padding:10px 0 4px">收敛信源</div>
            {art_list}
          </div>
        </div>""")

    clusters_html = ''.join(cluster_cards) if cluster_cards else (
        '<div style="padding:60px;text-align:center;color:#9ca3af;background:white;border-radius:8px;border:1px solid #e5e7eb">'
        '<div style="font-size:32px;margin-bottom:12px">🔍</div>'
        '<div style="font-size:14px;font-weight:600;margin-bottom:8px">暂无收敛集群</div>'
        '<div style="font-size:12px;line-height:1.8">运行 <code style="background:#f3f4f6;padding:2px 6px;border-radius:4px">'
        'python3 jd_intelligence_synthesis.py</code> 来生成收敛分析。<br>'
        '需要至少50篇已评分文章才能发现有效收敛。</div></div>'
    )

    # ── Lone strong signals ───────────────────────────────────────────────────
    lone_cards = []
    for row in lone_rows:
        src   = JD_SOURCE_MAP.get(row['feed_name'], {})
        label = src.get('label', row['feed_name'])
        sp    = STANDPOINT_MAP.get(row['feed_name'], '')
        sp_c  = SP_COLORS.get(sp, '#9ca3af')
        score = row['criteria_score']
        reason= row['criteria_reason'] or ''
        pub   = _parse_pub_date(row['published_date']).strftime('%m-%d %H:%M')
        s_col = '#c0392b' if (score or 0) >= 75 else '#e67e22'
        reason_html = f'<div style="margin-top:5px;font-size:11px;color:#6b7280;line-height:1.5">{reason[:160]}</div>' if reason else ''
        lone_cards.append(
            f'<div style="padding:12px 16px;border-bottom:1px solid #f3f4f6;display:flex;align-items:flex-start;gap:10px">'
            f'<div style="flex:1;min-width:0">'
            f'<a href="{row["article_link"]}" target="_blank" style="font-size:13px;font-weight:600;'
            f'color:#111827;text-decoration:none;line-height:1.4;display:block">{row["article_title"]}</a>'
            f'<div style="margin-top:4px;display:flex;align-items:center;gap:6px;flex-wrap:wrap">'
            f'<span style="font-size:10px;color:#9ca3af">{label} · {pub}</span>'
            f'<span style="font-size:10px;color:white;background:{sp_c};'
            f'padding:1px 6px;border-radius:4px">{sp or "—"}</span>'
            f'</div>'
            f'{reason_html}'
            f'</div>'
            f'<div style="text-align:center;flex-shrink:0;min-width:36px">'
            f'<div style="font-size:16px;font-weight:700;color:{s_col}">{score}</div>'
            f'</div></div>'
        )
    lone_html = ''.join(lone_cards) if lone_cards else (
        '<div style="padding:20px;text-align:center;font-size:12px;color:#9ca3af">暂无孤立强信号</div>'
    )

    run_info = (
        f'上次分析：{last_run} · '
        f'<code style="background:#f3f4f6;padding:1px 6px;border-radius:3px;font-size:11px">'
        f'python3 jd_intelligence_synthesis.py</code> 重新运行'
    ) if last_run else (
        '尚未运行分析 — 执行 '
        f'<code style="background:#f3f4f6;padding:1px 6px;border-radius:3px;font-size:11px">'
        f'python3 jd_intelligence_synthesis.py</code> 开始'
    )

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>收敛情报分析 · JD</title>
<style>
  * {{ box-sizing:border-box }}
  body {{ margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
         background:#f3f4f6;color:#1a1a2e }}
  .header {{ background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
             color:white;padding:20px 32px }}
  .header h1 {{ margin:0 0 4px;font-size:20px;font-weight:700 }}
  .meta {{ font-size:12px;opacity:.65 }}
  .nav {{ background:#16213e;padding:0 32px;display:flex;align-items:center;gap:4px }}
  .nav a {{ color:rgba(255,255,255,.55);text-decoration:none;padding:10px 14px;
            font-size:13px;border-bottom:2px solid transparent;display:inline-block }}
  .nav a:hover {{ color:white;border-bottom-color:#e74c3c }}
  .nav a.active {{ color:white;border-bottom-color:#e74c3c }}
  .wrap {{ max-width:900px;margin:24px auto;padding:0 20px }}
  .section-title {{ font-size:13px;font-weight:700;color:#374151;
                    text-transform:uppercase;letter-spacing:.5px;
                    margin:24px 0 12px;display:flex;align-items:center;gap:8px }}
  code {{ font-family:monospace }}
  @media(max-width:768px) {{ .wrap {{ padding:0 12px }} }}
</style>
</head>
<body>
<div class="header">
  <h1>🔗 收敛情报分析</h1>
  <div class="meta">多源独立验证 · 底层趋势识别 · CTO战略合成</div>
</div>
{_jd_nav("")}
<div class="wrap">

  <!-- Explainer banner -->
  <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;
              padding:14px 18px;margin-bottom:4px;font-size:12px;color:#374151;line-height:1.8">
    <strong>收敛分析逻辑：</strong>
    单篇高分文章是弱信号。当
    <span style="color:#7c3aed;font-weight:600">关键玩家</span> ·
    <span style="color:#059669;font-weight:600">资本动向</span> ·
    <span style="color:#d97706;font-weight:600">顶尖研究者</span>
    等不同立场的独立信源同期指向同一底层变化时，信号强度非线性放大。
    收敛分 = 单篇均分 × 立场多样性系数 × Tier1加成 × 时间集中系数。
  </div>
  <div style="font-size:11px;color:#9ca3af;margin-bottom:20px;padding:0 2px">{run_info}</div>

  <!-- Clusters -->
  <div class="section-title">
    <span style="background:#7c3aed;color:white;padding:2px 8px;border-radius:4px;font-size:11px">{len(clusters)}</span>
    收敛集群 — 多源独立验证的底层趋势
  </div>
  {clusters_html}

  <!-- Lone strong signals -->
  <div class="section-title" style="margin-top:32px">
    <span style="background:#e67e22;color:white;padding:2px 8px;border-radius:4px;font-size:11px">{len(lone_rows)}</span>
    孤立强信号 — 评分≥75 · 尚无独立对照信源 · 值得持续关注
  </div>
  <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
    {lone_html}
  </div>

</div>
</body>
</html>"""


@app.route('/jd/paste', methods=['GET', 'POST'])
def jd_paste():
    """Manual intelligence submission form.
    Supports three signal types with distinct scoring treatment:
      - jd-manual-wechat    : 文章/公众号  (published article, normal scoring)
      - jd-manual-community : 社区信号     (Discord/Reddit/HN, novelty capped)
      - jd-manual-report    : 内部报告     (internal doc/meeting note, max relevance)
    """
    from datetime import datetime, timezone

    # signal_type → (feed_name, standpoint colour, display label, scoring hint)
    SIGNAL_TYPES = {
        'article':   ('jd-manual-wechat',    '#2563eb', '📰 文章/公众号'),
        'community': ('jd-manual-community', '#6366f1', '💬 社区信号'),
        'report':    ('jd-manual-report',    '#be185d', '📋 内部报告'),
    }

    msg      = ''
    msg_type = ''

    if request.method == 'POST':
        title       = (request.form.get('title',       '') or '').strip()
        url         = (request.form.get('url',         '') or '').strip()
        source      = (request.form.get('source',      '') or '').strip() or '未知来源'
        content     = (request.form.get('content',     '') or '').strip()
        signal_type = (request.form.get('signal_type', 'article')).strip()
        tier_raw    = request.form.get('tier', '1')
        try:
            tier = int(tier_raw)
        except Exception:
            tier = 1

        if not title or not url:
            msg, msg_type = '❌ 标题和链接为必填项', 'err'
        else:
            if not url.startswith('http'):
                url = 'https://' + url
            feed_name = SIGNAL_TYPES.get(signal_type, SIGNAL_TYPES['article'])[0]
            pub_date  = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            try:
                conn = sqlite3.connect(DB_PATH)
                c    = conn.cursor()
                c.execute("""
                    INSERT OR IGNORE INTO articles
                      (feed_name, feed_url, article_title, article_link,
                       published_date, raw_content, signal_tier)
                    VALUES (?,?,?,?,?,?,?)
                """, (feed_name, f'manual://{source}',
                      title, url, pub_date, content, tier))
                ok = c.rowcount > 0
                conn.commit()
                conn.close()
                if ok:
                    type_label = SIGNAL_TYPES.get(signal_type, SIGNAL_TYPES['article'])[2]
                    msg = f'✅ [{type_label}] 已收录「{title[:40]}{"…" if len(title)>40 else ""}」— 下次运行 jd_scorer.py 后即可见评分'
                    msg_type = 'ok'
                else:
                    msg = '⚠️ 该链接已存在，跳过重复插入'
                    msg_type = 'err'
            except Exception as e:
                msg = f'❌ 数据库错误: {e}'
                msg_type = 'err'

    msg_html = ''
    if msg:
        bg  = '#f0fdf4' if msg_type == 'ok' else '#fef2f2'
        bdr = '#bbf7d0' if msg_type == 'ok' else '#fecaca'
        clr = '#166534' if msg_type == 'ok' else '#991b1b'
        msg_html = (f'<div style="margin-bottom:20px;padding:12px 16px;background:{bg};'
                    f'border:1px solid {bdr};border-radius:8px;font-size:13px;color:{clr}">'
                    f'{msg}</div>')

    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>人工投稿 · JD情报</title>
<style>
  * {{ box-sizing:border-box }}
  body {{ margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
          background:#f8f9fa;color:#1f2937 }}
  .header {{ background:#16213e;padding:16px 32px }}
  .header h1 {{ color:white;font-size:16px;margin:0;font-weight:700 }}
  .header .sub {{ color:rgba(255,255,255,.5);font-size:12px;margin-top:2px }}
  .nav {{ background:#16213e;padding:0 32px;display:flex;align-items:center;gap:4px;
          border-top:1px solid rgba(255,255,255,.1) }}
  .nav a {{ color:rgba(255,255,255,.55);text-decoration:none;padding:10px 14px;font-size:13px;
             border-bottom:2px solid transparent;display:inline-block }}
  .nav a:hover,.nav a.active {{ color:white;border-bottom-color:#e74c3c }}
  .wrap {{ max-width:760px;margin:32px auto;padding:0 16px }}
  .card {{ background:white;border:1px solid #e5e7eb;border-radius:10px;padding:28px 32px;
           margin-bottom:20px }}
  h2 {{ font-size:18px;margin:0 0 4px;font-weight:700 }}
  .sub {{ font-size:13px;color:#6b7280;margin-bottom:24px }}
  label {{ display:block;font-size:13px;font-weight:600;color:#374151;margin-bottom:6px }}
  input,textarea,select {{ width:100%;padding:10px 12px;border:1px solid #d1d5db;border-radius:6px;
                            font-size:13px;font-family:inherit;outline:none;transition:border .15s }}
  input:focus,textarea:focus,select:focus {{ border-color:#7c3aed;box-shadow:0 0 0 3px rgba(124,58,237,.1) }}
  textarea {{ resize:vertical;min-height:130px }}
  .field {{ margin-bottom:20px }}
  .hint {{ font-size:11px;color:#9ca3af;margin-top:4px;line-height:1.5 }}
  .row {{ display:flex;gap:16px }}
  .row .field {{ flex:1 }}
  .btn {{ background:#7c3aed;color:white;border:none;padding:11px 28px;border-radius:6px;
           font-size:14px;font-weight:600;cursor:pointer;transition:background .15s }}
  .btn:hover {{ background:#6d28d9 }}
  .divider {{ border:none;border-top:1px solid #e5e7eb;margin:24px 0 }}
  .tip-box {{ background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 16px;
              font-size:12px;color:#1e40af;line-height:1.7 }}
  /* Signal type selector */
  .sig-tabs {{ display:flex;gap:8px;margin-bottom:20px }}
  .sig-tab {{ flex:1;padding:10px 8px;border:2px solid #e5e7eb;border-radius:8px;cursor:pointer;
               text-align:center;font-size:12px;font-weight:600;color:#6b7280;
               transition:all .15s;background:white }}
  .sig-tab:hover {{ border-color:#7c3aed;color:#7c3aed }}
  .sig-tab.active-article {{ border-color:#2563eb;background:#eff6ff;color:#2563eb }}
  .sig-tab.active-community {{ border-color:#6366f1;background:#eef2ff;color:#6366f1 }}
  .sig-tab.active-report {{ border-color:#be185d;background:#fdf2f8;color:#be185d }}
  .sig-hint {{ display:none;padding:10px 14px;border-radius:6px;font-size:12px;
               line-height:1.6;margin-bottom:16px }}
  .sig-hint.show {{ display:block }}
  .hint-article {{ background:#eff6ff;color:#1e40af;border:1px solid #bfdbfe }}
  .hint-community {{ background:#eef2ff;color:#3730a3;border:1px solid #c7d2fe }}
  .hint-report {{ background:#fdf2f8;color:#9d174d;border:1px solid #fbcfe8 }}
</style>
</head>
<body>
<div class="header">
  <h1>✍️ 人工投稿</h1>
  <div class="sub">微信公众号 · 社区信号 · 内部报告 · 会议纪要</div>
</div>
{_jd_nav("")}

<div class="wrap">
  {msg_html}
  <div class="card">
    <h2>新增情报条目</h2>
    <p class="sub">将无法自动抓取的内容手工录入情报库，选择信号类型后AI会用对应评分规则处理。</p>
    <form method="POST" action="/jd/paste" id="pasteForm">
      <input type="hidden" name="signal_type" id="signal_type" value="article">

      <!-- Signal type selector -->
      <div class="field">
        <label>📂 信号类型</label>
        <div class="sig-tabs">
          <div class="sig-tab active-article" onclick="setType('article')" id="tab-article">
            📰<br>文章/公众号
          </div>
          <div class="sig-tab" onclick="setType('community')" id="tab-community">
            💬<br>社区信号
          </div>
          <div class="sig-tab" onclick="setType('report')" id="tab-report">
            📋<br>内部报告
          </div>
        </div>
        <div class="sig-hint hint-article show" id="hint-article">
          <strong>文章/公众号：</strong>微信公众号、虎嗅、36氪等已发布文章。
          按正常四维模型评分（来源层级 · 新鲜度 · 相关性 · 收敛性）。
        </div>
        <div class="sig-hint hint-community" id="hint-community">
          <strong>💬 社区信号：</strong>Discord / Reddit / HN / 微信群 的帖子或讨论摘要。
          <em>新鲜度上限15分</em>（非结构化内容本身无原创分析），
          但「我测试了…」「刚拿到内测…」等第一手实测描述可获满分相关性。
          <br>建议：将整个讨论线程归纳成1-2段再提交，而非粘贴原始消息。
        </div>
        <div class="sig-hint hint-report" id="hint-report">
          <strong>📋 内部报告：</strong>会议纪要、竞品调研、内部数据报告、战略备忘录。
          相关性权重×1.3（一手内部信息溢价），不对外公开的内容得分上限不受来源层级限制。
          <br>链接字段可填内网地址或文件标识符（如 confluence://page/12345）。
        </div>
      </div>

      <div class="field">
        <label>📌 标题 <span style="color:#ef4444">*</span></label>
        <input type="text" name="title" id="title_input"
               placeholder="粘贴文章标题或简短描述" required maxlength="300">
      </div>
      <div class="field">
        <label>🔗 链接 <span style="color:#ef4444">*</span></label>
        <input type="text" name="url" id="url_input"
               placeholder="https://mp.weixin.qq.com/s/..." required>
        <div class="hint" id="url_hint">
          微信文章：右上角「···」→「复制链接」。无公开链接时填写标识符，如
          <code>wechat://公众号名/日期</code>
        </div>
      </div>
      <div class="row">
        <div class="field">
          <label>📡 来源名称</label>
          <input type="text" name="source" id="source_input"
                 placeholder="例：虎嗅 · Latent Space Discord · 战略规划部">
        </div>
        <div class="field">
          <label>⭐ 优先级</label>
          <select name="tier">
            <option value="1" selected>Tier 1 · 风向标（高优）</option>
            <option value="2">Tier 2 · 确认信号（中优）</option>
          </select>
        </div>
      </div>
      <div class="field">
        <label>📝 内容摘要</label>
        <textarea name="content" id="content_input"
                  placeholder="粘贴文章摘要、关键段落，或社区讨论的核心结论"></textarea>
        <div class="hint" id="content_hint">
          建议300字以上，覆盖核心论点——AI评分质量直接取决于此。
        </div>
      </div>
      <button type="submit" class="btn">📥 提交入库</button>
    </form>

    <hr class="divider">
    <div class="tip-box">
      <strong>⚡ 快速上手：</strong><br>
      1. 选择信号类型 → 填写标题 + 链接 + 摘要 → 提交<br>
      2. 文章进入待评分队列，下次 <code>jd_scorer.py</code> 运行时（每天8点）自动评分<br>
      3. 评分≥55分自动出现在今日简报；社区信号会带 <strong style="color:#6366f1">💬 社区信号</strong> 标识，内部报告带 <strong style="color:#be185d">📋 内部情报</strong> 标识
    </div>
  </div>

  {_paste_recent_html()}
</div>

<script>
function setType(type) {{
  document.getElementById('signal_type').value = type;
  // Tabs
  ['article','community','report'].forEach(t => {{
    const tab = document.getElementById('tab-'+t);
    tab.className = 'sig-tab' + (t === type ? ' active-'+t : '');
  }});
  // Hints
  ['article','community','report'].forEach(t => {{
    const h = document.getElementById('hint-'+t);
    h.className = 'sig-hint hint-'+t + (t === type ? ' show' : '');
  }});
  // Update placeholder text
  const placeholders = {{
    article:   ['粘贴文章标题', 'https://mp.weixin.qq.com/s/...', '微信文章：右上角「···」→「复制链接」。', '建议粘贴核心论点或前三段，300字以上效果更好'],
    community: ['讨论主题摘要（如：LangChain Discord - Agent记忆管理最佳实践讨论）', 'https://discord.com/channels/... 或 community://Discord/频道名/日期', '社区链接，无固定链接可填 community://平台名/频道/日期', '建议将讨论线程归纳成1-2段结论再粘贴，而非原始消息流'],
    report:    ['报告标题（如：2025Q1竞品AI功能深度调研）', 'confluence://page/12345 或内网URL', '内网文件标识符或Confluence/Notion链接', '粘贴核心结论、数据摘要或执行摘要（Executive Summary）'],
  }};
  const p = placeholders[type];
  document.getElementById('title_input').placeholder   = p[0];
  document.getElementById('url_input').placeholder     = p[1];
  document.getElementById('url_hint').textContent      = p[2];
  document.getElementById('content_input').placeholder = p[3];
}}
</script>
</body>
</html>'''


def _paste_recent_html() -> str:
    """Show the last 15 manually submitted items across all signal types."""
    _FEED_BADGE = {
        'jd-manual-wechat':    ('📰', '#2563eb', '文章'),
        'jd-manual-community': ('💬', '#6366f1', '社区'),
        'jd-manual-report':    ('📋', '#be185d', '内部'),
    }
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT article_title, article_link, published_date,
                   COALESCE(criteria_score, 0) as score,
                   feed_url, feed_name
            FROM articles
            WHERE feed_name IN ('jd-manual-wechat','jd-manual-community','jd-manual-report')
            ORDER BY created_at DESC
            LIMIT 15
        """).fetchall()
        conn.close()
    except Exception:
        return ''
    if not rows:
        return ''
    items = ''
    for r in rows:
        score_col = ('#166534' if r['score'] >= 70 else
                     '#92400e' if r['score'] >= 55 else '#6b7280')
        score_str = f'{int(r["score"])}分' if r['score'] else '待评分'
        source    = (r['feed_url'] or '').replace('manual://', '') or '—'
        icon, col, label = _FEED_BADGE.get(r['feed_name'], ('✍️','#6b7280','手工'))
        badge = (f'<span style="font-size:10px;font-weight:700;color:{col};'
                 f'background:{col}15;border:1px solid {col}40;'
                 f'padding:1px 6px;border-radius:4px;white-space:nowrap">'
                 f'{icon} {label}</span>')
        items += (
            f'<div style="padding:10px 16px;border-bottom:1px solid #f3f4f6;'
            f'display:flex;align-items:center;gap:12px">'
            f'<span style="font-size:12px;font-weight:700;color:{score_col};'
            f'min-width:44px;text-align:right">{score_str}</span>'
            f'<div style="flex:1;min-width:0">'
            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">'
            f'{badge}'
            f'<span style="font-size:11px;color:#9ca3af">{source} · {r["published_date"][:10]}</span>'
            f'</div>'
            f'<a href="{r["article_link"]}" target="_blank" style="font-size:13px;'
            f'color:#1f2937;text-decoration:none;font-weight:500;display:block;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
            f'{r["article_title"]}</a>'
            f'</div></div>'
        )
    return (
        '<div class="card">'
        '<h2 style="font-size:16px;margin:0 0 16px">🕐 近期人工投稿</h2>'
        f'<div style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">{items}</div>'
        '</div>'
    )


@app.route('/jd/feed.xml')
@app.route('/jd/feed')
def jd_feed_all():
    return Response(
        _get_jd_rss(None, jd_cache, "https://rss.borntofly.ai/jd/feed.xml", "JD零售AI情报"),
        mimetype='application/rss+xml')

@app.route('/jd/tier1/feed.xml')
def jd_feed_tier1():
    return Response(
        _get_jd_rss(1, jd_t1_cache, "https://rss.borntofly.ai/jd/tier1/feed.xml", "JD情报·Tier1风向标"),
        mimetype='application/rss+xml')

@app.route('/jd/tier2/feed.xml')
def jd_feed_tier2():
    return Response(
        _get_jd_rss(2, jd_t2_cache, "https://rss.borntofly.ai/jd/tier2/feed.xml", "JD情报·Tier2确认信号"),
        mimetype='application/rss+xml')


@app.route('/jd/rss')
def jd_rss_page():
    feeds = [
        {
            "title": "JD零售AI情报 · 全部",
            "url": "https://rss.borntofly.ai/jd/feed.xml",
            "desc": "所有情报源，按情报分排序。推荐订阅此源。",
            "tier_color": "#1a1a2e",
            "icon": "🏪",
        },
        {
            "title": "Tier 1 · 风向标",
            "url": "https://rss.borntofly.ai/jd/tier1/feed.xml",
            "desc": "Smart Money、Best Minds、顶级研究员 — 最高权重信号源",
            "tier_color": "#7c3aed",
            "icon": "🌪",
        },
        {
            "title": "Tier 2 · 确认信号",
            "url": "https://rss.borntofly.ai/jd/tier2/feed.xml",
            "desc": "深度调查媒体、全球零售、中国电商 — 二级确认信号",
            "tier_color": "#2563eb",
            "icon": "📡",
        },
    ]

    cards = []
    for f in feeds:
        cards.append(f'''
        <div style="background:white;border:1px solid #e5e7eb;border-left:5px solid {f["tier_color"]};
                    border-radius:8px;padding:20px 24px;margin-bottom:16px;
                    box-shadow:0 1px 3px rgba(0,0,0,.05)">
          <div style="font-size:18px;margin-bottom:6px">{f["icon"]}
            <strong style="font-size:15px;color:#111827;margin-left:6px">{f["title"]}</strong>
          </div>
          <div style="font-size:13px;color:#6b7280;margin-bottom:14px">{f["desc"]}</div>
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <code id="url-{f["icon"]}" style="background:#f3f4f6;padding:8px 14px;border-radius:6px;
                  font-size:13px;color:#374151;flex:1;min-width:0;word-break:break-all">
              {f["url"]}
            </code>
            <button onclick="copyUrl('{f["url"]}', this)"
                    style="background:{f["tier_color"]};color:white;border:none;padding:8px 16px;
                           border-radius:6px;font-size:13px;cursor:pointer;white-space:nowrap;
                           font-family:inherit">
              复制链接
            </button>
            <a href="{f["url"]}" target="_blank"
               style="background:#f3f4f6;color:#374151;padding:8px 14px;border-radius:6px;
                      font-size:13px;text-decoration:none;white-space:nowrap">
              预览 ↗
            </a>
          </div>
        </div>''')

    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JD情报 · RSS订阅</title>
<style>
  * {{ box-sizing:border-box }}
  body {{ margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
          background:#f3f4f6;color:#1a1a2e }}
  .header {{ background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);color:white;padding:20px 32px }}
  .header h1 {{ margin:0 0 4px;font-size:20px;font-weight:700 }}
  .header .meta {{ font-size:12px;opacity:.65 }}
  .nav {{ background:#16213e;padding:0 32px;display:flex;align-items:center }}
  .nav a {{ color:rgba(255,255,255,.65);text-decoration:none;padding:10px 14px;
            font-size:13px;border-bottom:2px solid transparent;display:inline-block }}
  .nav a:hover,.nav a.active {{ color:white;border-bottom-color:#e74c3c }}
  .container {{ max-width:700px;margin:32px auto;padding:0 24px }}
  .hint {{ background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;
           padding:14px 18px;margin-bottom:24px;font-size:13px;color:#1e40af;line-height:1.6 }}
</style>
<script>
function copyUrl(url, btn) {{
  navigator.clipboard.writeText(url).then(() => {{
    const orig = btn.textContent;
    btn.textContent = '已复制 ✓';
    btn.style.background = '#16a34a';
    setTimeout(() => {{ btn.textContent = orig; btn.style.background = btn.dataset.color; }}, 2000);
  }});
  btn.dataset.color = btn.style.background;
}}
</script>
</head>
<body>
<div class="header">
  <h1>🏪 JD全球前沿情报系统</h1>
  <div class="meta">京东集团CTO部门 · 总裁简报原材料</div>
</div>
{_jd_nav("")}
<div class="container">
  <div class="hint">
    <strong>如何添加到 Reeder：</strong><br>
    复制下方任意链接 → 打开 Reeder → 点击 <strong>+</strong> → 粘贴链接 → 订阅。
    建议订阅「全部」源，文章已按情报分排序，高分内容优先展示。
  </div>
  {''.join(cards)}
</div>
</body>
</html>'''


# ── Intelligence Matrix ───────────────────────────────────────────────────────

MATRIX_COLS = [
    ('增长与流量',    '搜索 · 推荐 · 内容分发 · 流量获取'),
    ('应用设计',      '产品架构 · 业务系统 · 交易履约 · 数据产品'),
    ('交互设计',      'UX · 多模态交互 · 用户研究 · 转化设计'),
    ('基础效能',      '数据基础设施 · MLOps · SRE · 安全 · 中间件'),
    ('AI技术',        'AI/ML · LLM · 算法引擎 · 模型训练与推理'),
]

MATRIX_ROWS = [
    ('搜索与内容社区',   '搜索推荐 · 内容发现 · 个性化 · UX设计 · 技术社区'),
    ('广告营销',         '程序化广告 · 内容营销 · 用户获取 · CRM · 创意生成'),
    ('智能零售',         '电商平台 · 动态定价 · 购物车转化 · 竞品动态 · 跨境'),
    ('金融与支付',       '支付通道 · 先买后付 · 消费信贷 · 风控 · 数字钱包'),
    ('物流与供应链',     '仓储自动化 · 最后一公里 · 即时配送 · 路由优化 · 跨境物流'),
    ('具身智能与机器人', '仿人机器人 · 工业自动化 · 感知规划 · 具身AI · 操控系统'),
    ('智能硬件',         '芯片 · 消费电子 · 智能设备 · IoT · 新能源 · 通信模组'),
    ('AI基础设施',       '大模型 · 推理优化 · 训练平台 · AI Agent · 开发工具链'),
]

# [row][col] = (teams, sources)
MATRIX_CELLS = [
  [ # 搜索与内容社区
    ([], ['arXiv cs.IR', 'Eugene Yan', 'Amazon Science', 'Walmart Global Tech', 'Instacart Tech', 'Hacker News']),
    ([], ['Shopify Blog', 'Shopee Blog', 'Grab Engineering', 'Digital Commerce 360']),
    ([], ['Nielsen Norman Group', 'UX Collective', '人人都是产品经理']),
    ([], ['Instacart Tech']),
    ([], ['arXiv cs.IR', 'Eugene Yan', 'arXiv cs.LG']),
  ],
  [ # 广告营销
    ([], ['AdExchanger', 'Digiday', '36氪AI专题', '36氪融资快讯']),
    ([], ['AdExchanger', 'Digiday']),
    ([], ['Nielsen Norman Group', 'UX Collective', 'Digiday']),
    ([], []),
    ([], ['TechCrunch AI', 'VentureBeat AI', '36氪AI专题']),
  ],
  [ # 智能零售
    ([], ['Modern Retail', 'Retail Dive', 'Digital Commerce 360', '亿邦动力', '36氪', 'Alizila']),
    ([], ['Amazon Science', 'Walmart Global Tech', 'arXiv cs.IR', 'Eugene Yan']),
    ([], ['Shopify Blog', 'Practical Ecommerce', 'Nielsen Norman Group']),
    ([], []),
    ([], ['Meituan Tech Blog', '36氪AI专题', '虎嗅']),
  ],
  [ # 金融与支付
    ([], ['PYMNTS', 'Finextra', 'Payments Dive', 'Digital Transactions']),
    ([], ['Stripe Blog', 'Atlantic Council CBDC', 'Coin Center']),
    ([], ['PYMNTS', 'Nielsen Norman Group']),
    ([], ['Sift Blog', 'Finextra']),
    ([], ['Stripe Blog', 'Sift Blog', 'Atlantic Council CBDC']),
  ],
  [ # 物流与供应链
    ([], ['Supply Chain Dive', 'DC Velocity', 'FreightWaves', 'The Loadstar', 'SupplyChainBrain']),
    ([], ['Supply Chain Dive', 'Logistics Viewpoints', 'DC Velocity']),
    ([], []),
    ([], ['SupplyChainBrain', 'DC Velocity']),
    ([], ['Logistics Viewpoints', 'IEEE Spectrum Robotics', 'The Robot Report']),
  ],
  [ # 具身智能与机器人
    ([], ['The Robot Report', 'IEEE Spectrum Robotics']),
    ([], ['The Robot Report', 'MIT Tech Review']),
    ([], []),
    ([], []),
    ([], ['IEEE Spectrum Robotics', 'Import AI', 'Bloomberg Technology', 'MIT Tech Review']),
  ],
  [ # 智能硬件
    ([], ['Electrek', 'Electrive', 'Fierce Electronics']),
    ([], ['Fierce Electronics']),
    ([], []),
    ([], ['Canary Media', 'CleanTechnica']),
    ([], ['IEEE Spectrum Robotics', 'RCR Wireless']),
  ],
  [ # AI基础设施
    ([], ['a16z', 'TechCrunch AI', 'VentureBeat AI', '36氪AI专题', '雷锋网', 'Axios AI']),
    ([], ['Latent Space', 'LangChain Blog', 'Simon Willison']),
    ([], []),
    ([], ['Chip Huyen', 'Nathan Lambert (Interconnects)', 'fast.ai']),
    ([], ['arXiv cs.LG', 'Andrej Karpathy', "Lil'Log", 'The Gradient', 'Import AI', 'QbitAI']),
  ],
]


# ── Maps primary_team name → MATRIX_COLS column label ─────────────────────
TEAM_TO_COL = {
    # 增长与流量 — search / rec / traffic acquisition
    '搜推技术':            '增长与流量',
    '搜推业务':            '增长与流量',
    '流量策略':            '增长与流量',
    # 应用设计 — product / business systems / transaction
    '交易产研':            '应用设计',
    '财经':                '应用设计',
    '商品':                '应用设计',
    '安全风控':            '应用设计',
    '数据资产':            '应用设计',
    '营销&用户系统':       '应用设计',
    '国内业务':            '应用设计',
    '本地生活':            '应用设计',
    '国际业务':            '应用设计',
    # 交互设计 — UX / design / content product
    '设计用研':            '交互设计',
    '营销产品':            '交互设计',
    '生态产品':            '交互设计',
    '内容':                '交互设计',
    # 基础效能 — infra / data / platform engineering
    '技术保障':            '基础效能',
    '效能与中间件':        '基础效能',
    '数据库与存储':        '基础效能',
    '数据计算':            '基础效能',
    '商业智能':            '基础效能',
    '产品架构/技术架构':   '基础效能',
    # AI技术 — AI/ML / algorithms / model
    '智能零售':            'AI技术',
    'AI Infra':            'AI技术',
    '智能客服':            'AI技术',
}

# ── Fallback: primary_team → MATRIX_ROWS domain label ─────────────────────
# Used when FEED_DOMAIN_MAP doesn't cover the feed
TEAM_TO_DOMAIN = {
    '搜推技术':            '搜索与内容社区',
    '搜推业务':            '搜索与内容社区',
    '设计用研':            '搜索与内容社区',
    '营销&用户系统':       '广告营销',
    '营销产品':            '广告营销',
    '流量策略':            '广告营销',
    '智能零售':            '智能零售',
    '交易产研':            '智能零售',
    '商品':                '智能零售',
    '本地生活':            '智能零售',
    '国内业务':            '智能零售',
    '国际业务':            '智能零售',
    '财经':                '金融与支付',
    '安全风控':            '金融与支付',
    '物流与供应链':        '物流与供应链',
    '智能客服':            'AI基础设施',
    'AI Infra':            'AI基础设施',
    '内容':                '搜索与内容社区',
}


def _render_matrix_table(cells_data):
    """Return just the <table>…</table> HTML for embedding in other pages."""
    col_labels = [label for label, _ in MATRIX_COLS]
    col_bg  = ['#f5f3ff', '#eff6ff', '#f0fdf4', '#fff7ed', '#fdf4e7']
    col_hdr = ['#7c3aed', '#2563eb', '#059669', '#d97706', '#b45309']
    row_labels = [label for label, _ in MATRIX_ROWS]

    def _sc(s):
        if s is None: return '#9ca3af'
        return '#dc2626' if s >= 75 else '#d97706' if s >= 55 else '#6b7280'

    def _card(row):
        score = row['criteria_score'] or 0
        title = (row['article_title'] or '')[:50]
        if len(row['article_title'] or '') > 50: title += '…'
        src = JD_SOURCE_MAP.get(row['feed_name'], {}).get('label', row['feed_name'])
        pub = _parse_pub_date(row['published_date']).strftime('%-m/%-d')
        return (f'<a href="{row["article_link"]}" target="_blank" style="display:block;'
                f'text-decoration:none;padding:4px 6px;border-radius:4px;margin-bottom:3px;'
                f'background:#fff;border:1px solid #e5e7eb">'
                f'<div style="font-size:10px;font-weight:600;color:#111827;line-height:1.3;margin-bottom:2px">{title}</div>'
                f'<div style="display:flex;justify-content:space-between">'
                f'<span style="font-size:9px;color:#9ca3af">{src} · {pub}</span>'
                f'<span style="font-size:9px;font-weight:700;color:{_sc(score)}">{int(score)}</span>'
                f'</div></a>')

    col_hdrs = '<th style="width:80px;border:none;background:transparent"></th>'
    for i, (label, sub) in enumerate(MATRIX_COLS):
        total_in_col = sum(len(cells_data.get((d, label), [])) for d in row_labels)
        col_hdrs += (f'<th style="background:{col_hdr[i]};color:white;padding:8px 6px;'
                     f'text-align:center;font-size:10px;border-radius:5px 5px 0 0;'
                     f'min-width:160px;border:none">'
                     f'<div style="font-size:12px;font-weight:700">{label}</div>'
                     f'<div style="font-size:8px;opacity:.75;margin-top:1px">{sub}</div>'
                     f'<div style="font-size:8px;opacity:.6">{total_in_col}篇</div></th>')

    rows_html = ''
    for ri, (row_label, row_sub) in enumerate(MATRIX_ROWS):
        row_bg = '#fafafa' if ri % 2 == 0 else '#ffffff'
        cells_html = ''
        row_total = sum(len(cells_data.get((row_label, cl), [])) for cl in col_labels)
        for ci, col_label in enumerate(col_labels):
            arts = cells_data.get((row_label, col_label), [])
            bg = col_bg[ci] if arts else '#f9fafb'
            border = f'2px solid {col_hdr[ci]}22' if arts else '1px solid #f0f0f0'
            content = (''.join(_card(a) for a in arts[:2])
                       + (f'<div style="font-size:9px;color:#9ca3af;text-align:center;padding:2px">'
                          f'+{len(arts)-2}篇</div>' if len(arts) > 2 else '')) if arts else (
                '<span style="color:#d1d5db;font-size:10px">—</span>')
            cells_html += (f'<td style="background:{bg};border:{border};padding:6px;'
                           f'vertical-align:top">{content}</td>')
        rows_html += (f'<tr><td style="background:{row_bg};padding:8px 6px;vertical-align:middle;'
                      f'border-right:3px solid #e5e7eb;border-top:1px solid #f3f4f6;min-width:80px">'
                      f'<div style="font-size:10px;font-weight:700;color:#1a1a2e">{row_label}</div>'
                      f'<div style="font-size:8px;color:#9ca3af;margin-top:1px;line-height:1.2">{row_sub}</div>'
                      f'<div style="font-size:8px;color:#d1d5db;margin-top:2px">{row_total}篇</div>'
                      f'</td>{cells_html}</tr>')

    return (f'<table style="border-collapse:separate;border-spacing:3px;width:100%;'
            f'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif">'
            f'<thead><tr>{col_hdrs}</tr></thead>'
            f'<tbody>{rows_html}</tbody></table>')


def render_jd_matrix(cells_data, total_articles):
    # ── Column config (from MATRIX_COLS) ──────────────────────────────────
    col_labels = [label for label, _ in MATRIX_COLS]
    col_subs   = [sub   for _, sub   in MATRIX_COLS]
    col_bg  = ['#f5f3ff', '#eff6ff', '#f0fdf4', '#fff7ed', '#fdf4e7']
    col_hdr = ['#7c3aed', '#2563eb', '#059669', '#d97706', '#b45309']

    # ── Row config (from MATRIX_ROWS) ─────────────────────────────────────
    row_labels = [label for label, _ in MATRIX_ROWS]
    row_subs   = [sub   for _, sub   in MATRIX_ROWS]

    def score_color(s):
        if s is None: return '#9ca3af'
        if s >= 75: return '#dc2626'
        if s >= 55: return '#d97706'
        return '#6b7280'

    def article_card(row):
        score = row['criteria_score'] or 0
        title = row['article_title'] or ''
        title_short = title[:50] + '…' if len(title) > 50 else title
        src = JD_SOURCE_MAP.get(row['feed_name'], {}).get('label', row['feed_name'])
        pub = _parse_pub_date(row['published_date']).strftime('%-m/%-d')
        return (
            f'<a href="{row["article_link"]}" target="_blank" style="display:block;'
            f'text-decoration:none;padding:5px 7px;border-radius:5px;margin-bottom:4px;'
            f'background:#fff;border:1px solid #e5e7eb">'
            f'<div style="font-size:11px;font-weight:600;color:#111827;line-height:1.35;margin-bottom:3px">'
            f'{title_short}</div>'
            f'<div style="display:flex;align-items:center;justify-content:space-between">'
            f'<span style="font-size:9px;color:#9ca3af;overflow:hidden;text-overflow:ellipsis;'
            f'white-space:nowrap;max-width:105px">{src} · {pub}</span>'
            f'<span style="font-size:10px;font-weight:700;color:{score_color(score)};'
            f'flex-shrink:0;margin-left:4px">{score}</span>'
            f'</div></a>'
        )

    # ── Column headers ─────────────────────────────────────────────────────
    col_hdrs = '<th style="width:90px;border:none;background:transparent"></th>'
    for i, (label, sub) in enumerate(MATRIX_COLS):
        total_in_col = sum(len(cells_data.get((d, label), [])) for d in row_labels)
        col_hdrs += (
            f'<th style="background:{col_hdr[i]};color:white;padding:10px 8px;'
            f'text-align:center;font-size:11px;border-radius:6px 6px 0 0;'
            f'min-width:170px;border:none">'
            f'<div style="font-size:13px;font-weight:700">{label}</div>'
            f'<div style="font-size:9px;opacity:.75;margin-top:2px">{sub}</div>'
            f'<div style="font-size:9px;opacity:.6;margin-top:1px">{total_in_col} 篇</div></th>'
        )

    # ── Rows ───────────────────────────────────────────────────────────────
    rows_html = ''
    for ri, (row_label, row_sub) in enumerate(MATRIX_ROWS):
        row_bg = '#fafafa' if ri % 2 == 0 else '#ffffff'
        cells_html = ''
        row_total = sum(len(cells_data.get((row_label, cl), [])) for cl in col_labels)
        for ci, col_label in enumerate(col_labels):
            arts = cells_data.get((row_label, col_label), [])
            bg = col_bg[ci] if arts else '#f9fafb'
            border = f'2px solid {col_hdr[ci]}22' if arts else '1px solid #f0f0f0'
            if arts:
                content = ''.join(article_card(a) for a in arts[:2])
                if len(arts) > 2:
                    content += (f'<div style="font-size:9px;color:#9ca3af;text-align:center;'
                                f'padding:2px 0">+{len(arts)-2} 篇</div>')
            else:
                content = '<span style="color:#d1d5db;font-size:10px">—</span>'
            cells_html += (
                f'<td style="background:{bg};border:{border};padding:7px;'
                f'vertical-align:top;min-height:60px">{content}</td>'
            )
        rows_html += (
            f'<tr>'
            f'<td style="background:{row_bg};padding:10px 8px;vertical-align:middle;'
            f'border-right:3px solid #e5e7eb;border-top:1px solid #f3f4f6;min-width:90px">'
            f'<div style="font-size:11px;font-weight:700;color:#1a1a2e">{row_label}</div>'
            f'<div style="font-size:9px;color:#9ca3af;margin-top:2px;line-height:1.3">{row_sub}</div>'
            f'<div style="font-size:9px;color:#d1d5db;margin-top:3px">{row_total} 篇</div>'
            f'</td>{cells_html}</tr>'
        )

    empty_cells = sum(
        1 for rl, _ in MATRIX_ROWS for cl in col_labels
        if not cells_data.get((rl, cl))
    )
    total_cells = len(MATRIX_ROWS) * len(MATRIX_COLS)

    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JD情报矩阵</title>
<style>
  * {{ box-sizing:border-box }}
  body {{ margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
          background:#f3f4f6;color:#1a1a2e }}
  .header {{ background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;padding:20px 32px }}
  .header h1 {{ margin:0 0 4px;font-size:20px;font-weight:700 }}
  .header .meta {{ font-size:12px;opacity:.65 }}
  .nav {{ background:#16213e;padding:0 32px;display:flex;align-items:center }}
  .nav a {{ color:rgba(255,255,255,.65);text-decoration:none;padding:10px 14px;
            font-size:13px;border-bottom:2px solid transparent;display:inline-block }}
  .nav a:hover,.nav a.active {{ color:white;border-bottom-color:#e74c3c }}
  .wrap {{ max-width:1500px;margin:24px auto;padding:0 20px }}
  table {{ border-collapse:separate;border-spacing:3px;width:100% }}
  td,th {{ border-radius:4px }}
  a[href]:hover {{ background:#f0f9ff !important; }}
</style>
</head>
<body>
<div class="header">
  <h1>🗺 JD情报矩阵</h1>
  <div class="meta">近30天 · 评分≥55分 · 纵轴：14个业务领域 · 横轴：5个团队能力方向 · 共 {total_articles} 篇入库</div>
</div>
{_jd_nav("sources")}
<div class="wrap">
  <div style="display:flex;gap:12px;margin-bottom:14px;flex-wrap:wrap">
    <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:10px 16px;flex:1;min-width:200px">
      <div style="font-size:9px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px">纵轴 · 业务领域 Business Domain</div>
      <div style="font-size:11px;color:#374151">8大业务域 — 每行代表一个行业情报需求场景</div>
    </div>
    <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:10px 16px;flex:1;min-width:200px">
      <div style="font-size:9px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px">横轴 · 团队能力 Working Sectors</div>
      <div style="font-size:11px;color:#374151">CTO线5个技术能力方向 — 每列代表一类团队关注的议题</div>
    </div>
    <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:10px 16px;flex:1;min-width:200px">
      <div style="font-size:9px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px">格子内容 · 实时文章</div>
      <div style="font-size:11px;color:#374151">每格显示最高分前2篇 · 点击跳转原文 · {total_cells - empty_cells}/{total_cells} 格有覆盖</div>
    </div>
  </div>
  <div style="overflow-x:auto">
    <table>
      <thead><tr>{col_hdrs}</tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
  <div style="margin-top:12px;font-size:11px;color:#9ca3af">
    数据实时从数据库读取 · 领域映射：优先读取来源专属领域，其次由AI评分的 primary_teams 字段推导
  </div>
</div>
</body>
</html>'''


def _old_render_jd_matrix():
    col_bg = ['#f5f3ff','#eff6ff','#f0fdf4','#fff7ed','#fdf2f8']
    col_hdr = ['#7c3aed','#2563eb','#059669','#d97706','#9333ea']

    def team_chip(t):
        c = TEAM_PLATE_COLORS.get(t, '#6b7280')
        return (f'<span style="display:inline-block;background:{c};color:white;'
                f'font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;'
                f'margin:2px 2px 2px 0;white-space:nowrap">{t}</span>')

    def src_tag(s):
        return (f'<span style="display:inline-block;background:#f3f4f6;color:#4b5563;'
                f'font-size:9px;padding:1px 6px;border-radius:8px;border:1px solid #e5e7eb;'
                f'margin:2px 2px 2px 0;white-space:nowrap">{s}</span>')

    # column headers
    col_hdrs = '<th style="width:90px;border:none;background:transparent"></th>'
    for i, (label, sub) in enumerate(MATRIX_COLS):
        col_hdrs += (f'<th style="background:{col_hdr[i]};color:white;padding:10px 8px;'
                     f'text-align:center;font-size:11px;border-radius:6px 6px 0 0;'
                     f'min-width:170px;border:none">'
                     f'<div style="font-size:13px;font-weight:700">{label}</div>'
                     f'<div style="font-size:9px;opacity:.8;margin-top:2px">{sub}</div></th>')

    rows_html = ''
    for ri, (row_label, row_sub) in enumerate(MATRIX_ROWS):
        row_bg = '#fafafa' if ri % 2 == 0 else '#ffffff'
        cells_html = ''
        for ci in range(len(MATRIX_COLS)):
            teams, sources = MATRIX_CELLS[ri][ci]
            bg = col_bg[ci] if sources else '#fafafa'
            border_style = f'2px solid {col_hdr[ci]}20' if sources else '1px solid #f3f4f6'
            tags  = ''.join(src_tag(s) for s in sources)
            empty_note = '' if sources else '<span style="color:#d1d5db;font-size:9px">—</span>'
            cells_html += (f'<td style="background:{bg};border:{border_style};'
                           f'padding:8px;vertical-align:top;min-height:60px">'
                           f'{tags}{empty_note}</td>')
        rows_html += (f'<tr>'
                      f'<td style="background:{row_bg};padding:10px 8px;vertical-align:middle;'
                      f'border-right:3px solid #e5e7eb;border-top:1px solid #f3f4f6;'
                      f'min-width:90px">'
                      f'<div style="font-size:11px;font-weight:700;color:#1a1a2e">{row_label}</div>'
                      f'<div style="font-size:9px;color:#9ca3af;margin-top:2px;line-height:1.4">{row_sub}</div>'
                      f'</td>{cells_html}</tr>')

    # legend
    legend_teams = ''
    for plate, teams_in_plate, color, *_ in PLATE_GROUPS:
        legend_teams += (f'<span style="display:inline-flex;align-items:center;gap:4px;'
                         f'margin-right:14px;margin-bottom:6px">'
                         f'<span style="width:10px;height:10px;background:{color};border-radius:2px;display:inline-block"></span>'
                         f'<span style="font-size:10px;color:#4b5563">{plate}</span></span>')

    # gap analysis
    gaps = []
    for ri, (row_label, _) in enumerate(MATRIX_ROWS):
        for ci, (col_label, _) in enumerate(MATRIX_COLS):
            teams, sources = MATRIX_CELLS[ri][ci]
            if not sources:
                gaps.append(f'{row_label} × {col_label}')
    gap_html = ''
    if gaps:
        gap_items = ''.join(f'<span style="display:inline-block;background:#fef3c7;color:#92400e;'
                            f'font-size:9px;padding:1px 7px;border-radius:8px;margin:2px">{g}</span>'
                            for g in gaps)
        gap_html = (f'<div style="margin-top:20px;padding:14px 16px;background:#fffbeb;'
                    f'border:1px solid #fde68a;border-radius:8px">'
                    f'<div style="font-size:11px;font-weight:700;color:#92400e;margin-bottom:6px">'
                    f'⚠️ 覆盖空白 ({len(gaps)} 个格子无情报源) — 可考虑补充</div>'
                    f'{gap_items}</div>')

    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JD情报矩阵</title>
<style>
  * {{ box-sizing:border-box }}
  body {{ margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
          background:#f3f4f6;color:#1a1a2e }}
  .header {{ background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;padding:20px 32px }}
  .header h1 {{ margin:0 0 4px;font-size:20px;font-weight:700 }}
  .header .meta {{ font-size:12px;opacity:.65 }}
  .nav {{ background:#16213e;padding:0 32px;display:flex;align-items:center }}
  .nav a {{ color:rgba(255,255,255,.65);text-decoration:none;padding:10px 14px;
            font-size:13px;border-bottom:2px solid transparent;display:inline-block }}
  .nav a:hover,.nav a.active {{ color:white;border-bottom-color:#e74c3c }}
  .wrap {{ max-width:1400px;margin:24px auto;padding:0 20px }}
  .axis-label {{ font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;
                 letter-spacing:.8px;margin-bottom:6px }}
  table {{ border-collapse:separate;border-spacing:3px;width:100% }}
  td,th {{ border-radius:4px }}
</style>
</head>
<body>
<div class="header">
  <h1>🏪 JD全球前沿情报系统</h1>
  <div class="meta">京东集团CTO部门 · 总裁简报原材料 · 按情报分排序</div>
</div>
{_jd_nav("sources")}
<div class="wrap">
  <!-- Three-dimension legend -->
  <div style="display:flex;gap:12px;margin-bottom:14px;flex-wrap:wrap">
    <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:10px 16px;flex:1;min-width:200px">
      <div style="font-size:9px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px">维度一 · 业务领域 Business Domain</div>
      <div style="font-size:11px;color:#374151">纵轴 — 京东14个核心业务领域，每行代表一个情报需求场景</div>
    </div>
    <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:10px 16px;flex:1;min-width:200px">
      <div style="font-size:9px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px">维度二 · 团队能力 Working Sectors</div>
      <div style="font-size:11px;color:#374151">横轴 — CTO线5个技术能力方向，每列代表一类团队关注的议题</div>
    </div>
    <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:10px 16px;flex:1;min-width:200px">
      <div style="font-size:9px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px">维度三 · 观点立场 Standpoint</div>
      <div style="font-size:11px;color:#374151">格子内容 — 情报源按立场分类：关键玩家 · 投资人 · 研究者 · 社区 · 媒体 · 行业 · 专利 · 政策</div>
    </div>
  </div>
  <div style="font-size:11px;color:#9ca3af;margin-bottom:8px">
    ← 产品 / 业务&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;技术 / 工程 →
  </div>
  <div style="overflow-x:auto">
    <table>
      <thead><tr>{col_hdrs}</tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
  {gap_html}
  <div style="margin-top:16px;font-size:11px;color:#9ca3af;line-height:1.8">
    共 <strong>{sum(len(MATRIX_CELLS[r][c][1]) for r in range(len(MATRIX_ROWS)) for c in range(len(MATRIX_COLS)))}</strong> 个情报源映射 ·
    <strong>{len(MATRIX_ROWS) * len(MATRIX_COLS) - len(gaps)}</strong> / {len(MATRIX_ROWS) * len(MATRIX_COLS)} 格子有覆盖
  </div>
</div>
</body>
</html>'''


@app.route('/jd/matrix')
def jd_matrix():
    from flask import redirect as _redirect
    return _redirect('/jd/sources')


@app.route('/jd/_matrix')
def jd_matrix_internal():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, feed_name, article_title, article_link,
               published_date, criteria_score, criteria
        FROM articles
        WHERE feed_name LIKE 'jd-%'
          AND criteria_score >= 55
          AND published_date >= date('now', '-30 days')
          AND criteria IS NOT NULL
        ORDER BY criteria_score DESC
        LIMIT 600
    """).fetchall()
    conn.close()

    # Build cells: {(domain_row, col_label): [row, ...]}
    cells_data = {}
    for row in rows:
        try:
            bd = json.loads(row['criteria'])
            teams = bd.get('primary_teams') or bd.get('relevant_teams') or []

            # ── Row dimension: business domain ─────────────────────────────
            # Priority 1: explicit feed→domain mapping (industry-specific feeds)
            domain = FEED_DOMAIN_MAP.get(row['feed_name'], '')
            # Priority 2: derive from primary_teams (general AI/tech feeds)
            if not domain and teams:
                domain = TEAM_TO_DOMAIN.get(teams[0], '')

            # ── Column dimension: team capability area ─────────────────────
            col = ''
            for t in teams:
                col = TEAM_TO_COL.get(t, '')
                if col:
                    break

            if domain and col:
                key = (domain, col)
                cells_data.setdefault(key, []).append(row)
        except Exception:
            pass

    return render_jd_matrix(cells_data, len(rows))


# ── Capital & Investor standpoint feed (kept for backward compat) ─────────
CAPITAL_FEEDS = [
    'jd-a16z','jd-sequoia','jd-lightspeed','jd-ycombinator',
    'jd-elad-gil','jd-tomasz-tunguz','jd-benedict-evans',
    'jd-paul-graham','jd-nathan-benaich','jd-crunchbase-news',
]
CAPITAL_LABELS = {
    'jd-a16z': 'a16z',
    'jd-sequoia': 'Sequoia Capital',
    'jd-lightspeed': 'Lightspeed Venture',
    'jd-ycombinator': 'Y Combinator',
    'jd-elad-gil': 'Elad Gil',
    'jd-tomasz-tunguz': 'Tomasz Tunguz',
    'jd-benedict-evans': 'Benedict Evans',
    'jd-paul-graham': 'Paul Graham',
    'jd-nathan-benaich': 'Nathan Benaich',
    'jd-crunchbase-news': 'Crunchbase News',
}

# ═══════════════════════════════════════════════════════════════════════════
#  资金流向 — Capital Flow Intelligence
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/jd/capital')
def jd_capital():
    return render_jd_capital()

def render_jd_capital():
    """Render the 资金流向 (Capital Flows) intelligence page."""
    html = f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JD资金流向 · 智能资本信号</title>
<style>
  * {{ box-sizing:border-box }}
  body {{ margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
          background:#f3f4f6;color:#1a1a2e }}
  .header {{ background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;padding:20px 32px }}
  .header h1 {{ margin:0 0 4px;font-size:20px;font-weight:700 }}
  .header .meta {{ font-size:12px;opacity:.65 }}
  .nav {{ background:#16213e;padding:0 32px;display:flex;align-items:center }}
  .nav a {{ color:rgba(255,255,255,.65);text-decoration:none;padding:10px 14px;
            font-size:13px;border-bottom:2px solid transparent;display:inline-block }}
  .nav a:hover,.nav a.active {{ color:white;border-bottom-color:#e74c3c }}
  .wrap {{ max-width:1100px;margin:24px auto;padding:0 20px }}
  .section {{ background:white;border:1px solid #e5e7eb;border-radius:8px;
              padding:20px 24px;margin-bottom:24px }}
  .section-title {{ font-size:16px;font-weight:700;color:#1a1a2e;margin-bottom:4px }}
  .section-desc {{ font-size:12px;color:#6b7280;margin-bottom:16px }}
  .signal-row {{ display:flex;align-items:flex-start;gap:12px;padding:10px 0;
                 border-top:1px solid #f3f4f6 }}
  .signal-icon {{ font-size:20px;flex-shrink:0;width:32px;text-align:center }}
  .signal-body {{ flex:1;min-width:0 }}
  .signal-name {{ font-size:13px;font-weight:600;color:#111827 }}
  .signal-desc {{ font-size:11px;color:#6b7280;line-height:1.6;margin-top:2px }}
  .tag {{ display:inline-block;font-size:10px;font-weight:600;border-radius:4px;
          padding:2px 6px;margin-right:4px }}
  .tag-live {{ background:#dcfce7;color:#166534 }}
  .tag-paid {{ background:#fef3c7;color:#92400e }}
  .tag-manual {{ background:#eff6ff;color:#1e40af }}
</style>
</head>
<body>
<div class="header">
  <h1>💰 资金流向</h1>
  <div class="meta">最早期市场信号 · 私募融资 · 机构仓位 · 智能资本观点</div>
</div>
{_jd_nav("capital")}
<div class="wrap">

  <div style="background:#fef3c7;border:1px solid #fde68a;border-radius:8px;padding:12px 16px;
              margin-bottom:24px;font-size:12px;color:#92400e;line-height:1.7">
    <strong>📌 资金流向说明</strong> — 本页追踪「智能资本」的最早期动作：
    Form D私募备案（融资发生后15天内强制披露）、13F机构仓位变化、S-1上市申请、
    VC合伙人公开观点。这些信号比媒体报道早数周至数月。
    <strong>注意</strong>：ETF资金流入属于滞后信号，不在本页追踪范围。
  </div>

  <!-- ── Section 1: 私募市场最早信号 ── -->
  <div class="section">
    <div class="section-title">📋 私募市场最早信号</div>
    <div class="section-desc">Form D 备案 · S-1 上市申请 · 13D/G 大额持仓披露 · Crunchbase · YC批次</div>

    <div class="signal-row">
      <div class="signal-icon">🇺🇸</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-live">实时接入</span>
          SEC EDGAR — Form D (私募融资备案)
        </div>
        <div class="signal-desc">
          美国证券法要求：私募融资完成后<strong>15天内</strong>强制向SEC备案Form D。
          这是最早的官方融资信号，比TechCrunch报道早数周。
          涵盖：融资金额、投资者类型、公司注册地。<br>
          <a href="https://efts.sec.gov/LATEST/search-index?q=%22artificial+intelligence%22&dateRange=custom&startdt={__import__('datetime').date.today().strftime('%Y-%m-%d')}&forms=D"
             target="_blank" style="color:#2563eb">→ 今日AI相关Form D备案</a> ·
          <a href="https://efts.sec.gov/LATEST/search-index?q=%22machine+learning%22&forms=D&dateRange=custom&startdt={(__import__('datetime').date.today() - __import__('datetime').timedelta(days=7)).strftime('%Y-%m-%d')}"
             target="_blank" style="color:#2563eb">近7天ML相关</a>
        </div>
      </div>
    </div>

    <div class="signal-row">
      <div class="signal-icon">📈</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-live">实时接入</span>
          SEC EDGAR — S-1 (IPO申请)
        </div>
        <div class="signal-desc">
          公司IPO前的完整财务披露。S-1包含商业模式、竞争格局、风险因素，
          是了解新兴科技公司最详尽的公开文件。<br>
          <a href="https://efts.sec.gov/LATEST/search-index?q=%22artificial+intelligence%22&forms=S-1&dateRange=custom&startdt={(__import__('datetime').date.today() - __import__('datetime').timedelta(days=30)).strftime('%Y-%m-%d')}"
             target="_blank" style="color:#2563eb">→ 近30天AI相关S-1</a>
        </div>
      </div>
    </div>

    <div class="signal-row">
      <div class="signal-icon">🎯</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-live">实时接入</span>
          SEC EDGAR — 13D/G (大额持仓披露)
        </div>
        <div class="signal-desc">
          持股超过5%时须在10天内披露。13D=积极投资者（有意图影响公司），
          13G=被动持仓。追踪顶级机构对AI/科技公司的大额建仓动作。<br>
          <a href="https://efts.sec.gov/LATEST/search-index?q=%22artificial+intelligence%22&forms=SC+13D,SC+13G"
             target="_blank" style="color:#2563eb">→ AI相关13D/13G</a>
        </div>
      </div>
    </div>

    <div class="signal-row">
      <div class="signal-icon">🚀</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-manual">人工订阅</span>
          Crunchbase / 36氪融资快讯
        </div>
        <div class="signal-desc">
          Crunchbase免费版有24小时延迟，但覆盖全球。36氪融资快讯覆盖中国早期项目。
          两者结合可基本覆盖中美两市的种子轮至A轮信号。
        </div>
      </div>
    </div>

    <div class="signal-row">
      <div class="signal-icon">🐢</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-live">季度更新</span>
          Y Combinator 批次
        </div>
        <div class="signal-desc">
          YC每年两个批次（W/S），官方公司列表在Demo Day前约2周公开。
          YC公司的赛道分布是验证「什么方向正在被最聪明的创始人押注」的领先指标。<br>
          <a href="https://www.ycombinator.com/companies?batch=W25" target="_blank"
             style="color:#2563eb">→ W25批次公司列表</a>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Section 2: 机构仓位变化 ── -->
  <div class="section">
    <div class="section-title">🏦 机构仓位变化</div>
    <div class="section-desc">13F季报 · 私募数据库 · 二级市场聪明钱流向</div>

    <div class="signal-row">
      <div class="signal-icon">📊</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-live">季度更新</span>
          SEC 13F-HR (机构持仓季报)
        </div>
        <div class="signal-desc">
          管理资产超1亿美元的机构须每季度披露所有股票持仓。
          延迟45天，但对比相邻季度可发现「聪明钱」的仓位变化方向。
          重点追踪：a16z、Tiger Global、Coatue、Dragoneer对AI标的的加减仓。<br>
          <a href="https://efts.sec.gov/LATEST/search-index?q=%22NVIDIA%22+%22artificial+intelligence%22&forms=13F-HR"
             target="_blank" style="color:#2563eb">→ 含AI持仓的13F搜索</a>
        </div>
      </div>
    </div>

    <div class="signal-row">
      <div class="signal-icon">💼</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-paid">付费数据库</span>
          PitchBook — 私募交易数据库
        </div>
        <div class="signal-desc">
          最全面的私募融资数据库，包含未公开轮次、估值、LP信息。
          如您提供账号Cookie，可解析PitchBook的公司页面和融资历史。
          支持字段：融资日期、轮次、金额、投资机构、估值（如披露）。
        </div>
      </div>
    </div>

    <div class="signal-row">
      <div class="signal-icon">📉</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-paid">付费数据库</span>
          CB Insights — 市场地图与融资追踪
        </div>
        <div class="signal-desc">
          提供API接口（需API Key）。特色：市场地图（Market Map）自动分类竞争格局，
          独角兽追踪，以及「Mosaic Score」信号（综合社交媒体、招聘、新闻的健康度评分）。
        </div>
      </div>
    </div>

    <div class="signal-row">
      <div class="signal-icon">📋</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-paid">付费数据库</span>
          Carta — 股权与期权数据
        </div>
        <div class="signal-desc">
          Carta State of Private Markets报告（免费季报）提供汇总的私募市场数据。
          如有Carta账号，可获取特定公司的409A估值和股权结构（需公司授权）。
        </div>
      </div>
    </div>
  </div>

  <!-- ── Section 3: 智能资本观点 ── -->
  <div class="section">
    <div class="section-title">🧠 智能资本观点</div>
    <div class="section-desc">顶级VC合伙人公开撰文 · 投资论文 · 赛道判断</div>

    <div class="signal-row">
      <div class="signal-icon">🔵</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-live">RSS已接入</span>
          a16z · Andreessen Horowitz
        </div>
        <div class="signal-desc">
          AI/生物/加密三大主题。重点关注：Marc Andreessen的「Why AI Will Save the World」
          系列续集，Ben Horowitz的企业软件论断。
          <a href="https://a16z.com/feed/" target="_blank" style="color:#2563eb">RSS ↗</a>
        </div>
      </div>
    </div>

    <div class="signal-row">
      <div class="signal-icon">🌲</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-live">RSS已接入</span>
          Sequoia Capital
        </div>
        <div class="signal-desc">
          每年的「RIP Good Times」和「AI's $600B Question」类年度判断是重要参考。
          <a href="https://www.sequoiacap.com/our-views/feed/" target="_blank" style="color:#2563eb">RSS ↗</a>
        </div>
      </div>
    </div>

    <div class="signal-row">
      <div class="signal-icon">⚡</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-manual">KOL已追踪</span>
          Elad Gil · Tomasz Tunguz · Nathan Benaich
        </div>
        <div class="signal-desc">
          Elad Gil（高成长公司手册作者）、Tomasz Tunguz（Theory Ventures合伙人）、
          Nathan Benaich（Air Street Capital，年度AI报告作者）——三人的公开写作
          代表了最有深度的VC视角，比机构官方博客更坦率。
        </div>
      </div>
    </div>

    <div class="signal-row">
      <div class="signal-icon">📝</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-manual">人工追踪</span>
          Paul Graham Essays · Sam Altman Blog
        </div>
        <div class="signal-desc">
          PG的文章通常预判创业生态方向变化（如「Post-YC Founder Syndrome」）。
          Sam Altman的博客是OpenAI战略方向的间接信号。
        </div>
      </div>
    </div>
  </div>

  <!-- ── Section 4: 付费私募情报 ── -->
  <div class="section">
    <div class="section-title">🔒 付费私募情报</div>
    <div class="section-desc">需账号或API Key · 提供后可自动解析</div>

    <div class="signal-row">
      <div class="signal-icon">📰</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-paid">付费订阅</span>
          The Information
        </div>
        <div class="signal-desc">
          硅谷最权威的付费科技新闻，独家融资/收购信息平均比TechCrunch早1-2周。
          提供账号Cookie后可解析文章全文。价格：$399/年（个人）。
        </div>
      </div>
    </div>

    <div class="signal-row">
      <div class="signal-icon">🌍</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-paid">付费订阅</span>
          DealStreetAsia
        </div>
        <div class="signal-desc">
          东南亚和中国最专业的私募报道，覆盖Pre-A至Pre-IPO阶段。
          有限的RSS feed可免费接入（已配置）；深度报道需付费账号。
          <a href="https://www.dealstreetasia.com/feed/" target="_blank" style="color:#2563eb">免费RSS ↗</a>
        </div>
      </div>
    </div>

    <div class="signal-row">
      <div class="signal-icon">🏔</div>
      <div class="signal-body">
        <div class="signal-name">
          <span class="tag tag-paid">企业版</span>
          Preqin · Bloomberg Terminal
        </div>
        <div class="signal-desc">
          Preqin：PE/VC基金级别数据（LP承诺、基金业绩、GP信息）。
          Bloomberg Terminal：实时私募债券发行、SPAC、大宗交易。
          两者均需企业订阅，提供API后可接入自动拉取。
        </div>
      </div>
    </div>
  </div>

</div>
</body>
</html>'''
    return html


@app.route('/jd/sources')
def jd_sources():
    # ── Build matrix section ──────────────────────────────────────────────
    conn_m = sqlite3.connect(DB_PATH)
    conn_m.row_factory = sqlite3.Row
    matrix_rows = conn_m.execute("""
        SELECT id, feed_name, article_title, article_link,
               published_date, criteria_score, criteria
        FROM articles
        WHERE feed_name LIKE 'jd-%'
          AND criteria_score >= 55
          AND published_date >= date('now', '-30 days')
          AND criteria IS NOT NULL
        ORDER BY criteria_score DESC
        LIMIT 600
    """).fetchall()
    conn_m.close()
    matrix_cells = {}
    for row in matrix_rows:
        try:
            bd = json.loads(row['criteria'])
            teams = bd.get('primary_teams') or bd.get('relevant_teams') or []
            domain = FEED_DOMAIN_MAP.get(row['feed_name'], '')
            if not domain and teams:
                domain = TEAM_TO_DOMAIN.get(teams[0], '')
            col = ''
            for t in teams:
                col = TEAM_TO_COL.get(t, '')
                if col:
                    break
            if domain and col:
                matrix_cells.setdefault((domain, col), []).append(row)
        except Exception:
            pass
    matrix_section_html = _render_matrix_table(matrix_cells)

    stats = _get_source_stats()
    rss_count = len(JD_SOURCES)
    total_articles = sum(s.get('total', 0) for s in stats.values())
    total_high = sum(s.get('high', 0) for s in stats.values())
    name_to_src = {s['name']: s for s in JD_SOURCES}

    # ── Status badge helpers ──────────────────────────────────────────────
    STATUS = {
        'auto':    ('<span style="display:inline-flex;align-items:center;gap:5px;background:#f0fdf4;'
                    'color:#166534;border:1px solid #bbf7d0;padding:2px 8px;border-radius:10px;'
                    'font-size:11px;font-weight:600">🟢 自动抓取</span>'),
        'paid':    ('<span style="display:inline-flex;align-items:center;gap:5px;background:#fffbeb;'
                    'color:#92400e;border:1px solid #fde68a;padding:2px 8px;border-radius:10px;'
                    'font-size:11px;font-weight:600">🟡 付费订阅</span>'),
        'manual':  ('<span style="display:inline-flex;align-items:center;gap:5px;background:#eff6ff;'
                    'color:#1e40af;border:1px solid #bfdbfe;padding:2px 8px;border-radius:10px;'
                    'font-size:11px;font-weight:600">🔵 人工监控</span>'),
        'pending': ('<span style="display:inline-flex;align-items:center;gap:5px;background:#f9fafb;'
                    'color:#6b7280;border:1px solid #e5e7eb;padding:2px 8px;border-radius:10px;'
                    'font-size:11px;font-weight:600">⚪ 待接入</span>'),
    }

    def rss_src(name):
        src = name_to_src.get(name, {})
        st = stats.get(name, {})
        n, h, avg = st.get('total',0), st.get('high',0), int(st.get('avg_score') or 0)
        score_str = (f'<span style="font-size:12px;font-weight:700;color:{"#c0392b" if avg>=70 else "#e67e22" if avg>=50 else "#6b7280"}">{avg}分均值</span>'
                     f'<span style="font-size:11px;color:#9ca3af"> · {n}篇</span>' if n else
                     '<span style="font-size:11px;color:#9ca3af">待抓取</span>')
        url = src.get('url','')
        return (src.get('label', name), url, src.get('criteria',''), 'auto', score_str)

    def ext_src(label, url, desc, status):
        return (label, url, desc, status, STATUS[status])

    def x_src(handle, name, role, feed_name=None):
        """X/Twitter key figure entry with endorsement weight badge."""
        weight = X_ENDORSER_WEIGHTS.get(handle, X_ENDORSER_WEIGHTS.get(handle.lower(), 0))
        # Weight badge: colour scales with strength
        if weight >= 0.25:
            w_color, w_label = '#b45309', '核心信号'
        elif weight >= 0.18:
            w_color, w_label = '#1d4ed8', '强信号'
        else:
            w_color, w_label = '#6b7280', '监测中'
        bars = round(weight / 0.30 * 5)
        bar_html = ''.join(
            f'<span style="display:inline-block;width:5px;height:10px;border-radius:1px;margin-right:1px;'
            f'background:{"" + w_color if i < bars else "#e5e7eb"}"></span>'
            for i in range(5)
        )
        weight_badge = (
            f'<div style="display:inline-flex;align-items:center;gap:5px">'
            f'<span style="font-size:11px;font-weight:700;color:{w_color}">{w_label}</span>'
            f'<span style="font-size:10px;color:#9ca3af">×{weight:.2f}</span>'
            f'<div style="display:inline-flex;align-items:center;gap:1px;margin-left:2px">{bar_html}</div>'
            f'</div>'
        )
        # Article count from DB if we have a feed
        article_info = ''
        if feed_name:
            st = stats.get(feed_name, {})
            n = st.get('total', 0)
            if n:
                article_info = f'<br><span style="font-size:10px;color:#9ca3af">{n}篇已入库</span>'
        url = f'https://nitter.net/{handle}/rss' if feed_name else f'https://x.com/{handle}'
        status = 'auto' if feed_name else 'manual'
        return (
            f'@{handle} · {name}',
            url,
            role,
            status,
            weight_badge + article_info
        )

    def weibo_src(uid_or_handle, name, role):
        """Weibo planned account entry."""
        right = ('<span style="display:inline-flex;align-items:center;gap:5px;background:#fff7ed;'
                 'color:#c2410c;border:1px solid #fed7aa;padding:2px 8px;border-radius:10px;'
                 'font-size:11px;font-weight:600">🔶 规划接入</span>')
        return (f'{name}', f'https://weibo.com/{uid_or_handle}', role, 'pending', right)

    # ── Full source registry — organized by STANDPOINT ──────────────────
    # Each group: (group_label, group_desc, color, [(label, url, desc, status, right_col), ...])
    # Third dimension: 观点立场 — who is speaking and from what angle
    REGISTRY = [

    # ─────────────────────────────────────────────────────────────────────
    # 立场维度 1：关键玩家官方信源
    # 他们就是舞台上的主角 — 直接来自技术格局塑造者的第一手声音
    # ─────────────────────────────────────────────────────────────────────
      ('🌟 关键玩家官方信源',
       '舞台上的主角们直接发声 — AI实验室、平台公司、竞对巨头的官方博客，最权威的一手信号', '#7c3aed', [
        # 全球AI实验室
        rss_src('jd-openai-blog'),
        ext_src('Anthropic Blog', 'https://www.anthropic.com/news', 'Claude系列模型、AI安全研究、产品功能官方发布', 'pending'),
        rss_src('jd-deepmind-blog'),
        rss_src('jd-google-ai-blog'),
        rss_src('jd-meta-engineering'),
        rss_src('jd-microsoft-research'),
        rss_src('jd-huggingface-blog'),
        rss_src('jd-nvidia-developer'),
        rss_src('jd-aws-aiml'),
        # 中国AI主要玩家
        rss_src('jd-qwenlm'),
        ext_src('ByteDance Research', 'https://research.bytedance.com', '字节跳动AI研究院，TikTok算法、推荐系统、多模态', 'pending'),
        ext_src('Tencent AI Lab', 'https://ai.tencent.com/ailab', '腾讯AI实验室，无公开RSS', 'pending'),
        ext_src('Alibaba DAMO Academy', 'https://damo.alibaba.com', '达摩院，NLP/CV/量子计算前沿', 'pending'),
        ext_src('Baidu AI Blog', 'https://ai.baidu.com', '百度AI官方，文心一言/飞桨/自动驾驶', 'pending'),
        # 直接竞对的工程博客
        rss_src('jd-amazon-science'),
        rss_src('jd-walmart-tech'),
        rss_src('jd-meituan-tech'),
        rss_src('jd-alizila'),
        rss_src('jd-shopify'),
        rss_src('jd-grab-engineering'),
        rss_src('jd-shopee-blog'),
        rss_src('jd-instacart-tech'),
        rss_src('jd-databricks'),
        rss_src('jd-langchain-blog'),
        # Twitter/X via RSSHub (auto)
        rss_src('jd-twitter-sama'),
        rss_src('jd-twitter-demishassabis'),
        ext_src('字节跳动技术博客', 'https://mp.weixin.qq.com/s/bytedance-tech', '仅微信公众号', 'manual'),
        ext_src('腾讯技术工程', 'https://mp.weixin.qq.com/s/tencent-tech', '微信/广告系统工程实践 — 仅微信公众号', 'manual'),
        ext_src('菜鸟技术 (Cainiao)', 'https://mp.weixin.qq.com/s/cainiao-tech', '菜鸟物流AI技术 — 仅微信公众号', 'manual'),
        ext_src('拼多多/Temu Tech', '', '无公开技术博客，关注招聘JD和技术分享会议', 'pending'),
      ]),

    # ─────────────────────────────────────────────────────────────────────
    # 立场维度 2：资本动向与投资人观点
    # 投资决策是技术趋势最领先的指标，往往早于产品发布12-24个月
    # ─────────────────────────────────────────────────────────────────────
      ('💰 资本动向与投资人观点',
       '风险资本家和战略投资人的第一手判断 — 他们的下注方向是行业走势最超前的信号', '#059669', [
        rss_src('jd-a16z'),
        rss_src('jd-sequoia'),
        rss_src('jd-lightspeed'),
        rss_src('jd-ycombinator'),
        rss_src('jd-elad-gil'),
        rss_src('jd-tomasz-tunguz'),
        rss_src('jd-benedict-evans'),
        rss_src('jd-paul-graham'),
        rss_src('jd-nathan-benaich'),
        rss_src('jd-crunchbase-news'),
        ext_src('PitchBook / NVCA', 'https://pitchbook.com', 'VC投资数据库，追踪AI领域融资轮次与估值变化', 'paid'),
        ext_src('CB Insights', 'https://www.cbinsights.com', '技术投资情报，市场地图与独角兽追踪', 'paid'),
        ext_src('Crunchbase Pro', 'https://www.crunchbase.com', '全球融资事件实时追踪，发现未公开的早期投资信号', 'paid'),
        ext_src('Bessemer Venture Atlas', 'https://www.bvp.com/atlas', 'Bessemer年度报告，SaaS和云AI市场标杆数据', 'pending'),
        ext_src('GGV Capital (纪源资本)', 'https://www.ggvc.com/insights', '中美双市场投资视角', 'pending'),
        ext_src('启明创投 Qiming', 'https://www.qimingvc.com', '中国头部VC，消费/医疗/科技赛道判断', 'pending'),
        ext_src('高瓴 Hillhouse', 'https://www.hillhousecap.com', '新消费与科技产业深度研究', 'pending'),
        ext_src('天眼查 / 企查查', 'https://www.tianyancha.com', '中国企业工商数据，股权变更/融资轮次/高管变动', 'paid'),
        ext_src('SEC EDGAR', 'https://www.sec.gov/cgi-bin/browse-edgar', '美国上市公司AI相关披露，含资本支出和战略描述', 'pending'),
        ext_src('港交所 HKEX', 'https://www.hkexnews.hk', '港股上市公司重大事项公告，含阿里/腾讯/竞对动态', 'pending'),
        ext_src('Mergermarket', 'https://www.mergermarket.com', 'AI领域并购交易追踪，竞对填补能力缺口的信号', 'paid'),
        ext_src('LinkedIn Jobs (招聘信号)', 'https://linkedin.com/jobs', '竞对公司技术岗位招聘，揭示6-12个月后的产品方向', 'manual'),
        ext_src('Boss直聘 / 猎聘', 'https://www.zhipin.com', '国内大厂AI岗位招聘趋势，判断各公司技术投入重点', 'manual'),
        # Twitter/X via RSSHub (auto)
        rss_src('jd-twitter-pmarca'),
        rss_src('jd-twitter-naval'),
      ]),

    # ─────────────────────────────────────────────────────────────────────
    # 立场维度 2：顶尖研究者与工程师
    # 一线从业者的技术判断，领先产品发布3-12个月，是学术与工业界的桥梁
    # ─────────────────────────────────────────────────────────────────────
      ('🧠 顶尖研究者与工程师',
       '一线AI研究员和工程师的个人博客与技术通讯 — 这里的观点往往比产品发布早6-12个月', '#d97706', [
        rss_src('jd-chip-huyen'),
        rss_src('jd-interconnects'),
        rss_src('jd-karpathy'),
        rss_src('jd-lillog'),
        rss_src('jd-eugeneyan'),
        rss_src('jd-swyx'),
        rss_src('jd-fastai'),
        rss_src('jd-import-ai'),
        rss_src('jd-the-gradient'),
        rss_src('jd-synced'),
        rss_src('jd-nngroup'),
        rss_src('jd-sre-weekly'),
        rss_src('jd-ieee-spectrum-robotics'),
        rss_src('jd-stripe-blog'),
        rss_src('jd-simonwillison'),
        rss_src('jd-latent-space'),
        rss_src('jd-towards-ds'),
        rss_src('jd-lesswrong'),
        # Twitter/X via RSSHub (auto)
        rss_src('jd-twitter-karpathy'),
        rss_src('jd-twitter-ylecun'),
        rss_src('jd-twitter-drjimfan'),
        rss_src('jd-twitter-fchollet'),
        ext_src('Ilya Sutskever', 'https://x.com/ilyasut', 'SSI创始人，OpenAI联合创始人 — X/Twitter', 'pending'),
        ext_src('Yi Ma (马毅)', 'https://x.com/YiMaTweets', '加州大学伯克利分校教授，白盒AI/可解释性研究 — X/Twitter', 'pending'),
        rss_src('jd-arxiv-ir'),
        rss_src('jd-arxiv-lg'),
        ext_src('Papers With Code', 'https://paperswithcode.com', 'AI论文+代码实现+SOTA排行榜，覆盖所有主流任务', 'pending'),
        ext_src('OpenReview.net', 'https://openreview.net', 'NeurIPS/ICML/ICLR投稿预审平台，论文公开早于正式发表3个月', 'pending'),
        ext_src('Hugging Face Papers', 'https://huggingface.co/papers', '每日精选AI论文，含作者评论和模型下载数据', 'pending'),
        ext_src('Semantic Scholar', 'https://www.semanticscholar.org', '引用图谱分析，追踪高被引新论文', 'pending'),
      ]),

    # ─────────────────────────────────────────────────────────────────────
    # 立场维度 3：产品技术社区
    # 从业者社区的第一反应和内部讨论 — 产品好坏、技术真伪在这里最快浮出水面
    # ─────────────────────────────────────────────────────────────────────
      ('💬 产品技术社区',
       '从业者社区的集体判断 — 新产品发布后的第一反应，是过滤公关稿最快的渠道', '#6366f1', [
        rss_src('jd-github-blog'),
        rss_src('jd-ux-collective'),
        rss_src('jd-smashing-magazine'),
        rss_src('jd-infoq'),
        rss_src('jd-woshipm'),
        rss_src('jd-hackernews'),
        ext_src('Hacker News (unfiltered)', 'https://news.ycombinator.com', '未过滤全站 — 已通过 jd-hackernews 接入AI精选版（≥50分+关键词过滤）', 'manual'),
        ext_src('X (Twitter) — AI研究者列表', 'https://x.com', '追踪Karpathy/LeCun/Ilya/Sam Altman等50+账号，捕捉产品内测和技术预告', 'manual'),
        ext_src('X (Twitter) — VC/投资人列表', 'https://x.com', '追踪Marc Andreessen/Sarah Guo/Elad Gil等30+账号，融资信号最快来源', 'manual'),
        ext_src('X (Twitter) — 中国科技圈', 'https://x.com', '追踪国内创业者海外账号，内外信息差最大的渠道', 'manual'),
        ext_src('LinkedIn — 高管动态', 'https://linkedin.com', '大厂VP/Director的战略声明，产品方向往往在此先透露', 'manual'),
        ext_src('Reddit r/MachineLearning', 'https://reddit.com/r/MachineLearning', 'AI研究者社区，论文解读和争议最快浮出', 'pending'),
        ext_src('Discord — AI社区', 'https://discord.gg', 'Hugging Face Discord、Latent Space等，模型测试第一手反馈', 'manual'),
        ext_src('微博科技圈', 'https://weibo.com', '科技高管和研究员个人账号，产品泄露和内部消息最快传播渠道', 'manual'),
        ext_src('知乎 (Zhihu)', 'https://www.zhihu.com', '专家问答，AI研究员解读新论文、从业者评价竞品', 'manual'),
      ]),

    # ─────────────────────────────────────────────────────────────────────
    # 立场维度 4：中外科技媒体
    # 记者视角的报道 — 覆盖广、有独家，是感知行业舆论和竞对叙事的主渠道
    # ─────────────────────────────────────────────────────────────────────
      ('📰 中外科技媒体',
       '国内外主流科技记者和媒体机构 — 覆盖广泛，是感知行业舆论和竞对公关叙事的主渠道', '#2563eb', [
        rss_src('jd-techcrunch-ai'),
        rss_src('jd-verge-ai'),
        rss_src('jd-venturebeat-ai'),
        rss_src('jd-mit-tech-review'),
        rss_src('jd-wired'),
        rss_src('jd-platformer'),
        rss_src('jd-bloomberg-tech'),
        rss_src('jd-stratechery'),
        rss_src('jd-mittr-china'),
        rss_src('jd-restofworld'),
        rss_src('jd-36kr'),
        rss_src('jd-36kr-ai'),
        rss_src('jd-36kr-funding'),
        rss_src('jd-36kr-global'),
        rss_src('jd-leiphone'),
        rss_src('jd-huxiu'),
        rss_src('jd-pingwest'),
        rss_src('jd-ebrun'),
        rss_src('jd-technode'),
        rss_src('jd-pandaily'),
        rss_src('jd-scmp-tech'),
        rss_src('jd-techinasia'),
        ext_src('The Information', 'https://www.theinformation.com', '顶级付费科技媒体，独家报道大厂内幕和战略决策', 'paid'),
        ext_src('Financial Times Tech', 'https://www.ft.com/technology', '金融时报科技版，覆盖科技监管与资本市场', 'paid'),
        ext_src('WSJ Tech', 'https://www.wsj.com/tech', '华尔街日报科技版，企业AI战略与财报解读', 'paid'),
        ext_src('Bloomberg Intelligence', 'https://www.bloomberg.com/intelligence', '彭博分析报告，行业数据与竞争格局深度分析', 'paid'),
        ext_src('量子位 (Qbitai)', 'https://www.qbitai.com', '国内AI产品与商业化动态，覆盖初创公司和大厂新品 — 屏蔽RSS需人工监控', 'manual'),
        ext_src('机器之心 (Jiqizhixin)', 'https://www.jiqizhixin.com', '国内最权威AI媒体，覆盖国内外模型发布和算法突破 — 无公开RSS', 'manual'),
        ext_src('极客公园 (GeekPark)', 'https://www.geekpark.net', '科技产品与创业报道，无公开RSS', 'manual'),
        ext_src('第一财经 (Yicai)', 'https://www.yicai.com', '国内权威财经媒体，AI商业化与上市公司动态', 'manual'),
        ext_src('WeChat 公众号生态', 'https://mp.weixin.qq.com', '字节AI、阿里云、腾讯AI Lab等官方公众号 — 需订阅监控', 'manual'),
        rss_src('jd-axios-ai'),
      ]),

    # ─────────────────────────────────────────────────────────────────────
    # 立场维度 5：行业媒体和研究
    # 各垂直领域的专业视角 — 覆盖零售/物流/金融/健康/能源/广告/机器人等行业深度
    # ─────────────────────────────────────────────────────────────────────
      ('🏭 行业媒体和研究',
       '各垂直行业的专业媒体 — 深度远超通用科技媒体，直接映射京东零售/物流/金融/健康等各业务线', '#0891b2', [
        # 零售与电商
        rss_src('jd-modern-retail'),
        rss_src('jd-digital-commerce'),
        rss_src('jd-retail-dive'),
        rss_src('jd-practical-ecom'),
        rss_src('jd-krasia'),
        ext_src('Gartner Retail', 'https://www.gartner.com/en/retail', 'Gartner零售IT研究报告，覆盖技术采购决策趋势', 'paid'),
        ext_src('Forrester Retail', 'https://www.forrester.com/retail', 'Forrester零售行业报告，消费者行为与技术采纳', 'paid'),
        # 物流与供应链
        rss_src('jd-freightwaves'),
        rss_src('jd-loadstar'),
        rss_src('jd-supply-chain-dive'),
        rss_src('jd-logistics-viewpoints'),
        rss_src('jd-dc-velocity'),
        rss_src('jd-supplychainbrain'),
        # 内容直播 / 社交社区
        rss_src('jd-digiday'),
        rss_src('jd-naavik'),
        rss_src('jd-woshipm'),
        ext_src('晚点LatePost', 'https://www.latepost.com', '国内最权威商业调查媒体，大厂内幕与竞对战略深度报道 — 无公开RSS，人工监控', 'manual'),
        ext_src('新榜 (xinbang.com)', 'https://www.newrank.cn', '内容/直播/公众号数据，电商直播GMV排行与创作者经济趋势 — 无公开RSS', 'manual'),
        ext_src('卡思数据', 'https://www.caasdata.com', '抖音/快手/B站视频内容数据，直播电商选品和流量趋势 — 付费平台', 'paid'),
        # 广告与营销科技
        rss_src('jd-adexchanger'),
        # 金融科技与支付
        rss_src('jd-finextra'),
        rss_src('jd-pymnts'),
        rss_src('jd-sift-blog'),
        rss_src('jd-payments-dive'),
        rss_src('jd-digital-transactions'),
        ext_src('The Paypers', 'https://thepaypers.com', '全球支付行业深度报道，新支付方式和清算网络动态', 'pending'),
        ext_src('Nilson Report', 'https://nilsonreport.com', '支付行业圣经：全球卡组织交易量、interchange收益分配、网络市场份额数据', 'paid'),
        ext_src('BIS (国际清算银行)', 'https://www.bis.org/cpmi', 'CPMI委员会报告：跨境支付改革G20路线图、CBDC互操作标准、FX结算风险研究；无公开RSS，人工监控', 'manual'),
        ext_src('SWIFT Newsroom', 'https://www.swift.com/news-events', 'SWIFT GPI进展、CBDC连接标准、跨境结算轨道升级；无公开RSS，人工监控', 'manual'),
        ext_src('中国人民银行政策', 'https://www.pbc.gov.cn', '人民银行金融科技监管政策，直接影响京东金融', 'manual'),
        # 具身智能与机器人
        rss_src('jd-the-robot-report'),
        # 交互设计
        rss_src('jd-ux-collective'),
        rss_src('jd-smashing-magazine'),
        # 能源与可持续发展
        rss_src('jd-cleantechnica'),
        rss_src('jd-carbon-brief'),
        rss_src('jd-trellis'),
        rss_src('jd-canary-media'),
        # 医疗健康
        rss_src('jd-stat-health-tech'),
        rss_src('jd-medcity-news'),
        rss_src('jd-mobihealthnews'),
        # 基础效能
        rss_src('jd-infoq'),
        rss_src('jd-github-blog'),
        rss_src('jd-google-security'),
        rss_src('jd-cloudflare-security'),
        rss_src('jd-ars-technica'),
        # 基础通讯
        rss_src('jd-rcr-wireless'),
        rss_src('jd-fierce-electronics'),
        ext_src('C114通信网', 'https://www.c114.com.cn', '国内5G/AI通信产业最权威门户，运营商动态和网络设备商竞争 — 无公开RSS，人工监控', 'manual'),
        ext_src('飞象网', 'https://www.cctime.com', '通信行业垂直媒体，5G商业应用和工业互联网动态 — 无公开RSS，人工监控', 'manual'),
        ext_src('通信世界网', 'https://www.cww.net.cn', '工信部关联媒体，政策预告和行业标准动态最快披露 — 无公开RSS，人工监控', 'manual'),
        ext_src('中国信通院 (CAICT)', 'https://www.caict.ac.cn', '工信部旗下研究院，发布行业白皮书和AI/通信政策解读 — 人工监控', 'manual'),
        # 汽车与出行
        rss_src('jd-electrek'),
        rss_src('jd-electrive'),
      ]),

    # ─────────────────────────────────────────────────────────────────────
    # 立场维度 6：政策与专利（合并）
    # 两类信号性质相同：均是法律约束下的强制披露，不存在PR成分
    # 专利申请早于产品发布6-18个月；监管政策早于行业变化12-24个月
    # ─────────────────────────────────────────────────────────────────────
      ('📜 政策与专利',
       '法律强制披露信号 — 专利申请领先产品6-18个月，监管政策领先行业变化12-24个月', '#7c3aed', [
        # 专利情报
        ext_src('Google Patents', 'https://patents.google.com', '全球专利全文检索，可按申请人/关键词订阅，追踪各大厂AI/推荐/物流相关专利', 'manual'),
        ext_src('WIPO PATENTSCOPE', 'https://patentscope.wipo.int', 'PCT国际专利申请数据库，覆盖阿里/腾讯/百度/字节等中国申请人国际布局', 'manual'),
        ext_src('CNIPA 国家知识产权局', 'https://www.cnipa.gov.cn', '中国专利申请全库，关键词订阅可自动推送竞对新申请动态', 'pending'),
        ext_src('USPTO Patent Full-Text', 'https://ppubs.uspto.gov', '美国专利局全文检索，追踪亚马逊/Meta/Google零售AI专利布局', 'manual'),
        ext_src('EPO Espacenet', 'https://www.epo.org/en/searching-for-patents/technical/espacenet', '欧洲专利局检索，覆盖欧洲市场竞对技术布局动态', 'manual'),
        ext_src('Lens.org', 'https://www.lens.org', '开源专利+学术论文关联检索，可免费设RSS订阅特定机构专利申请', 'pending'),
        ext_src('Derwent Innovation (Clarivate)', 'https://www.derwentinnovation.com', '专利分析付费平台，技术景观图与竞对专利组合深度分析', 'paid'),
        # 政策与监管
        rss_src('jd-eu-digital'),
        rss_src('jd-eu-ai-act'),
        rss_src('jd-nist-ai'),
        rss_src('jd-ftc-tech'),
        rss_src('jd-atlantic-council-cbdc'),
        rss_src('jd-coin-center'),
        ext_src('MIIT 工信部', 'https://www.miit.gov.cn', '中国工业和信息化部，AI产业政策、算力规划、数据法规', 'manual'),
        ext_src('CAC 网信办', 'https://www.cac.gov.cn', '国家互联网信息办公室，大模型备案/内容监管/数据安全', 'manual'),
        ext_src('国务院AI政策', 'https://www.gov.cn', '国务院AI战略规划和专项扶持政策', 'manual'),
        ext_src('CFPB (美国消费者金融)', 'https://www.consumerfinance.gov', '美国金融监管局，信贷/BNPL/数字支付监管政策', 'pending'),
        ext_src('Federal Reserve Payments', 'https://www.federalreserve.gov/paymentsystems.htm', 'Fed官方：FedNow实时支付轨道进展、美联储CBDC研究报告、支付系统监管立场', 'manual'),
      ]),

    # ─────────────────────────────────────────────────────────────────────
    # 立场维度 7：人工投稿 — 微信公众号 & 内部报告
    # 无法自动抓取的高价值内容通过人工表单录入
    # ─────────────────────────────────────────────────────────────────────
      ('✍️ 人工投稿 · 微信公众号',
       '无公开RSS的微信公众号、付费内容、内部报告通过人工表单录入 — 进入相同的AI评分和收敛分析流程', '#0891b2', [
        ('人工投稿表单 (jd-manual-wechat)', '/jd/paste',
         '团队成员通过网页表单手工提交微信文章/内部报告/会议纪要，AI打分后自动进入简报候选池', 'manual',
         f'<a href="/jd/paste" style="font-size:11px;font-weight:600;color:#0891b2;'
         f'border:1px solid #a5f3fc;padding:2px 8px;border-radius:4px;text-decoration:none;'
         f'background:#ecfeff">✍️ 立即投稿</a>'),
        ext_src('微信公众号：虎嗅AI观察', 'https://mp.weixin.qq.com', '国内消费科技深度报道，电商/物流/AI商业化分析', 'manual'),
        ext_src('微信公众号：晚点LatePost', 'https://mp.weixin.qq.com', '深度调查，已有网页版，建议通过人工表单补录长文', 'manual'),
        ext_src('微信公众号：机器之心Pro', 'https://mp.weixin.qq.com', '付费深度研究，已接入免费版RSS，Pro内容需人工投稿', 'manual'),
        ext_src('微信公众号：京东探索研究院', 'https://mp.weixin.qq.com', '京东内部技术研究，不定期发布，需人工监控', 'manual'),
        ext_src('微信公众号：量子位情报局', 'https://mp.weixin.qq.com', '量子位付费简报，内容早于公开版1-2周', 'paid'),
      ]),

    # ─────────────────────────────────────────────────────────────────────
    # 社交信号 A：X（原Twitter）关键人物
    # 独立于内容评分的第二层信号 — 谁在转发比转发了什么更重要
    # 权重乘数：文章基础分 × (1 + Σ 转发人权重)，上限 2.0×
    # ─────────────────────────────────────────────────────────────────────
      ('𝕏 X（原Twitter）关键人物 · 信号乘数层',
       '22位关键人物账号已接入nitter RSS自动抓取；转发行为作为独立乘数放大被转文章得分（最高2.0×）', '#1a1a2a', [

        # ── 顶尖研究者（学术/工程权威）─────────────────────────────────
        x_src('karpathy',    'Andrej Karpathy',   '前OpenAI/Tesla，深度学习布道者，最广泛引用的AI教育者',      'jd-twitter-karpathy'),
        x_src('ylecun',      'Yann LeCun',         'Meta AI首席科学家，图灵奖得主，CNN发明人',                  'jd-twitter-ylecun'),
        x_src('ilyasut',     'Ilya Sutskever',     'SSI创始人，前OpenAI联合创始人/首席科学家',                  'jd-twitter-ilyasut'),
        x_src('fchollet',    'François Chollet',   'Keras作者，Google DeepMind，ARC-AGI基准提出者',            'jd-twitter-fchollet'),
        x_src('AndrewYNg',   'Andrew Ng',          'DeepLearning.AI/Landing AI创始人，AI普及最大推动者之一',    'jd-twitter-AndrewYNg'),
        x_src('jeffdean',    'Jeff Dean',          'Google DeepMind首席科学家，MapReduce/TensorFlow架构师',     'jd-twitter-jeffdean'),
        x_src('drjimfan',    'Jim Fan',            'NVIDIA Embodied AI负责人，具身智能与机器人前沿',            'jd-twitter-drjimfan'),
        x_src('rasbt',       'Sebastian Raschka',  'Lightning AI首席AI教育官，机器学习工程实践权威',             'jd-twitter-rasbt'),
        x_src('emollick',    'Ethan Mollick',      '宾夕法尼亚大学沃顿商学院教授，AI×商业落地研究',             'jd-twitter-emollick'),
        x_src('GaryMarcus',  'Gary Marcus',        'NYU认知科学教授，AI局限性批评者，LLM可靠性研究',             'jd-twitter-GaryMarcus'),
        x_src('xlr8harder',  'Mihail Eric',        'AI对齐/安全研究员，模型评估与边界研究',                     'jd-twitter-xlr8harder'),

        # ── 实验室领袖（顶尖AI公司CEO/联创）──────────────────────────────
        x_src('sama',         'Sam Altman',         'OpenAI CEO，AGI战略与产品方向最核心的声音',                 'jd-twitter-sama'),
        x_src('darioamodei',  'Dario Amodei',       'Anthropic CEO，AI安全×能力边界核心发声者',                  'jd-twitter-darioamodei'),
        x_src('demishassabis','Demis Hassabis',     'Google DeepMind CEO，AlphaFold/游戏AI/科学发现',           'jd-twitter-demishassabis'),
        x_src('gdb',          'Greg Brockman',      'OpenAI联合创始人，产品与工程战略核心',                      'jd-twitter-gdb'),
        x_src('kaifulee',     '李开复 Kai-Fu Lee',  '零一万物创始人，前Google中国/微软研究院，中美AI桥梁',        'jd-twitter-kaifulee'),

        # ── 资本与生态（VC/投资人/生态建设者）────────────────────────────
        x_src('pmarca',        'Marc Andreessen',   'a16z联合创始人，科技投资最具争议性的意见领袖',               'jd-twitter-pmarca'),
        x_src('sarahguo',      'Sarah Guo',         'Conviction创始人，AI-first VC，最活跃的AI早期投资人之一',   'jd-twitter-sarahguo'),
        x_src('eladgil',       'Elad Gil',          '连续创业者/天使投资人，AI基础设施与平台层判断权威',           'jd-twitter-eladgil'),
        x_src('martin_casado', 'Martin Casado',     'a16z合伙人，基础设施/AI平台，企业软件深度判断',              'jd-twitter-martin_casado'),
        x_src('naval',         'Naval Ravikant',    'AngelList创始人，科技哲学与创业洞察',                       'jd-twitter-naval'),
        x_src('chamath',       'Chamath Palihapitiya','Social Capital创始人，宏观科技趋势与政策批评',             'jd-twitter-chamath'),
      ]),

    # ─────────────────────────────────────────────────────────────────────
    # 社交信号 B：微博科技圈关键人物（规划接入）
    # 中文社交信号的补充 — 国内AI动态、产品泄露、行业内幕的最快传播渠道
    # ─────────────────────────────────────────────────────────────────────
      ('🇨🇳 微博关键人物 · 规划接入',
       '国内科技高管与研究员的微博账号，覆盖中文圈独有信号 — RSSHub提供微博RSS支持，技术上可接入', '#c2410c', [
        weibo_src('liyanhong',    '李彦宏',     '百度CEO，ERNIE Bot/文心一言战略，国内AI商业化最核心声音'),
        weibo_src('wanghaiwen',   '王慧文',     '光年之外创始人，前美团联合创始人，AI创业生态观察'),
        weibo_src('zhouhongyi',   '周鸿祎',     '360创始人，AI安全/大模型应用场景，媒体曝光率极高'),
        weibo_src('zhangpeng',    '张鹏',       '极客公园创始人，一线AI创业者深度采访资源'),
        weibo_src('jiayangqing',  '贾扬清',     'Lepton AI创始人，Caffe作者，前阿里/Meta，工程实践权威'),
        weibo_src('wuyonghao',    '罗永浩',     '交个朋友/前锤子科技，消费电子AI产品风向标'),
        weibo_src('kimi_moonshot','张予彤',     'Moonshot AI (Kimi) 投资方，AI产品与消费落地观察'),
        weibo_src('pengle',       '彭蕾',       '前蚂蚁金服CEO，金融科技政策敏感度'),
      ]),

    ]

    total_planned = sum(len(g[3]) for g in REGISTRY)
    auto_count = sum(1 for g in REGISTRY for s in g[3] if s[3] == 'auto')
    paid_count = sum(1 for g in REGISTRY for s in g[3] if s[3] == 'paid')
    manual_count = sum(1 for g in REGISTRY for s in g[3] if s[3] == 'manual')
    pending_count = sum(1 for g in REGISTRY for s in g[3] if s[3] == 'pending')

    # ── Chart 1: standpoint distribution (deduplicated per group) ─────────
    sp_data = []
    seen_all = set()
    for gname, _desc, gcolor, grp_sources in REGISTRY:
        counts = {'auto': 0, 'manual': 0, 'paid': 0, 'pending': 0}
        seen_in_group = set()
        for label, url, desc, status, _rc in grp_sources:
            key = (label, status)
            if key not in seen_in_group:
                seen_in_group.add(key)
                counts[status] = counts.get(status, 0) + 1
        total_g = sum(counts.values())
        sp_data.append((gname, gcolor, counts['auto'], counts['manual'], counts['paid'], counts['pending'], total_g))

    sp_max = max(d[6] for d in sp_data) if sp_data else 1

    def sp_bar(a, m, p, n, total):
        scale = 100 / sp_max
        wa = a * scale; wm = m * scale; wp = p * scale; wn = n * scale
        segs = ''
        if wa: segs += f'<div style="width:{wa:.1f}%;background:#16a34a;height:100%;display:inline-block;vertical-align:top" title="自动 {a}"></div>'
        if wm: segs += f'<div style="width:{wm:.1f}%;background:#2563eb;height:100%;display:inline-block;vertical-align:top" title="人工 {m}"></div>'
        if wp: segs += f'<div style="width:{wp:.1f}%;background:#d97706;height:100%;display:inline-block;vertical-align:top" title="付费 {p}"></div>'
        if wn: segs += f'<div style="width:{wn:.1f}%;background:#9ca3af;height:100%;display:inline-block;vertical-align:top" title="待接入 {n}"></div>'
        return (f'<div style="width:100%;background:#f3f4f6;border-radius:3px;height:14px;overflow:hidden">'
                f'{segs}</div>')

    sp_rows = ''
    for gname, gcolor, a, m, p, n, total in sp_data:
        short = gname.split(' ', 1)[1] if ' ' in gname else gname
        badge_parts = []
        if a: badge_parts.append(f'<span style="color:#16a34a">{a}</span>')
        if m: badge_parts.append(f'<span style="color:#2563eb">{m}</span>')
        if p: badge_parts.append(f'<span style="color:#d97706">{p}</span>')
        if n: badge_parts.append(f'<span style="color:#9ca3af">{n}</span>')
        badges = ' · '.join(badge_parts)
        sp_rows += f'''
        <div style="display:grid;grid-template-columns:130px 1fr 36px;align-items:center;gap:8px;margin-bottom:6px">
          <div style="font-size:11px;color:#374151;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="{gname}">{short}</div>
          <div>{sp_bar(a,m,p,n,total)}</div>
          <div style="font-size:11px;font-weight:700;color:#111827;text-align:right">{total}</div>
        </div>'''

    # ── Chart 2: business domain distribution from MATRIX_CELLS ──────────
    domain_data = []
    for ri, (row_label, _) in enumerate(MATRIX_ROWS):
        unique_srcs = set()
        for col_cells in MATRIX_CELLS[ri]:
            for s in col_cells[1]:
                unique_srcs.add(s)
        domain_data.append((row_label, len(unique_srcs)))
    domain_data.sort(key=lambda x: -x[1])
    dom_max = max(d[1] for d in domain_data) if domain_data else 1

    # color palette cycling
    dom_colors = ['#6366f1','#0891b2','#059669','#d97706','#dc2626',
                  '#7c3aed','#db2777','#0369a1','#65a30d','#b45309',
                  '#0f766e','#9333ea','#c2410c','#1d4ed8']
    dom_rows = ''
    for i, (dname, cnt) in enumerate(domain_data):
        bar_w = cnt / dom_max * 100
        col = dom_colors[i % len(dom_colors)]
        dom_rows += f'''
        <div style="display:grid;grid-template-columns:110px 1fr 28px;align-items:center;gap:8px;margin-bottom:6px">
          <div style="font-size:11px;color:#374151;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="{dname}">{dname}</div>
          <div style="background:#f3f4f6;border-radius:3px;height:14px;overflow:hidden">
            <div style="width:{bar_w:.1f}%;background:{col};height:100%"></div>
          </div>
          <div style="font-size:11px;font-weight:700;color:#111827;text-align:right">{cnt}</div>
        </div>'''

    # ── Chart 3: status donut (CSS-only arc approximation via conic-gradient) ─
    total_u = auto_count + manual_count + paid_count + pending_count
    if total_u:
        pa = auto_count / total_u * 360
        pm = manual_count / total_u * 360
        pp = paid_count / total_u * 360
        pn = pending_count / total_u * 360
        stop1 = pa
        stop2 = stop1 + pm
        stop3 = stop2 + pp
        donut_grad = (f'conic-gradient(#16a34a 0deg {stop1:.1f}deg,'
                      f'#2563eb {stop1:.1f}deg {stop2:.1f}deg,'
                      f'#d97706 {stop2:.1f}deg {stop3:.1f}deg,'
                      f'#9ca3af {stop3:.1f}deg 360deg)')
    else:
        donut_grad = '#e5e7eb'

    status_legend_html = ''
    for color, label, cnt in [
        ('#16a34a','🟢 自动抓取', auto_count),
        ('#2563eb','🔵 人工监控', manual_count),
        ('#d97706','🟡 付费订阅', paid_count),
        ('#9ca3af','⚪ 待接入',   pending_count),
    ]:
        pct = f'{cnt/total_u*100:.0f}%' if total_u else '0%'
        status_legend_html += f'''
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
          <div style="width:10px;height:10px;border-radius:50%;background:{color};flex-shrink:0"></div>
          <div style="font-size:12px;color:#374151;flex:1">{label}</div>
          <div style="font-size:13px;font-weight:700;color:#111827">{cnt}</div>
          <div style="font-size:11px;color:#9ca3af;width:34px;text-align:right">{pct}</div>
        </div>'''

    charts_html = f'''
  <div style="display:grid;grid-template-columns:1fr 1fr 260px;gap:16px;margin-bottom:24px">

    <!-- Chart 1: By Standpoint -->
    <div style="background:white;border:1px solid #e5e7eb;border-radius:10px;padding:18px 20px">
      <div style="font-size:13px;font-weight:700;color:#111827;margin-bottom:4px">按立场分布</div>
      <div style="font-size:11px;color:#9ca3af;margin-bottom:14px">
        <span style="color:#16a34a">■</span> 自动&nbsp;
        <span style="color:#2563eb">■</span> 人工&nbsp;
        <span style="color:#d97706">■</span> 付费&nbsp;
        <span style="color:#9ca3af">■</span> 待接入
      </div>
      {sp_rows}
    </div>

    <!-- Chart 2: By Business Domain -->
    <div style="background:white;border:1px solid #e5e7eb;border-radius:10px;padding:18px 20px">
      <div style="font-size:13px;font-weight:700;color:#111827;margin-bottom:4px">按业务领域分布</div>
      <div style="font-size:11px;color:#9ca3af;margin-bottom:14px">情报矩阵中各领域覆盖的唯一信源数（跨维度去重）</div>
      {dom_rows}
    </div>

    <!-- Chart 3: Status donut + legend -->
    <div style="background:white;border:1px solid #e5e7eb;border-radius:10px;padding:18px 20px;display:flex;flex-direction:column;align-items:center">
      <div style="font-size:13px;font-weight:700;color:#111827;margin-bottom:14px;align-self:flex-start">接入状态占比</div>
      <div style="width:120px;height:120px;border-radius:50%;background:{donut_grad};
                  margin-bottom:18px;flex-shrink:0;
                  -webkit-mask:radial-gradient(circle, transparent 42px, black 43px);
                  mask:radial-gradient(circle, transparent 42px, black 43px)">
      </div>
      <div style="width:100%">
        {status_legend_html}
      </div>
      <div style="margin-top:8px;padding:8px 12px;background:#f9fafb;border-radius:6px;width:100%;text-align:center">
        <div style="font-size:22px;font-weight:800;color:#111827">{total_u}</div>
        <div style="font-size:10px;color:#9ca3af;margin-top:1px">唯一信源总数</div>
      </div>
    </div>

  </div>'''

    sections_html = []
    for group_label, group_desc, group_color, sources in REGISTRY:
        rows_html = []
        for label, url, desc, status, right_col in sources:
            link = (f'<a href="{url}" target="_blank" style="font-weight:600;font-size:13px;'
                    f'color:#111827;text-decoration:none">{label}</a>' if url else
                    f'<span style="font-weight:600;font-size:13px;color:#111827">{label}</span>')
            rows_html.append(f'''
            <tr style="border-bottom:1px solid #f3f4f6">
              <td style="padding:10px 16px;width:220px;vertical-align:top">{link}</td>
              <td style="padding:10px 16px;font-size:12px;color:#374151;line-height:1.6;vertical-align:top">{desc}</td>
              <td style="padding:10px 16px;text-align:right;white-space:nowrap;vertical-align:middle">{right_col}</td>
            </tr>''')

        sections_html.append(f'''
        <div style="margin:28px 0 10px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap">
          <span style="font-size:15px;font-weight:700;color:{group_color}">{group_label}</span>
          <span style="font-size:12px;color:#6b7280">{group_desc}</span>
        </div>
        <table style="width:100%;border-collapse:collapse;background:white;border-radius:8px;
                      overflow:hidden;border:1px solid #e5e7eb;margin-bottom:4px">
          <thead>
            <tr style="background:#f9fafb;border-bottom:1px solid #e5e7eb">
              <th style="padding:9px 16px;text-align:left;font-size:11px;color:#9ca3af;font-weight:600;text-transform:uppercase;letter-spacing:.5px;width:220px">来源</th>
              <th style="padding:9px 16px;text-align:left;font-size:11px;color:#9ca3af;font-weight:600;text-transform:uppercase;letter-spacing:.5px">覆盖内容</th>
              <th style="padding:9px 16px;text-align:right;font-size:11px;color:#9ca3af;font-weight:600;text-transform:uppercase;letter-spacing:.5px">接入状态</th>
            </tr>
          </thead>
          <tbody>{"".join(rows_html)}</tbody>
        </table>''')

    legend = (STATUS['auto'] + '&nbsp;&nbsp;' + STATUS['paid'] + '&nbsp;&nbsp;' +
              STATUS['manual'] + '&nbsp;&nbsp;' + STATUS['pending'])

    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JD情报 · 情报源全景</title>
<style>
  * {{ box-sizing:border-box }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
          background:#f3f4f6; color:#1a1a2e }}
  .header {{ background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);color:white;padding:20px 32px }}
  .header h1 {{ margin:0 0 4px;font-size:20px;font-weight:700 }}
  .header .meta {{ font-size:12px;opacity:.65 }}
  .nav {{ background:#16213e;padding:0 32px;display:flex;align-items:center }}
  .nav a {{ color:rgba(255,255,255,.65);text-decoration:none;padding:10px 14px;
            font-size:13px;border-bottom:2px solid transparent;display:inline-block }}
  .nav a:hover,.nav a.active {{ color:white;border-bottom-color:#e74c3c }}
  .nav .rss {{ margin-left:auto;font-size:12px;opacity:.5 }}
  .container {{ max-width:1100px;margin:24px auto;padding:0 24px 48px }}
  .kpi-row {{ display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap }}
  .kpi {{ background:white;border:1px solid #e5e7eb;border-radius:8px;padding:14px 20px;
          flex:1;min-width:120px;text-align:center;box-shadow:0 1px 2px rgba(0,0,0,.04) }}
  .kpi .n {{ font-size:26px;font-weight:700;color:#1a1a2e }}
  .kpi .l {{ font-size:11px;color:#9ca3af;margin-top:2px }}
</style>
</head>
<body>
<div class="header">
  <h1>🏪 JD全球前沿情报系统</h1>
  <div class="meta">京东集团CTO部门 · 情报源全景 · Layer 1 原材料收集</div>
</div>
{_jd_nav("sources")}
<div class="container">
  <div class="kpi-row">
    <div class="kpi"><div class="n">{total_planned}</div><div class="l">规划情报源总数</div></div>
    <div class="kpi"><div class="n" style="color:#166534">{auto_count}</div><div class="l">🟢 自动抓取</div></div>
    <div class="kpi"><div class="n" style="color:#92400e">{paid_count}</div><div class="l">🟡 付费订阅</div></div>
    <div class="kpi"><div class="n" style="color:#1e40af">{manual_count}</div><div class="l">🔵 人工监控</div></div>
    <div class="kpi"><div class="n" style="color:#6b7280">{pending_count}</div><div class="l">⚪ 待接入</div></div>
    <div class="kpi"><div class="n">{total_articles}</div><div class="l">已抓取文章</div></div>
    <div class="kpi"><div class="n">{total_high}</div><div class="l">高分情报 ≥70分</div></div>
  </div>
  {charts_html}
  <div style="margin-bottom:20px;padding:10px 16px;background:white;border:1px solid #e5e7eb;
              border-radius:8px;font-size:12px;color:#374151;display:flex;align-items:center;gap:16px;flex-wrap:wrap">
    <strong>图例：</strong>{legend}
  </div>
  {"".join(sections_html)}
  <div style="margin-top:28px;padding:14px 16px;background:#f0fdf4;border:1px solid #bbf7d0;
              border-radius:8px;font-size:12px;color:#166534;line-height:1.7">
    <strong>📐 评分说明：</strong>
    自动抓取源通过 DeepSeek AI 按四维模型打分 — 京东业务相关性(40分) · 来源层级(25分) · 新鲜度(25分) · 信号收敛(10分)。
    评分≥55分进入简报候选池。付费/人工/待接入源为 Layer 1 扩展计划，Layer 2（信号关联）和 Layer 3（战略合成）将在后续建设。
  </div>

  <!-- ── 情报矩阵 embedded ── -->
  <div style="margin-top:36px">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;
                padding-bottom:10px;border-bottom:2px solid #e5e7eb">
      <span style="font-size:22px">🗺</span>
      <div>
        <div style="font-size:15px;font-weight:700;color:#1a1a2e">情报矩阵</div>
        <div style="font-size:11px;color:#9ca3af">近30天 · 评分≥55 · 8大业务域 × 5个团队能力方向</div>
      </div>
      <a href="/jd/_matrix" target="_blank"
         style="margin-left:auto;font-size:11px;color:#2563eb;text-decoration:none;
                background:#eff6ff;border:1px solid #bfdbfe;padding:4px 10px;border-radius:6px">
        全屏查看 ↗</a>
    </div>
    <div style="overflow-x:auto">
      {matrix_section_html}
    </div>
  </div>
</div>
</body>
</html>'''


@app.route('/jd/buzz')
def jd_buzz():
    import re as _re
    from urllib.parse import urlparse as _up
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Skip-list: redirect/shortener domains that tell us nothing
    _BAD_DOMAINS = {'bitly.com', 'ebx.sh', 't.co', 'buff.ly', 'ow.ly', 'bit.ly',
                    'dlvr.it', 'ift.tt', 'tinyurl.com', 'feedproxy.google.com'}

    def _clean_url(url):
        if not url or len(url) < 15:
            return None
        if any(c in url for c in ('"', '<', '>', '%22')):
            return None
        u = url.split('#')[0].rstrip('/')
        try:
            dom = _up(u).netloc.lower().replace('www.', '')
        except Exception:
            return None
        if dom in _BAD_DOMAINS:
            return None
        return u

    def _tweet_text(raw_content):
        """Strip HTML from tweet raw_content → clean readable text."""
        text = _re.sub(r'<[^>]+>', ' ', raw_content or '')
        text = _re.sub(r'&amp;', '&', text)
        text = _re.sub(r'&lt;', '<', text)
        text = _re.sub(r'&gt;', '>', text)
        text = _re.sub(r'\s+', ' ', text).strip()
        return text

    # ── 1. KOL推荐阅读 — top external links shared by high-weight KOLs ──────
    # Deduplicate by (handle, clean_url) so one tweet doesn't spawn N cards
    xe_rows = conn.execute("""
        SELECT xe.linked_url, xe.endorser_handle, xe.endorser_weight, xe.tweet_date,
               a.article_title as tweet_title, a.raw_content as tweet_raw
        FROM x_endorsements xe
        JOIN articles a ON xe.tweet_article_id = a.id
        WHERE xe.linked_url IS NOT NULL
        ORDER BY xe.endorser_weight DESC, xe.tweet_date DESC
    """).fetchall()

    seen_handle_url = set()
    kol_links = []          # list of dicts, one per unique (handle, url)
    for r in xe_rows:
        url = _clean_url(r['linked_url'])
        if not url:
            continue
        key = (r['endorser_handle'], url)
        if key in seen_handle_url:
            continue
        seen_handle_url.add(key)
        tweet_text = _tweet_text(r['tweet_raw'])
        # Strip "RT by @handle:" prefix for cleaner display
        display_text = tweet_text
        if display_text.startswith('RT by @') or display_text.startswith('R to @'):
            colon = display_text.find(': ')
            if colon > 0:
                display_text = display_text[colon+2:]
        # Skip if tweet text is too short to be useful (just a URL share with no commentary)
        try:
            dom = _up(url).netloc.replace('www.', '')
        except Exception:
            dom = url[:40]
        kol_links.append({
            'url': url, 'domain': dom,
            'handle': r['endorser_handle'],
            'weight': r['endorser_weight'],
            'date': r['tweet_date'],
            'tweet_title': r['tweet_title'] or '',
            'summary': display_text,
        })
        if len(kol_links) >= 30:
            break

    # ── 2. HN posts ranked by Points ─────────────────────────────────────
    hn_all = conn.execute("""
        SELECT article_title, article_link, published_date, raw_content, criteria_score
        FROM articles
        WHERE feed_name = 'jd-hackernews'
          AND raw_content IS NOT NULL
          AND published_date >= date('now', '-30 days')
        ORDER BY published_date DESC
        LIMIT 200
    """).fetchall()

    def _parse_points(rc):
        m = _re.search(r'Points:\s*(\d+)', rc or '')
        return int(m.group(1)) if m else 0

    def _parse_comments(rc):
        m = _re.search(r'#\s*Comments:\s*(\d+)', rc or '')
        return int(m.group(1)) if m else 0

    def _hn_comments_url(rc):
        m = _re.search(r'Comments URL.*?href="([^"]+)"', rc or '')
        return m.group(1) if m else ''

    def _hn_summary(rc):
        """Extract article body text from HN raw_content (Show HN posts often have it)."""
        text = _re.sub(r'<[^>]+>', ' ', rc or '')
        text = _re.sub(r'\s+', ' ', text).strip()
        # Skip boilerplate: remove "Article URL: ..." and "Comments URL: ..." lines
        text = _re.sub(r'Article URL:\s*\S+', '', text)
        text = _re.sub(r'Comments URL:\s*\S+', '', text)
        text = _re.sub(r'Points:\s*\d+', '', text)
        text = _re.sub(r'#\s*Comments:\s*\d+', '', text)
        text = _re.sub(r'\s+', ' ', text).strip()
        return text if len(text) > 40 else ''

    hn_scored = []
    for r in hn_all:
        pts = _parse_points(r['raw_content'])
        cmts = _parse_comments(r['raw_content'])
        if pts > 0 or cmts > 0:
            hn_scored.append({'title': r['article_title'], 'link': r['article_link'],
                              'pub': r['published_date'], 'points': pts, 'comments': cmts,
                              'comments_url': _hn_comments_url(r['raw_content']),
                              'summary': _hn_summary(r['raw_content']),
                              'ai_score': r['criteria_score']})
    hn_scored.sort(key=lambda x: -x['points'])
    hn_top = hn_scored[:20]

    # ── 3. KOL individual posts (grouped by person, weight-sorted) ────────
    kol_rows = conn.execute("""
        SELECT feed_name, article_title, article_link, published_date, raw_content
        FROM articles
        WHERE feed_name LIKE 'jd-twitter%'
          AND published_date >= date('now', '-14 days')
        ORDER BY feed_priority ASC, published_date DESC
    """).fetchall()
    conn.close()

    kol_posts = {}
    for r in kol_rows:
        fn = r['feed_name']
        if fn not in TWITTER_PERSON_MAP:
            continue
        if fn not in kol_posts:
            kol_posts[fn] = []
        if len(kol_posts[fn]) < 5:
            kol_posts[fn].append(dict(r))

    kol_order = sorted(kol_posts.keys(),
                       key=lambda fn: -X_ENDORSER_WEIGHTS.get(
                           fn.replace('jd-twitter-', ''), 0))

    # ── 4. Community feeds (thread platforms) ────────────────────────────
    community_sections_html = ''
    conn2 = sqlite3.connect(DB_PATH)
    conn2.row_factory = sqlite3.Row
    for cfn, (clabel, caccent, cbg, cborder) in _COMMUNITY_FEEDS.items():
        if cfn in ('jd-lobsters-ai', 'jd-hn-showhn', 'jd-hackernews'):
            continue  # HN shown separately
        # Sort by engagement for engagement-sorted feeds, else by score
        if cfn in _ENGAGEMENT_SORT_FEEDS:
            order_col = 'CAST(raw_content AS TEXT)'  # parse at Python level
            rows = conn2.execute("""
                SELECT article_title, article_link, published_date,
                       raw_content, criteria_score, criteria_reason
                FROM articles
                WHERE feed_name = ?
                  AND published_date >= date('now', '-30 days')
                ORDER BY published_date DESC
                LIMIT 50
            """, (cfn,)).fetchall()
            citems = [dict(r) for r in rows]
            citems.sort(key=lambda x: -_parse_reply_count(x.get('raw_content', '') or ''))
        else:
            rows = conn2.execute("""
                SELECT article_title, article_link, published_date,
                       raw_content, criteria_score, criteria_reason
                FROM articles
                WHERE feed_name = ?
                  AND criteria_score IS NOT NULL
                  AND published_date >= date('now', '-30 days')
                ORDER BY criteria_score DESC
                LIMIT 15
            """, (cfn,)).fetchall()
            citems = [dict(r) for r in rows]
        if citems:
            community_sections_html += _community_feed_section(
                cfn, citems, clabel, caccent, cbg, cborder
            )
    conn2.close()

    # ── Build HTML ────────────────────────────────────────────────────────

    # KOL推荐阅读 cards
    kol_links_html = ''
    for item in kol_links[:15]:
        handle = item['handle']
        fn = f'jd-twitter-{handle}'
        name, emoji, role = TWITTER_PERSON_MAP.get(fn, (f'@{handle}', '👤', ''))
        weight = item['weight']
        w_color = '#b45309' if weight >= 0.25 else '#1d4ed8' if weight >= 0.18 else '#6b7280'
        summary = item['summary']
        summary_s = summary[:280] + '…' if len(summary) > 280 else summary
        pub = _parse_pub_date(item['date']).strftime('%-m/%-d')
        domain = item['domain']
        url = item['url']
        kol_links_html += (
            f'<div style="background:white;border:1px solid #e5e7eb;border-left:4px solid {w_color};'
            f'border-radius:8px;padding:12px 14px;margin-bottom:10px">'
            # KOL byline
            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">'
            f'<span style="font-size:15px">{emoji}</span>'
            f'<span style="font-size:12px;font-weight:700;color:#111827">{name}</span>'
            f'<span style="font-size:10px;color:{w_color};font-weight:600">×{weight:.2f}</span>'
            f'<span style="font-size:10px;color:#9ca3af;margin-left:auto">{pub}</span>'
            f'</div>'
            # Their commentary = summary
            f'<div style="font-size:12px;color:#374151;line-height:1.7;margin-bottom:10px;'
            f'background:#f9fafb;border-radius:6px;padding:8px 10px">{summary_s}</div>'
            # Link
            f'<a href="{url}" target="_blank" style="font-size:11px;color:#2563eb;'
            f'text-decoration:none;display:flex;align-items:center;gap:4px">'
            f'<span style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:4px;'
            f'padding:2px 6px;font-size:10px;font-weight:600;color:#1d4ed8">{domain}</span>'
            f'<span style="color:#9ca3af">↗ 阅读原文</span></a>'
            f'</div>'
        )
    if not kol_links_html:
        kol_links_html = '<div style="color:#9ca3af;font-size:12px;padding:16px">暂无KOL外链推荐数据</div>'

    # KOL动态 cards (grouped by person)
    def _kol_post_html(p):
        raw = p['article_title'] or ''
        is_rt = raw.startswith('RT by @') or raw.startswith('R to @')
        text = raw[raw.find(': ')+2:] if (is_rt and ': ' in raw[:40]) else raw
        # Also use raw_content for fuller text
        full = _tweet_text(p.get('raw_content', '') or '')
        display = full if len(full) > len(text) else text
        display_s = display[:200] + '…' if len(display) > 200 else display
        pub = _parse_pub_date(p['published_date']).strftime('%-m/%-d')
        rt_tag = ('<span style="font-size:9px;background:#f3f4f6;color:#9ca3af;'
                  'border-radius:3px;padding:0 4px;margin-right:4px">RT</span>') if is_rt else ''
        return (f'<div style="padding:8px 0;border-top:1px solid #f3f4f6">'
                f'<div style="font-size:11px;color:#374151;line-height:1.6;margin-bottom:3px">'
                f'{rt_tag}{display_s}</div>'
                f'<a href="{p["article_link"]}" target="_blank" '
                f'style="font-size:10px;color:#9ca3af;text-decoration:none">原文 ↗</a>'
                f'<span style="font-size:9px;color:#d1d5db;margin-left:8px">{pub}</span>'
                f'</div>')

    kol_cards_html = ''
    for fn in kol_order:
        if not kol_posts.get(fn):
            continue
        name, emoji, role = TWITTER_PERSON_MAP[fn]
        handle = fn.replace('jd-twitter-', '')
        weight = X_ENDORSER_WEIGHTS.get(handle, 0)
        w_color = '#b45309' if weight >= 0.25 else '#1d4ed8' if weight >= 0.18 else '#6b7280'
        posts_html = ''.join(_kol_post_html(p) for p in kol_posts[fn])
        kol_cards_html += (
            f'<div style="background:white;border:1px solid #e5e7eb;border-radius:8px;'
            f'padding:12px 14px;margin-bottom:10px">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;'
            f'padding-bottom:6px;border-bottom:1px solid #f3f4f6">'
            f'<span style="font-size:18px">{emoji}</span>'
            f'<div style="flex:1">'
            f'<div style="font-size:12px;font-weight:700;color:#111827">{name}</div>'
            f'<div style="font-size:10px;color:#9ca3af">{role}'
            f' · <span style="color:{w_color};font-weight:600">权重×{weight:.2f}</span></div>'
            f'</div></div>'
            f'{posts_html}</div>'
        )

    # HN cards
    hn_html = ''
    for item in hn_top:
        pts = item['points']
        cmts = item['comments']
        pub = _parse_pub_date(item['pub']).strftime('%-m/%-d')
        heat = min(100, pts // 3)
        heat_color = '#dc2626' if pts >= 200 else '#d97706' if pts >= 80 else '#6b7280'
        cmt_url = item['comments_url'] or item['link']
        summary = item['summary']
        summary_html = (f'<div style="font-size:11px;color:#6b7280;line-height:1.6;margin-top:4px;'
                        f'background:#f9fafb;border-radius:4px;padding:6px 8px">'
                        f'{summary[:240]}{"…" if len(summary)>240 else ""}</div>') if summary else ''
        hn_html += (
            f'<div style="padding:10px 0;border-top:1px solid #f3f4f6;'
            f'display:flex;gap:10px;align-items:flex-start">'
            f'<div style="flex-shrink:0;width:44px;text-align:center">'
            f'<div style="font-size:14px;font-weight:700;color:{heat_color}">{pts}</div>'
            f'<div style="font-size:9px;color:#9ca3af">pts</div>'
            f'<div style="height:3px;width:100%;background:#f3f4f6;border-radius:2px;margin-top:2px">'
            f'<div style="height:100%;width:{heat}%;background:{heat_color};border-radius:2px"></div></div>'
            f'</div>'
            f'<div style="flex:1;min-width:0">'
            f'<a href="{item["link"]}" target="_blank" style="font-size:12px;font-weight:600;'
            f'color:#111827;text-decoration:none;line-height:1.5;display:block">{item["title"]}</a>'
            f'{summary_html}'
            f'<div style="font-size:10px;color:#9ca3af;margin-top:4px">'
            f'{pub} · <a href="{cmt_url}" target="_blank" style="color:#9ca3af;text-decoration:none">'
            f'💬 {cmts}条评论</a></div>'
            f'</div></div>'
        )
    if not hn_html:
        hn_html = '<div style="color:#9ca3af;font-size:12px;padding:16px">近30天无HN热帖数据</div>'

    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JD社区热议</title>
<style>
  * {{ box-sizing:border-box }}
  body {{ margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
          background:#f3f4f6;color:#1a1a2e }}
  .header {{ background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;padding:20px 32px }}
  .header h1 {{ margin:0 0 4px;font-size:20px;font-weight:700 }}
  .header .meta {{ font-size:12px;opacity:.65 }}
  .nav {{ background:#16213e;padding:0 32px;display:flex;align-items:center }}
  .nav a {{ color:rgba(255,255,255,.65);text-decoration:none;padding:10px 14px;
            font-size:13px;border-bottom:2px solid transparent;display:inline-block }}
  .nav a:hover,.nav a.active {{ color:white;border-bottom-color:#e74c3c }}
  .wrap {{ max-width:1100px;margin:24px auto;padding:0 20px }}
  .two-col {{ display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:start }}
  @media(max-width:800px) {{ .two-col {{ grid-template-columns:1fr }} }}
</style>
</head>
<body>
<div class="header">
  <h1>🔥 社区热议</h1>
  <div class="meta">基于人类热度信号 · 点赞 / 转发 / 评论 · 非AI判断</div>
</div>
{_jd_nav("buzz")}
<div class="wrap">
  <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:12px 16px;
              margin-bottom:24px;font-size:12px;color:#92400e;line-height:1.7">
    <strong>📌 排名逻辑</strong> — 本页内容完全基于人类行为信号，不依赖AI评分。
    HN热帖按真实点赞数(Points)降序 · KOL推荐阅读按发布者影响力权重排序，附其原话作为摘要 · KOL近期动态按权重+时效排序。
  </div>

  <!-- ── KOL推荐阅读 ── -->
  <div style="margin-bottom:32px">
    <div style="font-size:15px;font-weight:700;color:#1a1a2e;margin-bottom:4px">🔗 KOL推荐阅读</div>
    <div style="font-size:11px;color:#9ca3af;margin-bottom:12px">
      顶级意见领袖主动分享的外链 · 其原话即摘要 · 按影响力权重排序
    </div>
    {kol_links_html}
  </div>

  <!-- ── 社区热议各平台 ── -->
  <div style="margin-bottom:32px">
    <div style="font-size:15px;font-weight:700;color:#1a1a2e;margin-bottom:4px">🌐 社区热议各平台</div>
    <div style="font-size:11px;color:#9ca3af;margin-bottom:12px">
      线上讨论社区 · Reddit / HF / V2EX / 掘金 / 少数派 / Linux.do · 按热度或AI评分排序
    </div>
    {community_sections_html}
  </div>

  <div class="two-col">
    <!-- ── HN热帖 ── -->
    <div>
      <div style="font-size:15px;font-weight:700;color:#1a1a2e;margin-bottom:4px">📊 Hacker News热帖</div>
      <div style="font-size:11px;color:#9ca3af;margin-bottom:12px">按点赞数(Points)降序 · 近30天 · 含正文摘要</div>
      <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:12px 16px">
        {hn_html}
      </div>
    </div>

    <!-- ── KOL近期动态 ── -->
    <div>
      <div style="font-size:15px;font-weight:700;color:#1a1a2e;margin-bottom:4px">💬 KOL近期动态</div>
      <div style="font-size:11px;color:#9ca3af;margin-bottom:12px">按影响力权重排序 · 近14天 · 含完整推文</div>
      {kol_cards_html or '<div style="color:#9ca3af;font-size:12px;padding:16px">无KOL动态</div>'}
    </div>
  </div>
</div>
</body>
</html>'''


@app.route('/jd/step2')
def jd_step2():
    html_path = os.path.join(os.path.dirname(__file__), 'workflow_step2_detail.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        return Response(f.read(), mimetype='text/html')


# ═══════════════════════════════════════════════════════════════════════════
#  产业共识 — Industry Consensus Intelligence (刘强东10节甘蔗)
# ═══════════════════════════════════════════════════════════════════════════

# Import the 10-segment definition from retail_convergence.py at runtime
def _load_ganmie():
    try:
        import importlib.util, os as _os
        spec = importlib.util.spec_from_file_location(
            'retail_convergence',
            _os.path.join(_os.path.dirname(__file__), 'retail_convergence.py')
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.GANMIE_SEGMENTS
    except Exception:
        return []

GANMIE_SEGMENTS_RT = _load_ganmie()  # list of (key, label, emoji, desc, feeds, kw)

# Feeds that directly cover the retail value chain or competitor moves
RETAIL_CHAIN_FEEDS = {
    # Competitor official tech/engineering blogs
    'jd-amazon-science', 'jd-walmart-tech', 'jd-alizila',
    'jd-shopify', 'jd-shopee-blog', 'jd-meituan-tech',
    'jd-grab-engineering', 'jd-instacart-tech',
    # Retail industry media
    'jd-modern-retail', 'jd-retail-dive', 'jd-digital-commerce', 'jd-practical-ecom',
    # Supply chain & logistics
    'jd-supply-chain-dive', 'jd-dc-velocity', 'jd-logistics-viewpoints',
    'jd-freightwaves', 'jd-loadstar', 'jd-supplychainbrain',
    # Warehouse automation & embodied AI
    'jd-the-robot-report', 'jd-ieee-spectrum-robotics',
    # Chinese retail / ecommerce media
    'jd-36kr', 'jd-36kr-ai', 'jd-36kr-funding', 'jd-36kr-global',
    'jd-ebrun', 'jd-latepost', 'jd-huxiu', 'jd-yicai',
    # Chinese tech media (editorial, not community)
    'jd-geekpark', 'jd-ifanr', 'jd-ruanyifeng',
    # Global / cross-border retail coverage
    'jd-krasia', 'jd-pandaily', 'jd-scmp-tech', 'jd-techinasia', 'jd-restofworld',
    # Recommendation / search research (direct product relevance)
    'jd-arxiv-ir', 'jd-eugeneyan',
    # Earnings / investor relations
    'jd-ir-jd', 'jd-ir-pdd', 'jd-ir-alibaba',
    # Marketing & ad-tech (customer acquisition layer of retail)
    'jd-adexchanger', 'jd-digiday',
    # Payment / fintech (checkout & credit in retail)
    'jd-finextra', 'jd-pymnts', 'jd-stripe-blog', 'jd-payments-dive',
    'jd-digital-transactions',
    # General tech media when they cover retail-adjacent topics
    'jd-techcrunch-ai', 'jd-venturebeat-ai', 'jd-bloomberg-tech',
    'jd-mit-tech-review', 'jd-36kr-global',
    # Manual submissions tagged as retail
    'jd-manual-report', 'jd-manual-wechat',
}

# Domain labels (from FEED_DOMAIN_MAP) that qualify as retail value chain
RETAIL_CHAIN_DOMAINS = {
    '智能零售', '物流与供应链', '交易服务平台', '广告营销',
    '金融与支付', '具身智能与机器人', '跨语言与全球化',
    '消费电子与智能硬件',  # hardware driving retail (AR/VR, smart devices)
}

# Sub-sector grouping for display
RETAIL_SECTORS = [
    ('零售产品与技术',       '🛒', '#2563eb',
     '商品发现 · 推荐系统 · 个性化 · 搜索 · 转化优化 · 竞品产品迭代',
     {'智能零售', '交易服务平台'}),
    ('供应链、物流与配送',   '📦', '#7c3aed',
     '供应链管理 · 仓储自动化 · 末端配送 · 即时配送 · 逆向物流 · 具身智能机器人',
     {'物流与供应链', '具身智能与机器人'}),
    ('营销与用户增长',       '📣', '#d97706',
     '广告技术 · 内容营销 · 用户获取 · CRM · 会员体系 · 创意生成',
     {'广告营销'}),
    ('支付与金融科技',       '💳', '#0891b2',
     '支付通道 · 先买后付 · 信贷 · 风控 · 数字钱包',
     {'金融与支付'}),
    ('全球化与跨境',         '🌏', '#dc2626',
     '跨境电商 · 海外市场进展 · 本地化 · 全球供应链动态',
     {'跨语言与全球化'}),
]


def render_jd_retail(ganmie_clusters, ganmie_articles, total_clusters, days=60,
                     buzz_twitter=None, hn_rows=None):
    """Render the retail competitor page using 10节甘蔗 segments + convergence clusters."""

    GANMIE_COLORS = [
        '#6366f1','#7c3aed','#2563eb','#0891b2',
        '#059669','#d97706','#dc2626','#be185d','#0f766e','#1d4ed8',
    ]

    def score_color(s):
        if s is None: return '#9ca3af'
        if s >= 75:   return '#dc2626'
        if s >= 55:   return '#d97706'
        return '#6b7280'

    def score_bar_sm(s):
        if s is None: return ''
        pct = min(100, int(s))
        color = score_color(s)
        return (f'<div style="width:40px">'
                f'<div style="font-size:13px;font-weight:700;color:{color};text-align:center">{int(s)}</div>'
                f'<div style="height:3px;background:#f3f4f6;border-radius:2px;margin-top:2px">'
                f'<div style="height:100%;width:{pct}%;background:{color};border-radius:2px"></div></div>'
                f'</div>')

    def sp_pill(sp):
        colors = {
            '关键玩家': ('#f5f3ff','#7c3aed','#ddd6fe'),
            '资本动向':  ('#f0fdf4','#059669','#bbf7d0'),
            '顶尖研究者':('#fff7ed','#d97706','#fed7aa'),
            '行业媒体':  ('#f0f9ff','#0891b2','#bae6fd'),
            '科技媒体':  ('#eff6ff','#2563eb','#bfdbfe'),
            '技术社区':  ('#f5f3ff','#6366f1','#ddd6fe'),
            '政策与专利':('#fef2f2','#dc2626','#fecaca'),
        }
        if not sp: return ''
        bg, fg, bd = colors.get(sp, ('#f3f4f6','#6b7280','#e5e7eb'))
        return (f'<span style="font-size:9px;background:{bg};color:{fg};border:1px solid {bd};'
                f'padding:1px 6px;border-radius:5px;font-weight:500">{sp}</span>')

    # Scope → baseline keyword set for community signal matching
    SCOPE_KEYWORDS = {
        'search_content': ['recommendation', 'search', 'retrieval', 'ranking', 'personali', 'ux', 'content'],
        'advertising':    ['advertis', 'marketing', 'campaign', 'crm', 'audience', 'brand'],
        'smart_retail':   ['retail', 'ecommerc', 'shopping', 'merchant', 'pricing', 'marketplace', 'platform'],
        'finance':        ['payment', 'checkout', 'fintech', 'bnpl', 'fraud', 'wallet', '支付'],
        'logistics':      ['logistic', 'warehouse', 'delivery', 'supply chain', 'shipping', 'fulfillment', '物流'],
        'robotics':       ['robot', 'humanoid', 'embodied', 'autonomous', 'dexterous', '机器人'],
        'hardware':       ['chip', 'hardware', 'iot', 'semiconductor', 'device', 'electronic'],
        'ai_infra':       ['llm', 'model', 'inference', 'agent', 'training', 'vibe', 'safety',
                           'foundation', 'open.?source', 'reasoning', 'benchmark'],
    }

    def _match_buzz(cl, buzz_posts):
        """Return up to 2 community posts that best match this cluster."""
        import re as _re
        scope = cl['scope'] if 'scope' in cl.keys() else ''
        theme = (cl['theme_label'] or '').lower()
        why   = (cl['why_convergent'] or '').lower()
        combined = theme + ' ' + why

        # Build keyword list: scope base + specific nouns from theme_label
        kws = list(SCOPE_KEYWORDS.get(scope, []))
        for w in _re.findall(r'[A-Za-z]{4,}', cl['theme_label'] or ''):
            kws.append(w.lower())
        for w in _re.findall(r'[一-鿿]{2,4}', cl['theme_label'] or ''):
            if w not in ('的与和是在了等对于从'):
                kws.append(w)

        scored = []
        for post in buzz_posts:
            text = (post['article_title'] or '').lower()
            hits = sum(1 for kw in kws if _re.search(kw, text))
            if hits:
                scored.append((hits, post))
        scored.sort(key=lambda x: -x[0])
        return [dict(p) for _, p in scored[:2]]

    def cluster_card(cl, seg_color, community_signals=None):
        score   = cl['convergence_score'] or 0
        theme   = cl['theme_label'] or ''
        why     = cl['why_convergent'] or ''
        synth   = cl['synthesis_text'] or ''
        sq      = cl['strategic_question'] or ''
        action  = cl['recommended_action'] or ''
        feeds   = json.loads(cl['article_feed_names'] or '[]')
        titles  = json.loads(cl['article_titles'] or '[]')
        links   = json.loads(cl['article_links'] or '[]')
        scores  = json.loads(cl['article_scores'] or '[]')
        sps     = json.loads(cl['standpoints'] or '[]')

        try:
            ad = json.loads(cl['action_data'] or '{}')
        except Exception:
            ad = {}

        shipped     = ad.get('shipped_product', '')
        v_exp       = ad.get('value_experience', '')
        v_cost      = ad.get('value_cost', '')
        v_eff       = ad.get('value_efficiency', '')
        maturity    = ad.get('maturity', '')
        leader_n    = ad.get('leader_names', '')
        leader_t    = ad.get('leader_type', '')
        reaction    = ad.get('reaction', '')
        teams       = ad.get('lean_in_teams', '')

        # maturity badge
        maturity_cfg = {
            'early':   ('早期探索', '#f0fdf4', '#059669', '#bbf7d0'),
            'growing': ('快速扩张', '#fff7ed', '#d97706', '#fed7aa'),
            'mature':  ('成熟落地', '#eff6ff', '#2563eb', '#bfdbfe'),
        }
        mc = maturity_cfg.get(maturity, (maturity or '—', '#f3f4f6', '#6b7280', '#e5e7eb'))
        maturity_html = (f'<span style="font-size:9px;font-weight:600;background:{mc[1]};'
                         f'color:{mc[2]};border:1px solid {mc[3]};padding:2px 7px;'
                         f'border-radius:5px">{mc[0]}</span>')

        # leader type badge
        lt_cfg = {
            'competitor': ('竞对', '#fef2f2', '#dc2626', '#fecaca'),
            'partner':    ('潜在合作', '#f0fdf4', '#059669', '#bbf7d0'),
            'neutral':    ('中立研究', '#f5f3ff', '#7c3aed', '#ddd6fe'),
            'mixed':      ('竞合混合', '#fff7ed', '#d97706', '#fed7aa'),
        }
        ltc = lt_cfg.get(leader_t, ('', '#f3f4f6', '#6b7280', '#e5e7eb'))
        leader_html = ''
        if leader_n:
            lt_badge = (f'<span style="font-size:9px;font-weight:600;background:{ltc[1]};'
                        f'color:{ltc[2]};border:1px solid {ltc[3]};padding:2px 7px;border-radius:5px">'
                        f'{ltc[0]}</span>') if ltc[0] else ''
            leader_html = (f'<div style="font-size:11px;color:#374151;margin-top:4px">'
                           f'<strong style="color:#6b7280">领跑：</strong>{leader_n} {lt_badge}</div>')

        # reaction badge
        rx_cfg = {
            'ignore':  ('忽略', '#f3f4f6', '#6b7280', '⬜'),
            'monitor': ('持续跟踪', '#fffbeb', '#92400e', '👁'),
            'act':     ('立即行动', '#fef2f2', '#dc2626', '🔴'),
        }
        rxc = rx_cfg.get(reaction, ('—', '#f3f4f6', '#6b7280', ''))
        reaction_html = (f'<span style="font-size:11px;font-weight:700;color:{rxc[2]}">'
                         f'{rxc[3]} 建议态度：{rxc[0]}</span>') if reaction else ''
        teams_html = (f'<span style="font-size:11px;color:#374151;margin-left:12px">'
                      f'<strong style="color:#6b7280">介入团队：</strong>{teams}</span>') if teams else ''

        # value triptych — only render if any value field present
        value_html = ''
        if v_exp or v_cost or v_eff:
            def _vbox(label, text, color):
                return (f'<div style="flex:1;min-width:0;background:{color}08;border:1px solid {color}20;'
                        f'border-radius:6px;padding:8px 10px">'
                        f'<div style="font-size:9px;font-weight:700;color:{color};margin-bottom:4px;letter-spacing:.5px">{label}</div>'
                        f'<div style="font-size:11px;color:#374151;line-height:1.5">{text or "—"}</div>'
                        f'</div>')
            value_html = (f'<div style="display:flex;gap:8px;margin:10px 0">'
                          + _vbox('体验', v_exp, '#2563eb')
                          + _vbox('成本', v_cost, '#059669')
                          + _vbox('效率', v_eff, '#d97706')
                          + '</div>')

        sources_html = ''
        for f, t, lk, sc in zip(feeds, titles, links, scores):
            lbl = JD_SOURCE_MAP.get(f, {}).get('label', f)
            sp  = STANDPOINT_MAP.get(f, '')
            sources_html += (
                f'<div style="display:flex;align-items:flex-start;gap:8px;'
                f'padding:6px 0;border-top:1px solid #f3f4f6">'
                f'<span style="font-size:10px;font-weight:700;color:{score_color(sc)};'
                f'flex-shrink:0;min-width:26px">{int(sc)}</span>'
                f'<div style="flex:1;min-width:0">'
                f'<a href="{lk}" target="_blank" style="font-size:11px;font-weight:600;'
                f'color:#111827;text-decoration:none;line-height:1.4;display:block">{t}</a>'
                f'<span style="font-size:9px;color:#9ca3af">{lbl}</span> '
                f'{sp_pill(sp)}'
                f'</div></div>'
            )

        sps_html = ' '.join(sp_pill(s) for s in sps if s)

        shipped_html = ''
        if shipped and shipped != '尚未商业化':
            shipped_html = (f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;'
                            f'padding:8px 12px;margin-bottom:8px">'
                            f'<span style="font-size:9px;font-weight:700;color:#059669;letter-spacing:.5px">📦 已落地产品/技术</span>'
                            f'<div style="font-size:12px;color:#1a1a2e;margin-top:3px;font-weight:500">{shipped}</div>'
                            f'</div>')
        elif shipped == '尚未商业化':
            shipped_html = (f'<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;'
                            f'padding:6px 12px;margin-bottom:8px;font-size:11px;color:#9ca3af">'
                            f'🔬 尚未商业化落地</div>')

        # Community signals block
        buzz_block = ''
        if community_signals:
            buzz_items = ''
            for post in community_signals:
                fn = post.get('feed_name', '')
                raw = post.get('article_title', '') or ''
                is_rt = raw.startswith('RT by @') or raw.startswith('R to @')
                text = raw[raw.find(': ')+2:] if ': ' in raw[:30] else raw
                text_short = text[:140] + '…' if len(text) > 140 else text
                pub = _parse_pub_date(post.get('published_date', '')).strftime('%-m/%-d')
                link = post.get('article_link', '#') or '#'
                if fn in TWITTER_PERSON_MAP:
                    pname, emoji, _ = TWITTER_PERSON_MAP[fn]
                    src_label = f'{emoji} {pname}'
                elif fn == 'jd-hackernews':
                    src_label = '🔗 HN'
                else:
                    src_label = fn
                rt_tag = ('<span style="font-size:8px;background:#f3f4f6;color:#9ca3af;'
                          'border-radius:3px;padding:0 3px;margin-right:3px">转</span>') if is_rt else ''
                buzz_items += (
                    f'<div style="padding:5px 0;border-top:1px solid #fde68a;'
                    f'display:flex;gap:8px;align-items:flex-start">'
                    f'<span style="font-size:10px;color:#d97706;font-weight:600;'
                    f'flex-shrink:0;white-space:nowrap">{src_label}</span>'
                    f'<div style="font-size:10px;color:#78350f;line-height:1.5;flex:1">'
                    f'{rt_tag}'
                    f'<a href="{link}" target="_blank" style="color:#78350f;text-decoration:none">{text_short}</a>'
                    f'<span style="color:#d1d5db;margin-left:4px">{pub}</span>'
                    f'</div></div>'
                )
            fire = '🔥 ' * min(len(community_signals), 2)
            buzz_block = (
                f'<div style="padding:8px 16px;background:#fffbeb;border-top:1px solid #fde68a">'
                f'<div style="font-size:10px;font-weight:700;color:#d97706;margin-bottom:4px">'
                f'{fire}社区热议印证</div>'
                f'{buzz_items}'
                f'</div>'
            )

        has_buzz = bool(community_signals)
        border_color = '#f59e0b' if has_buzz else seg_color
        fire_badge = ('<span style="font-size:10px;background:#fef3c7;color:#d97706;'
                      'border:1px solid #fde68a;border-radius:4px;padding:1px 6px;'
                      'font-weight:700">🔥 社区热议</span> ') if has_buzz else ''

        return f'''<div style="border:1px solid {"#fde68a" if has_buzz else "#e5e7eb"};border-left:4px solid {border_color};
                       border-radius:8px;margin-bottom:14px;background:white;overflow:hidden">
  <div style="padding:14px 16px;background:{seg_color}08">
    <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px">
      <div style="font-size:14px;font-weight:700;color:#1a1a2e">{fire_badge}{theme}</div>
      <div style="display:flex;align-items:center;gap:6px;flex-shrink:0">
        {sps_html}
        {maturity_html}
        <span style="font-size:12px;font-weight:700;color:{score_color(score)}">{score}</span>
      </div>
    </div>
    <div style="font-size:11px;color:#6b7280;line-height:1.6">{why}</div>
  </div>
  <div style="padding:12px 16px">
    {shipped_html}
    {value_html}
    {leader_html}
    {sources_html}
  </div>
  {f'<div style="padding:8px 16px;background:#f9fafb;border-top:1px solid #f3f4f6;font-size:11px;color:#374151;line-height:1.7">{synth}</div>' if synth else ''}
  {buzz_block}
  {f'<div style="padding:10px 16px;background:#fffbeb;border-top:1px solid #fde68a"><div style="font-size:11px;color:#92400e;line-height:1.6"><strong>🔍 {sq}</strong></div><div style="font-size:11px;color:#78350f;margin-top:4px">📋 {action}</div></div>' if sq or action else ''}
  {f'<div style="padding:8px 16px;background:#fef2f2;border-top:1px solid #fecaca;display:flex;align-items:center;flex-wrap:wrap;gap:4px">{reaction_html}{teams_html}</div>' if reaction else ''}
</div>'''

    # ── Flatten all buzz posts for matching ───────────────────────────────
    all_buzz_posts = []
    for posts in (buzz_twitter or {}).values():
        all_buzz_posts.extend(dict(p) for p in posts)
    all_buzz_posts.extend(dict(r) for r in (hn_rows or []))

    # ── Build segment blocks ───────────────────────────────────────────────
    segments_html = ''
    for ci, (seg_key, seg_label, seg_emoji, seg_desc, _, __) in enumerate(GANMIE_SEGMENTS_RT):
        color    = GANMIE_COLORS[ci % len(GANMIE_COLORS)]
        clusters = ganmie_clusters.get(seg_key, [])
        arts     = ganmie_articles.get(seg_key, [])
        n_cl     = len(clusters)
        n_art    = len(arts)

        if clusters:
            body = ''.join(
                cluster_card(cl, color, community_signals=_match_buzz(cl, all_buzz_posts))
                for cl in clusters
            )
        elif arts:
            # Fallback: show top individual articles if no clusters yet
            def _art_card(row):
                src = JD_SOURCE_MAP.get(row['feed_name'], {}).get('label', row['feed_name'])
                pub = _parse_pub_date(row['published_date']).strftime('%m-%d')
                sc  = row['criteria_score'] or 0
                return (f'<div style="display:flex;gap:10px;padding:8px 0;border-top:1px solid #f3f4f6;align-items:flex-start">'
                        f'<span style="font-size:11px;font-weight:700;color:{score_color(sc)};flex-shrink:0;min-width:26px">{int(sc)}</span>'
                        f'<div><a href="{row["article_link"]}" target="_blank" style="font-size:12px;font-weight:600;color:#111827;text-decoration:none">{row["article_title"]}</a>'
                        f'<div style="font-size:10px;color:#9ca3af;margin-top:2px">{src} · {pub}</div></div></div>')
            body = (f'<div style="padding:10px 16px;background:#f9fafb;border-radius:6px;font-size:11px;color:#9ca3af;margin-bottom:8px">'
                    f'收敛分析待运行 — 显示最高分文章</div>')
            body += ''.join(_art_card(r) for r in arts[:6])
        else:
            body = '<div style="padding:20px;text-align:center;color:#d1d5db;font-size:12px">暂无数据 — 运行 retail_convergence.py 后填充</div>'

        badge = (f'<span style="background:{color}15;color:{color};border:1px solid {color}30;'
                 f'font-size:10px;font-weight:600;padding:2px 8px;border-radius:8px">'
                 f'{n_cl} 个聚类</span>' if n_cl else
                 f'<span style="background:#f3f4f6;color:#9ca3af;font-size:10px;padding:2px 8px;border-radius:8px">'
                 f'{n_art} 篇</span>')

        segments_html += f'''
<div style="margin-bottom:28px" id="seg-{seg_key}">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;
              padding-bottom:10px;border-bottom:2px solid {color}30">
    <span style="font-size:22px">{seg_emoji}</span>
    <div style="flex:1">
      <div style="font-size:15px;font-weight:700;color:#1a1a2e">{seg_label}</div>
      <div style="font-size:11px;color:#9ca3af;margin-top:1px">{seg_desc}</div>
    </div>
    {badge}
  </div>
  <div style="padding:0 4px">{body}</div>
</div>'''

    # Overview pills
    overview = ''
    for ci, (sk, sl, se, _, __, ___) in enumerate(GANMIE_SEGMENTS_RT):
        color = GANMIE_COLORS[ci % len(GANMIE_COLORS)]
        n = len(ganmie_clusters.get(sk, []))
        overview += (f'<a href="#seg-{sk}" style="text-decoration:none;display:inline-flex;'
                     f'align-items:center;gap:5px;background:white;border:1px solid #e5e7eb;'
                     f'border-left:3px solid {color};border-radius:6px;padding:6px 10px;'
                     f'font-size:11px;color:#1a1a2e;font-weight:500">'
                     f'{se} {sl}'
                     f'<span style="color:{color};font-weight:700">{n}</span></a>')

    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JD产业共识 · 8大业务域</title>
<style>
  * {{ box-sizing:border-box }}
  body {{ margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
          background:#f3f4f6;color:#1a1a2e }}
  .header {{ background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;padding:20px 32px }}
  .header h1 {{ margin:0 0 4px;font-size:20px;font-weight:700 }}
  .header .meta {{ font-size:12px;opacity:.65 }}
  .nav {{ background:#16213e;padding:0 32px;display:flex;align-items:center }}
  .nav a {{ color:rgba(255,255,255,.65);text-decoration:none;padding:10px 14px;
            font-size:13px;border-bottom:2px solid transparent;display:inline-block }}
  .nav a:hover,.nav a.active {{ color:white;border-bottom-color:#e74c3c }}
  .wrap {{ max-width:900px;margin:24px auto;padding:0 20px }}
</style>
</head>
<body>
<div class="header">
  <h1>🏭 产业共识</h1>
  <div class="meta">8大业务域跨来源收敛分析 · 近{days}天 · 共 {total_clusters} 个收敛聚类</div>
</div>
{_jd_nav("retail")}
<div class="wrap">
  <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:12px 16px;
              margin-bottom:16px;font-size:12px;color:#92400e;line-height:1.7">
    <strong>📌 收敛信号说明</strong> — 每个卡片代表来自多个独立来源对同一趋势的交叉印证。
    8大业务域覆盖搜索与内容、广告营销、智能零售、金融与支付、物流供应链、
    具身智能与机器人、智能硬件、AI基础设施。
    每个域显示该领域内产品/技术已落地的跨来源收敛信号，附体验/成本/效率三维价值分析与团队行动建议。
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:20px">
    {overview}
  </div>
  {segments_html}
</div>
</body>
</html>'''


BUZZ_TWITTER_FEEDS = list(TWITTER_PERSON_MAP.keys())

@app.route('/jd/retail')
def jd_retail():
    days = int(request.args.get('days', 60))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Load clusters grouped by scope (= ganmie segment key)
    cluster_rows = conn.execute("""
        SELECT * FROM intelligence_clusters
        WHERE scope != '' AND scope IS NOT NULL
          AND created_at >= datetime('now', '-7 days')
        ORDER BY convergence_score DESC
    """).fetchall()

    ganmie_clusters = {}
    for cl in cluster_rows:
        sk = cl['scope']
        ganmie_clusters.setdefault(sk, []).append(cl)

    # For segments with no clusters, load top individual articles as fallback
    ganmie_articles = {}
    if GANMIE_SEGMENTS_RT:
        for seg_key, _, _, _, seg_feeds, _ in GANMIE_SEGMENTS_RT:
            if seg_key not in ganmie_clusters:
                placeholders = ','.join('?' * len(seg_feeds))
                arts = conn.execute(
                    "SELECT id, feed_name, article_title, article_link, "
                    "published_date, criteria_score, criteria_reason, criteria "
                    "FROM articles WHERE feed_name IN (" + placeholders + ") "
                    "AND criteria_score >= 50 "
                    "AND published_date >= date('now', '-" + str(days) + " days') "
                    "ORDER BY criteria_score DESC LIMIT 6",
                    list(seg_feeds)
                ).fetchall()
                ganmie_articles[seg_key] = arts

    # ── 技术社区热议: twitter KOLs + HN ───────────────────────────────────
    tw_placeholders = ','.join('?' * len(BUZZ_TWITTER_FEEDS))
    tw_rows = conn.execute(
        "SELECT feed_name, article_title, article_link, published_date, criteria_score, criteria_reason "
        "FROM articles WHERE feed_name IN (" + tw_placeholders + ") "
        "AND published_date >= date('now','-10 days') "
        "ORDER BY published_date DESC LIMIT 60",
        BUZZ_TWITTER_FEEDS
    ).fetchall()

    # Group twitter by person, cap at 3 posts each
    buzz_twitter = {}
    for row in tw_rows:
        fn = row['feed_name']
        if fn not in buzz_twitter:
            buzz_twitter[fn] = []
        if len(buzz_twitter[fn]) < 3:
            buzz_twitter[fn].append(row)

    # HN: last 14 days, recency-sorted (scores unreliable until fix lands)
    hn_rows = conn.execute(
        "SELECT article_title, article_link, published_date, criteria_score, criteria_reason "
        "FROM articles WHERE feed_name='jd-hackernews' "
        "AND published_date >= date('now','-14 days') "
        "ORDER BY CASE WHEN criteria_score > 30 THEN criteria_score ELSE 0 END DESC, "
        "published_date DESC LIMIT 10"
    ).fetchall()

    conn.close()
    total_clusters = sum(len(v) for v in ganmie_clusters.values())
    return render_jd_retail(ganmie_clusters, ganmie_articles, total_clusters, days,
                            buzz_twitter=buzz_twitter, hn_rows=hn_rows)


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 智能RSS聚合服务（简化版）启动")
    print("=" * 60)
    print(f"📡 已配置RSS源: {len(config.RSS_FEEDS)} 个")
    print(f"\n📱 本地地址: http://localhost:5005/feed")
    print(f"🌐 永久地址: https://rss.borntofly.ai/feed.xml")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5005, debug=False)