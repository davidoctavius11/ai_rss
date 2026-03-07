# generator.py - RSS生成器
import json
import re
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import pytz


def _strip_markdown(text):
    """Remove markdown syntax so RSS readers display clean plain text."""
    # Headers: ### Title → Title
    text = re.sub(r'^#{1,6}\s*\*{0,2}(.+?)\*{0,2}\s*$', r'\1', text, flags=re.MULTILINE)
    # Bold/italic: **text** or *text* → text
    text = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text)
    # Remove leftover leading/trailing asterisks on lines
    text = re.sub(r'^\*+\s*', '', text, flags=re.MULTILINE)
    # Horizontal rules
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Collapse 3+ blank lines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _story_note(cluster_member_of):
    """Add a back-link note for articles that are part of a story cluster but not the seed."""
    if not cluster_member_of:
        return ""
    title = cluster_member_of.get('seed_title', '')[:60]
    return f"\n\n🔗 本文是「{title}」故事的相关报道，点击封面文章可查看多视角总结。"


def _mp_block(mp_text, cluster_json):
    """Build the multi-perspective block for RSS descriptions."""
    if not mp_text:
        return ""
    source_line = ""
    if cluster_json:
        try:
            items = json.loads(cluster_json) if isinstance(cluster_json, str) else cluster_json
            sources = list(dict.fromkeys(item['source'] for item in items))  # unique, order-preserving
            source_line = f"\n综合 {len(items)} 篇报道 · 来自: {' / '.join(sources)}\n"
        except Exception:
            pass
    return f"\n\n🧠 多视角故事总结：{source_line}\n{_strip_markdown(mp_text)}"

class RSSGenerator:
    """生成标准RSS 2.0格式的聚合Feed"""
    
    def __init__(self, feed_title, feed_link="https://smart-rss.local", feed_description="AI智能筛选的资讯聚合"):
        self.feed_title = feed_title
        self.feed_link = feed_link
        self.feed_description = feed_description
    
    def _ensure_timezone(self, dt):
        """确保datetime对象有时区信息"""
        if dt is None:
            return datetime.now(timezone.utc)
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                # 如果没有时区，添加UTC时区
                return dt.replace(tzinfo=timezone.utc)
            return dt
        return datetime.now(timezone.utc)
    
    def generate(self, articles, output_path="feed.xml"):
        """生成RSS文件"""
        fg = FeedGenerator()
        fg.title(self.feed_title)
        fg.link(href=self.feed_link, rel='alternate')
        fg.description(self.feed_description)
        fg.language('zh-CN')
        
        for article in articles:
            fe = fg.add_entry()
            title = ("🧠 " + article['title']) if article.get('multi_perspective') else article['title']
            fe.title(title)
            fe.link(href=article.get('internal_link', article.get('link', '')))
            
            # 处理发布时间，确保有时区
            pub_date = self._ensure_timezone(article.get('published'))
            fe.pubDate(pub_date)
            
            ai_reason = article.get('ai_reason', '无筛选理由')
            summary = article.get('summary', '')[:500]
            mp = article.get('multi_perspective', '')
            mp_block = _mp_block(mp, article.get('cluster_json'))
            story_note = _story_note(article.get('cluster_member_of'))
            enhanced_summary = f"🤖 AI筛选理由：{ai_reason}\n\n📰 原文摘要：{summary}{story_note}{mp_block}"
            fe.description(enhanced_summary)
            fe.guid(article.get('link', str(hash(article['title']))), permalink=True)
            fe.author(name=article.get('source', '未知来源'))

        fg.rss_file(output_path, pretty=True)
        print(f"✅ RSS源已生成: {output_path}, 文章数: {len(articles)}")
        return output_path

    def generate_xml_string(self, articles):
        """直接生成XML字符串"""
        fg = FeedGenerator()
        fg.title(self.feed_title)
        fg.link(href=self.feed_link, rel='alternate')
        fg.description(self.feed_description)
        fg.language('zh-CN')

        for article in articles:
            fe = fg.add_entry()
            title = ("🧠 " + article['title']) if article.get('multi_perspective') else article['title']
            fe.title(title)
            fe.link(href=article.get('internal_link', article.get('link', '')))

            # 处理发布时间，确保有时区
            pub_date = self._ensure_timezone(article.get('published'))
            fe.pubDate(pub_date)

            ai_reason = article.get('ai_reason', '无筛选理由')
            summary = article.get('summary', '')[:500]
            mp = article.get('multi_perspective', '')
            mp_block = _mp_block(mp, article.get('cluster_json'))
            story_note = _story_note(article.get('cluster_member_of'))
            enhanced_summary = f"🤖 AI筛选理由：{ai_reason}\n\n📰 原文摘要：{summary}{story_note}{mp_block}"
            fe.description(enhanced_summary)
            fe.guid(article.get('link', str(hash(article['title']))), permalink=True)
            fe.author(name=article.get('source', '未知来源'))
        
        return fg.rss_str(pretty=True).decode('utf-8')
