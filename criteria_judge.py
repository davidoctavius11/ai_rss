#!/usr/bin/env python3
"""
AI RSS - 基于全文/RSS摘要的Criteria审阅器
用每个源自己的criteria，逐篇判断相关性
优先使用全文，如果没有全文则使用RSS摘要
不跳过任何文章，所有文章都会经过审阅
"""

import sqlite3
import json
import os
import time
from openai import OpenAI
from dotenv import dotenv_values

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ai_rss.db')
KNOWLEDGE_LOG_PATH = os.path.expanduser('~/Agents/knowledge_log/concepts.json')


def _load_knowledge_context():
    """Load a compact summary of active learning concepts for injection into scoring prompts."""
    try:
        with open(KNOWLEDGE_LOG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        lines = []
        for c in data.get('concepts', []):
            lines.append(f"[{c['domain']}] {c['concept']}: {', '.join(c.get('keywords', []))}")
        return '\n'.join(lines)
    except Exception:
        return ''
DEFAULT_THRESHOLD = 50
FULLTEXT_PREFETCH_LIMIT = 120
FULLTEXT_PREFETCH_DAYS = 90

# Read API credentials directly from .env file to bypass stale shell environment variables
_env = dotenv_values(os.path.join(os.path.dirname(__file__), '.env'))
client = OpenAI(
    api_key=_env.get('DEEPSEEK_API_KEY') or _env.get('OPENAI_API_KEY'),
    base_url=_env.get('OPENAI_BASE_URL', 'https://api.deepseek.com/v1')
)

# 从config.py导入RSS_FEEDS
import sys
sys.path.append(os.path.dirname(__file__))
try:
    from config import RSS_FEEDS
except ImportError:
    RSS_FEEDS = []

# 构建源名称到criteria的映射
FEED_CRITERIA_MAP = {}
for feed in RSS_FEEDS:
    FEED_CRITERIA_MAP[feed['name']] = feed.get('criteria', '')

def judge_article(article_id, feed_name, title, content, is_fulltext=False, borrowed_from=None):
    """
    用该源专属的criteria审阅单篇文章
    content可能是全文也可能是RSS摘要
    is_fulltext: 用于日志区分
    """

    criteria = FEED_CRITERIA_MAP.get(feed_name, '')
    if not criteria:
        return 50, "无明确criteria，默认保留"

    # 如果内容过短或缺失，至少用标题参与判断（不忽略）
    if not content or len(content) < 50:
        content = f"{title}\n\n{content or ''}".strip()

    # 根据内容长度决定截取多少
    content_sample = content[:3000] if len(content) > 3000 else content
    if is_fulltext and len(content) > 500:
        content_type = "【全文】"
    elif len(content) >= 50:
        content_type = "【RSS摘要】"
    else:
        content_type = "【标题】"
    if borrowed_from:
        content_type += f"(来自: {borrowed_from})"

    knowledge_context = _load_knowledge_context()
    learning_section = ""
    if knowledge_context:
        learning_section = f"""
---
【我正在学习的技术领域（来自真实项目实践）】
{knowledge_context}

3. 学习关联（可选）：
   如果这篇文章与上述任一领域有实质关联，用半句话点出（例如："与我们用LaunchAgents管理进程的实践相关"）。
   无关联则输出 null。
   将关联内容拼接在reason末尾，格式：reason内容 + " — " + 学习关联。
"""

    source_criteria = criteria

    prompt = f"""你是一位CTO级别的情报审稿人，专门识别「超前市场」的产品与商业创新信号。

你的核心任务：判断这篇文章是否包含竞争对手尚未掌握、但未来6-18个月内将成为行业标配的信号。

高价值信号（加分）：
- 实际构建者的第一手经验：工程师/创始人部署新技术后的真实发现和意外收获
- 产品范式转变的早期证据：用户行为改变、新商业模式出现、旧有假设被推翻
- 技术使能新市场的具体案例：不限于AI，任何技术栈驱动的产品创新
- 竞争对手的早期动作（产品发布、团队扩张、战略转型）
- 「别人还不知道但12个月后会成常识」的洞察

低价值信号（扣分）：
- 主流媒体对已知趋势的综述（人人皆知的内容）
- 无产品落地的纯学术研究（数学推导、消融实验、无实证）
- 营销/PR稿、软文、成功案例包装
- 对已公布信息的新闻跟进报道
- 概念演示、无商业路径的技术展示

评分0-100：
90-100 = 超前市场第一手信号，竞争对手尚未关注
70-89 = 有实质内容，值得深入研究
50-69 = 有参考价值，但信号较弱
30-49 = 低价值，主要是已知信息
0-29 = 无价值，广告/PR/纯综述

来源标识：{source_criteria}

文章标题：{title}
文章内容：{content_sample}
{learning_section}
请直接给出：评分（数字）和简短中文理由（2-3句，重点说明为什么有/没有超前市场信号）。
格式：输出JSON {{"score": 整数, "reason": "理由"}}"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是CTO级别的情报分析师，专门识别超前市场的产品与商业创新信号。你的任务是评估一篇文章是否包含竞争对手尚未掌握、但未来6-18个月内将成为行业标配的信号。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=280,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        score = int(result.get('score', 50))
        reason = result.get('reason', '无理由')
        
        # 确保分数在0-100之间
        score = max(0, min(100, score))
        
        return score, reason
        
    except Exception as e:
        print(f"  ⚠️ 审阅失败: {e}")
        return 40, f"AI审阅出错: {str(e)[:50]}"

def batch_judge_unread(threshold=DEFAULT_THRESHOLD, limit=200, prefetch=True, only_missing_fulltext=False):
    """
    批量审阅未评分的文章
    优先使用全文，如果没有全文则使用RSS摘要
    threshold: 低于此分的标记为淘汰
    """
    # 预抓全文：提升评分质量（优先覆盖最近文章）
    if prefetch:
        try:
            from fulltext_fetcher import update_articles_with_fulltext
            print(f"🧠 预抓全文: 最近{FULLTEXT_PREFETCH_DAYS}天，最多{FULLTEXT_PREFETCH_LIMIT}篇")
            update_articles_with_fulltext(
                limit=FULLTEXT_PREFETCH_LIMIT,
                force=False,
                feed_name=None,
                days=FULLTEXT_PREFETCH_DAYS,
            )
        except Exception as e:
            print(f"⚠️ 预抓全文失败: {e}")
    else:
        print("⏭️ 已跳过全文预抓（仅用摘要/标题打分）")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 查找所有未评分的文章，优先使用全文，没有全文就用raw_content；若都缺失则用标题
    base_query = '''
        SELECT 
            id, 
            feed_name, 
            article_title, 
            article_link,
            CASE 
                WHEN content IS NOT NULL AND length(content) > 200 THEN content 
                WHEN raw_content IS NOT NULL AND length(raw_content) > 0 THEN raw_content
                ELSE article_title
            END as content_to_judge,
            CASE 
                WHEN content IS NOT NULL AND length(content) > 200 THEN 1 
                ELSE 0 
            END as has_fulltext
        FROM articles
        WHERE criteria_score IS NULL
    '''
    if only_missing_fulltext:
        base_query += '''
        AND (content IS NULL OR length(content) <= 200)
        '''
    base_query += '''
        ORDER BY published_date DESC
        LIMIT ?
    '''
    c.execute(base_query, (limit,))
    
    articles = c.fetchall()
    if only_missing_fulltext:
        print(f"⚖️ 共 {len(articles)} 篇文章待审阅（仅缺失全文的文章）")
    else:
        print(f"⚖️ 共 {len(articles)} 篇文章待审阅（含RSS摘要）")
    
    kept = 0
    rejected = 0
    fulltext_count = 0
    summary_count = 0
    
    def _borrow_content_by_title(article_id, title):
        """从同标题的其他来源借用全文/摘要"""
        c.execute('''
            SELECT feed_name, content, raw_content
            FROM articles
            WHERE article_title = ?
              AND id != ?
              AND (
                    (content IS NOT NULL AND length(content) > 200)
                 OR (raw_content IS NOT NULL AND length(raw_content) > 0)
              )
            ORDER BY length(content) DESC
            LIMIT 1
        ''', (title, article_id))
        row = c.fetchone()
        if not row:
            return None, None
        borrowed_feed = row[0]
        borrowed_content = row[1] if row[1] and len(row[1]) > 200 else row[2]
        return borrowed_content, borrowed_feed

    for row in articles:
        article_id = row['id']
        feed_name = row['feed_name']
        title = row['article_title']
        content = row['content_to_judge']
        has_fulltext = row['has_fulltext']
        borrowed_from = None

        # 如果只有标题/超短内容，尝试从其他来源借全文/摘要
        if not content or len(content) < 50:
            borrowed, borrowed_from = _borrow_content_by_title(article_id, title)
            if borrowed:
                content = borrowed
        
        if has_fulltext:
            fulltext_count += 1
        else:
            summary_count += 1
        
        print(f"\n📄 {feed_name} - {title[:60]}...")
        print(f"  内容类型: {'✅ 全文' if has_fulltext else '📋 RSS摘要'}, 长度: {len(content)} 字")
        
        score, reason = judge_article(article_id, feed_name, title, content, is_fulltext=has_fulltext, borrowed_from=borrowed_from)
        
        # 存入数据库
        c.execute('''
            UPDATE articles
            SET criteria_score = ?, criteria_reason = ?
            WHERE id = ?
        ''', (score, reason, article_id))
        conn.commit()
        
        if score >= threshold:
            kept += 1
            status = "✅ 保留"
        else:
            rejected += 1
            status = "❌ 淘汰"
        
        print(f"  评分: {score} | {reason}")
        print(f"  结果: {status}")
        
        time.sleep(0.5)  # API限流保护
    
    conn.close()
    print(f"\n🎯 审阅完成:")
    print(f"  - 全文审阅: {fulltext_count} 篇")
    print(f"  - 摘要审阅: {summary_count} 篇")
    print(f"  - 保留: {kept} 篇 (≥{threshold}分)")
    print(f"  - 淘汰: {rejected} 篇 (<{threshold}分)")
    return kept, rejected

def get_scoring_stats():
    """获取评分统计"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("\n📊 评分统计")
    print("=" * 60)
    
    # 各源平均分
    c.execute('''
        SELECT 
            feed_name,
            COUNT(*) as total,
            AVG(criteria_score) as avg_score,
            SUM(CASE WHEN criteria_score >= ? THEN 1 ELSE 0 END) as kept,
            SUM(CASE WHEN fulltext_fetched = 1 THEN 1 ELSE 0 END) as has_fulltext
        FROM articles
        WHERE criteria_score IS NOT NULL
        GROUP BY feed_name
        ORDER BY avg_score DESC
    ''', (DEFAULT_THRESHOLD,))
    
    rows = c.fetchall()
    for row in rows:
        feed_name = row[0]
        total = row[1]
        avg = row[2]
        kept = row[3] or 0
        fulltext = row[4] or 0
        print(f"  {feed_name[:30]:<30} 平均分:{avg:5.1f} 保留:{kept:3d}/{total:3d} 全文:{fulltext:3d}")
    
    # 总体统计
    c.execute('''
        SELECT 
            COUNT(*) as total,
            AVG(criteria_score) as avg_score,
            SUM(CASE WHEN criteria_score >= ? THEN 1 ELSE 0 END) as kept,
            SUM(CASE WHEN criteria_score < ? THEN 1 ELSE 0 END) as rejected
        FROM articles
        WHERE criteria_score IS NOT NULL
    ''', (DEFAULT_THRESHOLD, DEFAULT_THRESHOLD))
    
    total, avg, kept, rejected = c.fetchone()
    print("\n" + "=" * 60)
    print(f"📈 总计: {total} 篇文章, 平均分 {avg:.1f}")
    print(f"  ✅ 保留: {kept} 篇 ({kept/total*100:.1f}%)" if total > 0 else "  ✅ 保留: 0 篇")
    print(f"  ❌ 淘汰: {rejected} 篇 ({rejected/total*100:.1f}%)" if total > 0 else "  ❌ 淘汰: 0 篇")
    print("=" * 60)
    
    conn.close()

def reset_scores():
    """重置所有评分，用于重新审阅"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE articles SET criteria_score = NULL, criteria_reason = NULL')
    conn.commit()
    count = c.rowcount
    conn.close()
    print(f"✅ 已重置 {count} 篇文章的评分")
    return count

def judge_specific_feed(feed_name, threshold=DEFAULT_THRESHOLD):
    """专门审阅某个源的未评分文章"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
        SELECT 
            id, 
            feed_name, 
            article_title, 
            article_link,
            raw_content as content_to_judge,
            CASE 
                WHEN content IS NOT NULL AND length(content) > 200 THEN 1 
                ELSE 0 
            END as has_fulltext
        FROM articles
        WHERE criteria_score IS NULL
        AND feed_name = ?
        AND (
            (content IS NOT NULL AND length(content) > 50)
            OR 
            (raw_content IS NOT NULL AND length(raw_content) > 50)
        )
        ORDER BY published_date DESC
    ''', (feed_name,))
    
    articles = c.fetchall()
    print(f"⚖️ {feed_name}: {len(articles)} 篇文章待审阅")
    
    kept = 0
    rejected = 0
    
    for row in articles:
        article_id = row['id']
        feed_name = row['feed_name']
        title = row['article_title']
        content = row['content_to_judge']
        has_fulltext = row['has_fulltext']
        
        print(f"\n📄 {title[:60]}...")
        score, reason = judge_article(article_id, feed_name, title, content, is_fulltext=has_fulltext)
        
        c.execute('''
            UPDATE articles
            SET criteria_score = ?, criteria_reason = ?
            WHERE id = ?
        ''', (score, reason, article_id))
        conn.commit()
        
        if score >= threshold:
            kept += 1
            status = "✅ 保留"
        else:
            rejected += 1
            status = "❌ 淘汰"
        
        print(f"  评分: {score} | {reason}")
        print(f"  结果: {status}")
        
        time.sleep(0.5)
    
    conn.close()
    print(f"\n🎯 {feed_name} 审阅完成: 保留 {kept} 篇, 淘汰 {rejected} 篇")
    return kept, rejected

if __name__ == '__main__':
    import sys
    skip_prefetch_env = os.getenv("SKIP_FULLTEXT_PREFETCH", "").strip().lower() in ("1", "true", "yes", "y")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--reset":
            reset_scores()
        elif sys.argv[1] == "--stats":
            get_scoring_stats()
        elif sys.argv[1] == "--feed" and len(sys.argv) > 2:
            judge_specific_feed(sys.argv[2])
        elif sys.argv[1] == "--no-prefetch":
            batch_judge_unread(threshold=DEFAULT_THRESHOLD, limit=200, prefetch=False)
        elif sys.argv[1] == "--only-missing-fulltext":
            batch_judge_unread(threshold=DEFAULT_THRESHOLD, limit=200, prefetch=False, only_missing_fulltext=True)
        elif sys.argv[1] == "--threshold" and len(sys.argv) > 2:
            threshold = int(sys.argv[2])
            batch_judge_unread(threshold=threshold, limit=200, prefetch=not skip_prefetch_env)
        else:
            print("用法:")
            print("  python criteria_judge.py              # 正常审阅（阈值60）")
            print("  python criteria_judge.py --threshold 50  # 设置阈值50")
            print("  python criteria_judge.py --no-prefetch   # 不预抓全文，仅用摘要/标题")
            print("  python criteria_judge.py --only-missing-fulltext  # 仅评分缺失全文的文章")
            print("  SKIP_FULLTEXT_PREFETCH=1 python criteria_judge.py --threshold 50  # 环境变量跳过全文预抓")
            print("  python criteria_judge.py --reset      # 重置所有评分")
            print("  python criteria_judge.py --stats      # 查看评分统计")
            print("  python criteria_judge.py --feed '源名称' # 专门审阅某个源")
    else:
        batch_judge_unread(threshold=DEFAULT_THRESHOLD, limit=200, prefetch=not skip_prefetch_env)
        get_scoring_stats()
