# generator.py - RSS生成器
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import pytz

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
            fe.title(article['title'])
            fe.link(href=article.get('internal_link', article.get('link', '')))
            
            # 处理发布时间，确保有时区
            pub_date = self._ensure_timezone(article.get('published'))
            fe.pubDate(pub_date)
            
            ai_reason = article.get('ai_reason', '无筛选理由')
            summary = article.get('summary', '')[:500]
            mp = article.get('multi_perspective', '')
            mp_block = f"\n\n🧠 多视角总结：\n{mp}" if mp else ""
            enhanced_summary = f"🤖 AI筛选理由：{ai_reason}\n\n📰 原文摘要：{summary}{mp_block}"
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
            fe.title(article['title'])
            fe.link(href=article.get('internal_link', article.get('link', '')))
            
            # 处理发布时间，确保有时区
            pub_date = self._ensure_timezone(article.get('published'))
            fe.pubDate(pub_date)
            
            ai_reason = article.get('ai_reason', '无筛选理由')
            summary = article.get('summary', '')[:500]
            mp = article.get('multi_perspective', '')
            mp_block = f"\n\n🧠 多视角总结：\n{mp}" if mp else ""
            enhanced_summary = f"🤖 AI筛选理由：{ai_reason}\n\n📰 原文摘要：{summary}{mp_block}"
            fe.description(enhanced_summary)
            fe.guid(article.get('link', str(hash(article['title']))), permalink=True)
            fe.author(name=article.get('source', '未知来源'))
        
        return fg.rss_str(pretty=True).decode('utf-8')
