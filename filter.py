# filter.py - DeepSeek AI筛选器
import os
import json
import time
from openai import OpenAI

class DeepSeekFilter:
    """使用DeepSeek API筛选文章"""
    
    def __init__(self, api_key=None, model="deepseek-v4-pro"):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("❌ 未找到DeepSeek API Key")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )
        self.model = model
        print(f"✅ DeepSeek筛选器已就绪")
    
    def _truncate(self, text, max_len=600):
        if not text:
            return ""
        return text[:max_len] + "..." if len(text) > max_len else text
    
    def should_keep(self, article, criteria):
        title_preview = article.get('title', '无标题')[:30]
        print(f"  🎯 DeepSeek分析: {title_preview}...")
        
        try:
            messages = [
                {"role": "system", "content": """你是一个专业的内容筛选助手。
输出必须是JSON格式，包含两个字段：
- "keep": true或false
- "reason": 中文判断理由（20字以内）"""},
                {"role": "user", "content": f"""【筛选标准】
{criteria}

【文章信息】
标题：{article.get('title', '无标题')}
来源：{article.get('source', '未知')}
摘要：{self._truncate(article.get('summary', ''), 500)}

请输出JSON判断结果："""}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            keep = result.get("keep", False)
            reason = result.get("reason", "无理由")
            
            print(f"     {'✅ 保留' if keep else '❌ 忽略'} - {reason}")
            return keep, reason, 0.00001
            
        except Exception as e:
            print(f"     ⚠️ 筛选失败: {str(e)[:40]}...")
            return False, f"错误: {type(e).__name__}", 0.0
    
    def batch_filter(self, articles, criteria, delay=0.5):
        print(f"\n🔍 开始筛选 {len(articles)} 篇文章")
        kept = []
        total_cost = 0.0
        
        for i, article in enumerate(articles):
            print(f"  [{i+1}/{len(articles)}]", end="")
            keep, reason, cost = self.should_keep(article, criteria)
            if keep:
                article['ai_reason'] = reason
                kept.append(article)
            total_cost += cost
            time.sleep(delay)
        
        print(f"\n📊 筛选完成: 保留 {len(kept)}/{len(articles)} 篇")
        return kept, total_cost
