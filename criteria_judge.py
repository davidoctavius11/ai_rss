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

    prompt = f"""你是一个严格的科技文章审稿人。请根据以下"筛选标准"，判断这篇文章是否符合要求。

---
【筛选标准】
{criteria}

---
【文章标题】
{title}

---
【文章内容】{content_type}
{content_sample}
{learning_section}
---
请完成两项任务：

1. 相关性评分（0-100分）：
   - 90-100：完全命中，有深度分析，直接相关
   - 70-89：强相关，有实质性内容，符合标准
   - 50-69：部分相关，擦边或信息不足
   - 30-49：弱相关，仅提到关键词但无实质
   - 20-29：完全不相关，或属于"严格排除"范围
   - 0-19：垃圾内容、广告、纯PR稿

2. 评分理由（一句话，如有学习关联则附在末尾）：
   说明为什么给这个分数，扣分点或加分点是什么。
   如果内容明显属于"严格排除"范围，请明确指出。

输出格式（严格按此JSON）：
{{"score": 整数, "reason": "一句话理由（含学习关联，若有）"}}
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是严谨的科技文章审稿人，严格按照给定的筛选标准打分，不偏袒不手软。即使只有摘要也要尽力判断。"},
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
