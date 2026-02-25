# config.example.py - example configuration (copy to config.py)

import os

MY_AGGREGATED_FEED_TITLE = "AI RSS Example"

# RSSHub support (optional)
RSSHUB_BASE = os.getenv("RSSHUB_BASE", "http://localhost:1200").rstrip("/")
RSSHUB_TOKEN = os.getenv("RSSHUB_TOKEN", "").strip()
RSSHUB_TOKEN_PARAM = f"?key={RSSHUB_TOKEN}" if RSSHUB_TOKEN else ""

RSS_FEEDS = [
    {
        "name": "36氪",
        "url": "https://www.36kr.com/feed",
        "priority": "high",
        "criteria": """筛选与AI产业应用、产品落地、商业化进展相关的报道（覆盖更广范围）。
        重点关注：企业转型案例、技术落地代价、算力/数据成本对业务影响、AI产品发布与功能更新、行业趋势与竞争格局。
        可接受：创始人/CTO访谈、行业调研、趋势分析、涉及AI的新品与功能更新（需有应用场景或业务影响）。
        严格排除：广告与营销软文。"""
    },
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/news/rss.xml",
        "priority": "high",
        "criteria": """筛选OpenAI的模型更新、API发布、安全策略。
        重点关注：GPT系列、Sora等新能力的技术报告和应用案例。
        可接受：系统卡、安全分析报告。
        严格排除：纯政策倡导、公司治理新闻。"""
    },
    {
        "name": "AWS Machine Learning Blog",
        "url": "https://aws.amazon.com/blogs/machine-learning/feed/",
        "priority": "high",
        "criteria": """重点关注：真实行业落地案例、架构设计、成本/性能权衡、MLOps流程与运维经验。
        可接受：端到端参考实现与实验复盘。
        严格排除：纯产品发布、入门级教程、营销软文。"""
    },
    {
        "name": "Solidot 科技",
        "url": f"{RSSHUB_BASE}/solidot/technology{RSSHUB_TOKEN_PARAM}",
        "enabled": False,
        "priority": "high",
        "criteria": """筛选普通科技爱好者感兴趣的硬新闻。
        重点关注：开源项目新动态、互联网服务变化、隐私安全事件、智能硬件发布。
        可接受：技术趋势简讯、开发者工具更新。
        严格排除：Linux内核补丁讨论、编程语言规范。"""
    },
]

print(f"✅ example config loaded, feeds: {len(RSS_FEEDS)}")
