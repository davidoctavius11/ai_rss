# config.py - 最终版 (整合 Karpathy 精选博客 & 国内优化源)

import os

# RSSHub 支持（用于本地或自建RSSHub）
RSSHUB_BASE = os.getenv("RSSHUB_BASE", "http://localhost:1200").rstrip("/")
RSSHUB_TOKEN = os.getenv("RSSHUB_TOKEN", "").strip()
RSSHUB_TOKEN_PARAM = f"?key={RSSHUB_TOKEN}" if RSSHUB_TOKEN else ""

MY_AGGREGATED_FEED_TITLE = "AI重塑·真实可用 | 算力×算法×数据×组织×商业"

RSS_FEEDS = [
    # ========== 一、国内核心深度媒体 (可全文抓取) ==========
    {
        "name": "腾讯研究院",
        "url": "https://tisi.org/rss",
        "priority": "low",
        "criteria": """保留。研究机构的宏观趋势分析、行业展望、政策解读均有价值。
        重点关注：AI对产业/社会/组织的长期影响、技术伦理、数字化转型。
        可接受：有数据支撑的行业报告、问卷调查、案例分析。
        严格排除：纯公关稿、企业宣传、无实质内容的短评。"""
    },
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
        "name": "虎嗅",
        "url": "https://www.huxiu.com/rss/",
        "enabled": False,  # 2026-02-25 健康检查: 404
        "priority": "high",
        "criteria": """筛选商业科技领域的深度评论和产业分析。
        重点关注：AI创业公司动态、传统行业数字化转型、商业模式创新。
        可接受：行业趋势解读、科技伦理讨论。
        严格排除：纯个人观点散文、无信息量的短讯。"""
    },
    {
        "name": "极客公园",
        "url": "https://www.geekpark.net/rss",
        "enabled": False,  # 2026-02-25 健康检查: 连接被远端关闭
        "priority": "medium",
        "criteria": """筛选关于科技产品、硬件创新、AI应用的前沿报道。
        重点关注：AI在消费电子、智能硬件领域的落地案例。
        可接受：产品深度评测、创始人故事、技术科普。
        严格排除：纯产品参数表、发布会流水账。"""
    },
    {
        "name": "InfoQ·架构与算力",
        "url": "https://feed.infoq.com/",
        "priority": "medium",
        "criteria": """筛选关于大模型工程、AI架构、云原生实践的技术管理文章。
        重点关注：技术选型背后的组织决策、算力成本优化、工程实践。
        可接受：技术会议演讲实录、团队管理经验。
        严格排除：纯产品发布、入门教程。"""
    },
    {
        "name": "爱范儿·未来商业",
        "url": "https://www.ifanr.com/feed",
        "priority": "medium",
        "criteria": """筛选AI/算力如何重塑传统行业、改变普通人工作方式的商业案例。
        重点关注：实体行业（零售、物流、制造、设计）被AI赋能的真实故事、成本结构变化。
        可接受：消费级AI产品的市场分析。
        严格排除：纯手机评测、发布会通稿、融资快讯。"""
    },
    {
        "name": "晚点LatePost",
        "url": f"{RSSHUB_BASE}/latepost/1{RSSHUB_TOKEN_PARAM}",
        "enabled": False,  # 2026-02-25 健康检查: rsshub.app 403；启用需自建RSSHub
        "priority": "low",
        "criteria": """筛选中国科技公司在AI时代的战略焦虑、组织调整的深度报道。
        重点关注：具体公司如何调整预算/团队应对AI冲击、算力投入与实际产出的落差。
        可接受：高管访谈中涉及决策逻辑的部分。
        严格排除：股价波动、普通人事变动、娱乐化八卦。"""
    },

    # ========== 二、国外顶尖科技/AI博客 (从 rushter 清单精选) ==========
    {
        "name": "Google Research Blog",
        "url": "http://feeds.feedburner.com/blogspot/gJZg",
        "priority": "low",
        "criteria": """筛选已经或即将产品化的技术突破。
        重点关注：Gemini等大模型的技术预告、Android/Chrome的新AI能力、开发者工具。
        可接受：有Demo视频、开源代码、交互示例的研究。
        严格排除：纯学术论文预印本、距离落地超过3年的前瞻研究。"""
    },
    {
        "name": "Meta AI Blog",
        "url": "https://ai.meta.com/blog/feed/",
        "enabled": False,  # 2026-02-25 健康检查: 404
        "priority": "low",
        "criteria": """筛选Meta在LLM、计算机视觉、AR/VR领域的应用型研究成果。
        重点关注：Llama系列模型更新、AI在社交/元宇宙场景的落地。
        可接受：有实际产品影响的算法创新。
        严格排除：纯理论研究、无法复现的结论。"""
    },
    {
        "name": "DeepMind Blog",
        "url": "https://deepmind.com/blog/feed",
        "priority": "low",
        "criteria": """筛选DeepMind在通用AI、多模态、科学计算领域的突破性研究。
        重点关注：AlphaFold、Gemini等项目的技术解读。
        可接受：有潜在工业价值的前沿探索。
        严格排除：数学推导过多的纯理论文章。"""
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
        "name": "Anthropic Blog",
        "url": "https://www.anthropic.com/feed.xml",
        "enabled": False,  # 2026-02-25 健康检查: 404
        "priority": "medium",
        "criteria": """筛选Claude模型更新、AI安全、可解释性研究。
        重点关注：模型能力边界、对齐技术、实际应用。
        可接受：技术论文解读、安全框架讨论。
        严格排除：纯哲学讨论、无实证的伦理猜测。"""
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "priority": "medium",
        "criteria": """筛选开源数据集/模型的应用案例。
        重点关注：开发者如何用HF生态快速搭建应用、社区热门模型解读。
        可接受：新模型的技术解读（需有性能对比）。
        严格排除：纯模型卡片发布、商业化功能宣传。"""
    },
    {
        "name": "Simon Willison's Blog",
        "url": "https://simonwillison.net/feed/",
        "enabled": False,  # 2026-02-25 健康检查: 404
        "priority": "high",
        "criteria": """筛选AI工具实战、LLM应用边界、技术趋势思考。
        重点关注：如何用现有模型解决实际问题、工具评测。
        可接受：技术讲座笔记、开源项目介绍。
        严格排除：纯代码片段、无上下文的技术吐槽。"""
    },
    {
        "name": "Dan Luu's Blog",
        "url": "https://danluu.com/atom.xml",
        "priority": "low",
        "criteria": """筛选关于硬件/软件性能、编程语言、技术决策的微观分析。
        重点关注：技术选型的长期成本、系统瓶颈剖析。
        可接受：数据详实的性能对比。
        严格排除：入门教程、无数据的空谈。"""
    },
    {
        "name": "Julia Evans' Blog",
        "url": "https://jvns.ca/atom.xml",
        "priority": "medium",
        "criteria": """筛选关于系统原理、调试、网络的深度科普。
        重点关注：用易懂方式解释复杂技术问题。
        可接受：Zine漫画、排查案例。
        严格排除：编程语言入门、纯语法讲解。"""
    },
    {
        "name": "Sebastian Raschka's Blog",
        "url": "https://sebastianraschka.com/rss.xml",
        "enabled": False,  # 2026-02-25 健康检查: 404
        "priority": "low",
        "criteria": """筛选关于PyTorch、模型架构、LLM微调的深度解析。
        重点关注：从代码实现角度理解论文、训练技巧。
        可接受：技术书籍节选、算法演进综述。
        严格排除：基础API教程、新手入门。"""
    },
    {
        "name": "Andrej Karpathy's Blog",
        "url": "https://karpathy.ai/feed.xml",
        "priority": "high",
        "criteria": """筛选AI教育、LLM原理、技术创业的深度思考。
        重点关注：技术概念的直观解释、AI发展展望。
        可接受：课程资料、代码库介绍。
        严格排除：日常碎碎念。"""
    },
    {
        "name": "Lil'Log (Lilian Weng)",
        "url": "https://lilianweng.github.io/feed.xml",
        "enabled": False,  # 2026-02-25 健康检查: 404
        "priority": "low",
        "criteria": """筛选关于强化学习、LLM、多模态的前沿综述。
        重点关注：对特定技术领域的系统性梳理。
        可接受：论文笔记、趋势总结。
        严格排除：缺乏深度的新闻快讯。"""
    },
    {
        "name": "Eugene Yan's Blog",
        "url": "https://eugeneyan.com/feed.xml",
        "enabled": False,  # 2026-02-25 健康检查: 404
        "priority": "medium",
        "criteria": """筛选关于推荐系统、LLM应用、数据科学的实战经验。
        重点关注：工业界真实部署案例、AB测试经验。
        可接受：技术调研报告、工具链分享。
        严格排除：纯学术论文翻译。"""
    },

    # ========== 新增：产业AI/基础设施/生产力/数据科学 ==========
    {
        "name": "AWS Machine Learning Blog",
        "url": "https://aws.amazon.com/blogs/machine-learning/feed/",
        "enabled": True,  # 临时启用用于健康检查
        "priority": "high",
        "criteria": """重点关注：真实行业落地案例、架构设计、成本/性能权衡、MLOps流程与运维经验。
        可接受：端到端参考实现与实验复盘。
        严格排除：纯产品发布、入门级教程、营销软文。"""
    },
    {
        "name": "Microsoft AI Blog",
        "url": "https://blogs.microsoft.com/ai/feed/",
        "enabled": True,  # 临时启用用于健康检查
        "priority": "high",
        "criteria": """重点关注：企业AI应用落地、Copilot/生产力改造、组织流程与安全治理。
        可接受：客户案例与ROI分析。
        严格排除：纯PR、与AI无关的公司新闻。"""
    },
    {
        "name": "Google AI Blog",
        "url": "https://blog.google/technology/ai/rss/",
        "enabled": True,  # 临时启用用于健康检查
        "priority": "medium",
        "criteria": """重点关注：AI产品/平台在实际业务中的应用与落地经验。
        可接受：重要模型能力发布及其应用场景。
        严格排除：与AI无关的泛科技新闻。"""
    },
    {
        "name": "NVIDIA Developer Blog",
        "url": "https://developer.nvidia.com/blog/feed",
        "enabled": True,  # 临时启用用于健康检查
        "priority": "high",
        "criteria": """重点关注：训练/推理加速、算力优化、部署栈、CUDA/Triton实践。
        可接受：性能对比与工程实战。
        严格排除：活动宣传、无数据的观点文。"""
    },
    {
        "name": "NVIDIA Newsroom",
        "url": "https://nvidianews.nvidia.com/releases.xml",
        "enabled": True,  # 临时启用用于健康检查
        "priority": "medium",
        "criteria": """重点关注：数据中心、AI平台、企业合作与生态战略。
        可接受：重大产品发布与产业影响分析。
        严格排除：与AI无关的公司新闻。"""
    },
    {
        "name": "Apple Machine Learning Research",
        "url": "https://machinelearning.apple.com/rss.xml",
        "enabled": True,  # 临时启用用于健康检查
        "priority": "medium",
        "criteria": """重点关注：端侧AI、隐私保护、模型/算法研究进展。
        可接受：系统性方法与数据集贡献。
        严格排除：无技术细节的摘要或宣传。"""
    },
    {
        "name": "PyTorch Blog",
        "url": "https://pytorch.org/feed.xml",
        "enabled": False,  # 2026-02-25 健康检查: HTTP 404
        "priority": "medium",
        "criteria": """重点关注：训练/推理性能优化、部署与工程化实践、框架新特性。
        可接受：生态合作带来的技术价值。
        严格排除：社区活动通告、无技术深度的更新。"""
    },
    {
        "name": "Salesforce AI Research Blog",
        "url": "https://www.salesforce.com/blog/category/ai-research/feed/",
        "enabled": True,  # 临时启用用于健康检查
        "priority": "medium",
        "criteria": """重点关注：LLM/对话系统/自动化的研究与应用进展。
        可接受：可复现的研究方法与实验结果。
        严格排除：无实验细节的营销内容。"""
    },
    {
        "name": "The Gradient",
        "url": "https://thegradient.pub/rss/",
        "enabled": True,  # 临时启用用于健康检查
        "priority": "medium",
        "criteria": """重点关注：算法/模型/系统研究综述与趋势分析。
        可接受：有证据链的产业影响讨论。
        严格排除：纯观点、无实证内容。"""
    },
    {
        "name": "QwenLM Blog",
        "url": "https://qwenlm.github.io/blog/index.xml",
        "enabled": True,  # 临时启用用于健康检查
        "priority": "medium",
        "criteria": """重点关注：模型能力更新、推理优化、多模态与工具使用进展。
        可接受：开源模型与基准评测解读。
        严格排除：无技术细节的宣传。"""
    },

    # ========== 三、国内大众化/科普入口 (平衡多样性) ==========
    {
        "name": "Solidot 科技",
        "url": f"{RSSHUB_BASE}/solidot/technology{RSSHUB_TOKEN_PARAM}",
        "enabled": False,  # 2026-02-25 健康检查: RSSHub 未运行；启用需自建RSSHub
        "priority": "high",
        "criteria": """筛选普通科技爱好者感兴趣的硬新闻。
        重点关注：开源项目新动态、互联网服务变化、隐私安全事件、智能硬件发布。
        可接受：技术趋势简讯、开发者工具更新。
        严格排除：Linux内核补丁讨论、编程语言规范。"""
    },
    {
    "name": "知乎每日精选",
    "url": f"{RSSHUB_BASE}/zhihu/daily{RSSHUB_TOKEN_PARAM}",  # 需要RSSHub
    "enabled": False,  # 2026-02-25 健康检查: RSSHub 未运行；启用需自建RSSHub
    "priority": "high",
    "criteria": """只保留与**人工智能、大模型、前沿科技、产业趋势、科技商业、数据科学**强相关的科普或深度讨论。
    
    重点关注以下**具体主题**：
    - AI大模型（如GPT、Sora、Llama）的技术解读、应用案例、行业影响
    - 芯片、算力、数据中心的发展与博弈
    - 自动驾驶、机器人、智能硬件
    - 科技公司的战略、组织变革、商业竞争
    - 数据科学、算法原理的通俗解释
    
    严格排除**所有**与以上主题无关的内容，包括但不限于：
    - 自然科学（物理、化学、生物、医学、动物、植物）
    - 生活常识、健康养生、饮食文化
    - 历史、文学、艺术、哲学、心理学
    - 社会新闻、娱乐八卦、情感问答
    
    判断标准：文章的核心讨论对象，是否属于上述“重点关注”的范围内？如果不是，直接给0分。"""
},

    # ========== 四、算法突破 (大幅收紧) ==========
    {
        "name": "arXiv cs.CL·精选",
        "url": "http://export.arxiv.org/rss/cs.CL",
        "priority": "batch",
        "criteria": """只保留同时满足：
        1. 已被主流科技媒体/知乎大V解读过（标题匹配『解读』『通俗』等关键词）
        2. 讨论普通人能理解的应用（ChatGPT、翻译、教育等）
        3. 非纯数学、非纯理论证明
        否则直接0分。"""
    },
    {
        "name": "arXiv cs.LG·精选",
        "url": "http://export.arxiv.org/rss/cs.LG",
        "priority": "batch",
        "criteria": """只保留同时满足：
        1. 已被主流科技媒体/知乎大V解读过（标题匹配『解读』『通俗』等关键词）
        2. 讨论普通人能理解的应用（ChatGPT、翻译、教育等）
        3. 非纯数学、非纯理论证明
        否则直接0分。"""
    },

{
    "name": "The Verge Full Feed",
    "url": "https://www.theverge.com/rss/full.xml",
    "priority": "high",
    "criteria": """
    【重点关注 Priority Focus】
    - 全球科技巨头（Apple, Google, Meta, Microsoft, NVIDIA, AMD）的AI/算力战略动向、并购、投资、组织架构调整
    - AI芯片/硬件产业的竞争格局、供应链分析、技术标准博弈
    - 重大AI产品或服务发布背后的产业逻辑、商业模式分析
    - 科技政策（如AI监管、数据隐私法）对市场和企业的影响
    
    【可以接受 Acceptable】
    - 有深度产业分析的消费电子产品报道（非单纯评测）
    - 对科技行业有深远影响的技术趋势分析或评论文章
    - 知名科技公司创始人的深度访谈
    
    【严格排除 Strictly Exclude】
    - 纯消费电子产品评测、游戏新闻、娱乐内容、社会新闻
    - 短讯类快报、无深度分析的产品发布通稿
    """
},

{
    "name": "少数派",
    "url": "https://sspai.com/feed",
    "priority": "medium",
    "criteria": """
    【重点关注 Priority Focus】
    - AI驱动的新工具/软件如何重塑个人工作流、团队协作模式
    - 利用AI工具（如Copilot、Notion AI）提升生产力的实际案例
    - 知识管理、自动化流程与AI结合的深度方法论
    
    【可以接受 Acceptable】
    - 涉及AI应用的高效工具推荐（需有具体使用场景）
    - 对生产力影响显著的软件更新或新范式介绍
    - 个人/小团队通过AI工具提升竞争力的经验分享
    
    【严格排除 Strictly Exclude】
    - 纯硬件评测、无AI视角的应用技巧
    - 泛生活类内容、与生产力无关的消费推荐
    """
},

{
    "name": "TechCrunch",
    "url": "https://techcrunch.com/feed/",
    "priority": "high",
    "criteria": """
    【重点关注 Priority Focus】
    - AI, big data, cloud computing, semiconductor startups' funding, strategy, product launches
    - How startups leverage technology to disrupt traditional industries (finance, healthcare, manufacturing)
    - Investment trends in AI/compute sectors
    - Commercialization progress of emerging technologies (autonomous driving, robotics, spatial computing)
    
    【可以接受 Acceptable】
    - Analysis pieces on AI/tech market dynamics
    - Interviews with founders/VCs about tech trends
    - Reports on M&A activities with strategic implications
    
    【严格排除 Strictly Exclude】
    - Pure funding announcements without business logic analysis
    - Internet gossip, consumer electronics reviews
    - Short news without depth
    """
},

{
    "name": "OneV's Den",
    "url": "http://onevcat.com/feed.xml",
    "priority": "medium",
    "criteria": """
    【重点关注 Priority Focus】
    - AI辅助编程工具（Claude Code, Copilot）的深度使用体验
    - AI对开发者工作效率、软件工程流程的重塑
    - AI模型（如Foundation Models）在端侧应用的技术分析
    
    【可以接受 Acceptable】
    - 关于AI如何影响开发者决策、团队协作的反思
    - 编程语言/开发框架未来演变的AI视角思考
    - 具体详实的AI编程案例研究
    
    【严格排除 Strictly Exclude】
    - 纯iOS开发入门教程
    - 未结合AI视角的通用技术分享
    - 个人生活记录
    """
},

{
    "name": "Lifehacker",
    "url": "https://lifehacker.com/rss",
    "priority": "medium",
    "criteria": """
    【重点关注 Priority Focus】
    - 利用AI工具/自动化流程提升个人生活和工作效率的具体方法
    - AI在日常场景（写作、研究、规划、学习辅助）的落地应用
    - 关于数字生活方式的AI优化方案
    
    【可以接受 Acceptable】
    - 涉及AI的软件推荐和使用技巧
    - AI在家庭自动化、个人财务管理等场景的应用
    - 效率导向的科技产品推荐（需有AI视角）
    
    【严格排除 Strictly Exclude】
    - 纯生活窍门（无AI或数据驱动）
    - 非科技类的健康/饮食建议
    - 纯消费推荐而无效率视角
    """
},

    # ========== 新增：财富思维·中美精选 (2026.02.23) ==========
    {
    "name": "也谈钱",
    "url": "https://yetanmoney.com/feed.xml",
    "priority": "high",
    "criteria": """【核心定位】普通人财务自由实录 × 可复制的攒钱方法论
    【保留标准】一个普通上班族践行财务自由计划的真实记录。重点关注：具体如何存钱、如何记账、如何做副业、如何平衡消费与储蓄、心态起伏的真实记录。
    【特色】最接地气的财务自由实践者，他的困惑、尝试、成功和失败对大多数人有直接的参考价值。"""
},

{
    "name": "辉哥奇谭",
    "url": "https://wechat2rss.xlab.app/feed/901d558ca470febb48ce51c8cc2eb9a7.xml",
    "enabled": False,  # 2026-02-25 健康检查: 404
    "priority": "high",
    "criteria": """【核心定位】职业发展 × 财务思维 × 人生哲学
    【保留标准】关于职业选择、收入结构、人生规划的深度思考。重点关注：如何构建三份收入、职场跃迁策略、中年危机应对、认知升级。
    【特色】辉哥的思考体系完整，既有方法论又有实践案例，对个人成长极具启发性。"""
},

{
    "name": "caoz的梦呓",
    "url": "https://wechat2rss.xlab.app/feed/58484c9d2aa54d25b109ed8f65029f7e.xml",
    "enabled": False,  # 2026-02-25 健康检查: 404
    "priority": "high",
    "criteria": """【核心定位】商业逻辑 × 财富机会 × 认知升级
    【保留标准】对互联网商业、个人发展选择的犀利洞察。重点关注：行业红利期的判断、职场跃迁的底层逻辑、如何发现并抓住财富机会、信息差的运用。
    【特色】曹政老师是资深互联网人，说话直接、一针见血，擅长拆解商业现象背后的本质。"""
},

{
    "name": "孟岩",
    "url": "https://wechat2rss.xlab.app/feed/58484c9d2aa54d25b109ed8f65029f7e.xml",
    "enabled": False,  # 2026-02-25 健康检查: 404
    "priority": "high",
    "criteria": """【核心定位】投资哲学 × 内心秩序 × 幸福科学
    【保留标准】探讨投资与人生关系的深度文章。重点关注：对财富本质的反思、情绪与决策的关系、投资者心理建设、慢即是多的长期主义。
    【特色】作者是前基金公司高管，文风温柔但有力量，擅长将复杂的投资逻辑转化为人生智慧。"""
},

    {
        "name": "Mr. Money Mustache",
        "url": "https://feeds.feedburner.com/MrMoneyMustache",
        "priority": "high",
        "criteria": """【核心定位】FIRE运动鼻祖 × 生活方式革命 × 财富自由哲学
        【保留标准】通过改变生活方式和消费观实现财务独立的颠覆性思维。重点关注：如何计算真正的退休所需、消费主义陷阱拆解、高储蓄率的生活方式设计、快乐与支出的脱钩。
        【特色】美式极简主义的代表，文风幽默犀利，用数学和逻辑说服你：自由不是赚更多，而是需要更少。提供完全不同的财富视角。
        【排除】纯省钱技巧、不涉及思维转变的消费攻略。"""
    },
    {
        "name": "Farnam Street",
        "url": "https://fs.blog/feed/",
        "priority": "high",
        "criteria": """【核心定位】思维模型 × 决策科学 × 投资智慧
        【保留标准】提升认知水平和决策能力的深度内容。重点关注：顶级投资家的思维方式、如何避免认知偏误、第一性原理、复利思维在人生中的应用、跨学科智慧。
        【特色】这是六篇里最「硬核认知」的，不直接谈钱，而是教你如何像查理·芒格一样更好地思考。钱是正确决策的副产品。
        【排除】快餐式成功学、无理论支撑的个人观点。"""
    },
    {
        "name": "James Clear",
        "url": "https://jamesclear.com/feed",
        "priority": "medium",
        "criteria": """【核心定位】原子习惯 × 持续改进 × 行动科学
        【保留标准】关于如何建立好习惯、打破坏习惯、每天进步1%的系统方法。重点关注：行为改变的科学依据、习惯养成四步法、如何设计环境促使行动、身份认同与习惯的关系。
        【特色】《原子习惯》作者的博客，是六篇里最「行动导向」的。它解决的是「知道了道理但做不到」的问题，专注于如何把认知转化为持久的行动。
        【排除】纯励志口号、缺乏实操框架的理论。"""
    }
    # ========== 财富思维精选结束 ==========

]

# 将列表赋值完成
print(f"✅ 最终版 config.py 加载完成，共 {len(RSS_FEEDS)} 个订阅源。")
