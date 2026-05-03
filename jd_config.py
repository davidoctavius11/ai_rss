# jd_config.py — JD零售AI情报 source definitions
# Tier 1: 风向标 (smart money, best minds, policy)
# Tier 2: Confirmed signal (investigative, global retail, china ecom)
# Add new sources here; scorer picks them up automatically.

JD_SOURCES = [

    # ── Tier 1: Skin in the Game — Practitioners & Investors ────────────
    {
        "name": "jd-chip-huyen",
        "url": "https://huyenchip.com/feed.xml",
        "tier": 1,
        "category": "best_minds",
        "label": "Chip Huyen",
        "criteria": "全部保留 — ML系统工程、模型部署、实时推理，直接对标京东AI基础设施问题",
    },
    {
        "name": "jd-interconnects",
        "url": "https://www.interconnects.ai/feed",
        "tier": 1,
        "category": "best_minds",
        "label": "Nathan Lambert (Interconnects)",
        "criteria": "全部保留 — RLHF/模型训练实践者，对模型能力边界的判断是一线信号",
    },
    {
        "name": "jd-swyx",
        "url": "https://www.swyx.io/rss.xml",
        "tier": 1,
        "category": "best_minds",
        "label": "Swyx (AI Engineer)",
        "criteria": "保留技术驱动的产品与工程实践：AI工程、开发者工具、产品生态演变、市场格局判断；Swyx是'AI工程师'概念的缔造者，对新兴技术栈的采纳曲线判断极为精准；过滤纯个人随笔",
    },
    {
        "name": "jd-paul-graham",
        "url": "https://paulgraham.com/rss.html",
        "tier": 1,
        "category": "smart_money",
        "label": "Paul Graham",
        "criteria": "全部保留 — 低频极高信号，每篇都是下一代创始人思维的风向标",
    },
    {
        "name": "jd-benedict-evans",
        "url": "https://www.ben-evans.com/benedictevans?format=rss",
        "tier": 1,
        "category": "smart_money",
        "label": "Benedict Evans",
        "criteria": "全部保留 — 前a16z，最擅长分析技术转变对行业结构的影响，正是总裁级需要的视角",
    },
    {
        "name": "jd-tomasz-tunguz",
        "url": "https://tomtunguz.com/index.xml",
        "tier": 1,
        "category": "smart_money",
        "label": "Tomasz Tunguz (Theory Ventures)",
        "criteria": "保留任何技术（AI、基础设施、SaaS平台）驱动的企业采纳率数据、市场规模测算、投资决策依据；Tomasz Tunguz以数据驱动分析见长，是技术商业化曲线最权威的量化信源",
    },
    {
        "name": "jd-elad-gil",
        "url": "https://blog.eladgil.com/feed",
        "tier": 1,
        "category": "smart_money",
        "label": "Elad Gil",
        "criteria": "全部保留 — AI公司构建和市场格局分析，投资判断背后的真实逻辑",
    },
    {
        "name": "jd-nathan-benaich",
        "url": "https://nathanbenaich.substack.com/feed",
        "tier": 1,
        "category": "smart_money",
        "label": "Nathan Benaich (State of AI)",
        "criteria": "全部保留 — Air Street Capital，发布年度AI生态系统深度报告，生态竞争格局最权威来源之一",
    },
    {
        "name": "jd-fastai",
        "url": "https://www.fast.ai/index.xml",
        "tier": 1,
        "category": "best_minds",
        "label": "fast.ai (Jeremy Howard)",
        "criteria": "全部保留 — 真正的实践者视角，专门揭示哪些AI能力被高估、哪些被低估",
    },

    # ── Tier 1: Smart Money ──────────────────────────────────────────────
    {
        "name": "jd-36kr-funding",
        "url": "https://36kr.com/feed",          # rss.36kr.com DNS fails; main domain works
        "tier": 1,
        "category": "smart_money",
        "label": "36氪融资快讯",
        "criteria": "只保留融资、投资、并购相关内容，尤其是AI/电商/零售/物流方向；过滤产品功能更新、软文",
    },
    {
        "name": "jd-a16z",
        "url": "https://www.a16z.news/feed",     # redirected from a16z.com/feed/
        "tier": 1,
        "category": "smart_money",
        "label": "a16z Blog",
        "criteria": "保留产品与市场格局分析：AI应用、消费科技、企业软件、零售/电商/物流方向的投资论文；a16z的发文即下注声明，直接反映未来12-24个月哪些产品方向获得顶级资本背书；过滤纯技术科普",
    },

    # ── Tier 1: Best Minds ───────────────────────────────────────────────
    {
        "name": "jd-karpathy",
        "url": "https://karpathy.ai/feed.xml",
        "tier": 1,
        "category": "best_minds",
        "label": "Andrej Karpathy",
        "criteria": "全部保留 — 低频高信号，每篇均为行业frame-setting级别",
    },
    {
        "name": "jd-lillog",
        "url": "https://lilianweng.github.io/lil-log/feed.xml",  # fixed URL
        "tier": 1,
        "category": "best_minds",
        "label": "Lil'Log (Lilian Weng)",
        "criteria": "全部保留 — OpenAI研究主管，内容为综述级别，直接影响业界技术方向",
    },
    {
        "name": "jd-eugeneyan",
        "url": "https://eugeneyan.com/rss/",     # fixed: rss/ not feed.xml
        "tier": 1,
        "category": "best_minds",
        "label": "Eugene Yan (RecSys)",
        "criteria": "全部保留 — 专注推荐系统/搜索/LLM应用，与京东核心AI技术直接相关",
    },
    {
        "name": "jd-import-ai",
        "url": "https://jack-clark.net/feed/",
        "tier": 1,
        "category": "best_minds",
        "label": "Import AI (Jack Clark)",
        "criteria": "全部保留 — Jack Clark已完成一次高质量筛选，打分聚焦京东相关性即可",
    },
    {
        "name": "jd-qwenlm",
        "url": "https://qwenlm.github.io/blog/index.xml",
        "tier": 1,
        "category": "best_minds",
        "label": "QwenLM (Alibaba AI)",
        "criteria": "全部保留 — 阿里LLM团队发布=直接竞对R&D信号",
    },
    {
        "name": "jd-arxiv-ir",
        "url": "http://export.arxiv.org/rss/cs.IR",
        "tier": 2,
        "category": "best_minds",
        "label": "arXiv cs.IR",
        "is_arxiv": True,
        "criteria": "【优先级大幅降低：算法团队已独立跟进】仅保留同时满足以下两个条件的论文：①作者来自顶级机构（Google/Meta/Alibaba/顶级高校等）；②有明确产业落地证据（工业界数据集、真实系统部署描述、开源且有大量star）。纯学术改进、只用公开benchmark的论文直接过滤",
    },
    {
        "name": "jd-arxiv-lg",
        "url": "http://export.arxiv.org/rss/cs.LG",
        "tier": 2,
        "category": "best_minds",
        "label": "arXiv cs.LG",
        "is_arxiv": True,
        "criteria": "【优先级大幅降低：算法团队已独立跟进】仅保留同时满足以下两个条件的论文：①作者来自顶级机构；②有直接产品/商业应用价值的落地描述（不是'可以应用于'的推测，而是'我们在X系统中部署了'的实证）。过滤一切纯理论推导、仅benchmark对比的论文",
    },
    {
        "name": "jd-the-gradient",
        "url": "https://thegradient.pub/rss/",
        "tier": 1,
        "category": "best_minds",
        "label": "The Gradient",
        "criteria": "保留技术转变对产业结构影响的深度分析：AI能力边界、系统设计决策、从研究到产品的路径；过滤无产品路径的纯学术综述",
    },

    # ── Tier 1: Chinese AI Ecosystem (accessible without RSSHub) ────────
    {
        "name": "jd-mittr-china",
        "url": "https://www.mittrchina.com/feed",
        "tier": 1,
        "category": "best_minds",
        "label": "MIT科技评论中文版",
        "criteria": "保留中国科技产业的深度分析：技术趋势对商业格局的影响、中国AI生态演变、监管政策与产业创新的互动；不限AI，凡涉及产业结构性变化的深度报道均保留；过滤纯科普入门",
    },
    {
        "name": "jd-synced",
        "url": "https://syncedreview.com/feed/",
        "tier": 1,
        "category": "best_minds",
        "label": "Synced (机器之心英文版)",
        "criteria": "保留中国AI/科技生态的英文视角：机构成果、中美技术竞争、模型商业化评测；该信源为国际受众提供中国科技独家视角，信号密度高；过滤纯技术教程",
    },
    {
        "name": "jd-36kr-ai",
        "url": "https://36kr.com/information/AI/feed",
        "tier": 2,
        "category": "investigative",
        "label": "36氪AI专题",
        "criteria": "保留科技驱动的产品创新与商业化案例：AI落地、新商业模式、创业公司融资战略；核心是「技术如何改变产品和市场」而非AI本身；过滤纯技术科普和软文",
    },
    {
        "name": "jd-leiphone",
        "url": "https://www.leiphone.com/feed",
        "tier": 2,
        "category": "investigative",
        "label": "雷锋网",
        "criteria": "保留技术在产业的落地报道：零售科技、机器人商业化、自动化物流、大模型产品化；核心信号是「哪家公司用什么技术解决了什么产业问题」",
    },

    # ── Tier 2: Investigative / China ───────────────────────────────────
    {
        "name": "jd-huxiu",
        "url": "https://www.huxiu.com/rss/",     # RSS removed by huxiu — consistently 404/502; keeping entry for manual paste
        "tier": 2,
        "category": "investigative",
        "label": "虎嗅",
        "criteria": "保留中国科技/电商公司的商业模式创新、竞对战略动态、产业变革深度分析；虎嗅擅长从商业逻辑角度拆解科技公司决策，不限于AI",
    },
    {
        "name": "jd-pingwest",
        "url": "https://www.pingwest.com/feed",
        "tier": 2,
        "category": "investigative",
        "label": "品玩PingWest",
        "criteria": "保留国内科技公司的产品创新与战略动态；关注商业模式变化、新产品类别出现、竞争格局演变；过滤消费电子纯评测、游戏娱乐内容",
    },
    {
        "name": "jd-36kr",
        "url": "https://www.36kr.com/feed",
        "tier": 2,
        "category": "investigative",
        "label": "36氪",
        "criteria": "保留中国科技/电商公司的产品创新、战略动态、商业模式变化；重点关注竞对（阿里/PDD/抖音/字节）的产品新动作和市场策略；不限AI，凡涉及技术驱动的商业变化均保留",
    },
    {
        "name": "jd-36kr-global",
        "url": "https://36kr.com/feed",           # fallback to main feed
        "tier": 2,
        "category": "china_ecom",
        "label": "36氪出海",
        "criteria": "保留中国企业出海的产品策略、市场进入方式、竞争格局；不限AI，凡涉及技术或产品创新驱动的出海动态均保留",
    },
    {
        "name": "jd-ebrun",
        "url": "https://www.ebrun.com/feed/",     # RSS broken — consistently 404; keeping for manual paste
        "tier": 2,
        "category": "china_ecom",
        "label": "亿邦动力",
        "criteria": "保留中国电商行业的产品创新、平台政策变化、商业模式演变；核心是技术和产品如何改变电商竞争格局",
    },

    # ── Tier 2: Global Retail AI ─────────────────────────────────────────
    {
        "name": "jd-modern-retail",
        "url": "https://www.modernretail.co/feed/",
        "tier": 2,
        "category": "global_retail",
        "label": "Modern Retail",
        "criteria": "保留零售科技的产品创新：个性化、搜索、定价算法、供应链技术、全渠道融合的新实践；不限AI，凡零售商用技术解决问题的案例均有价值；过滤纯品牌营销和时尚内容",
    },
    {
        "name": "jd-digital-commerce",
        "url": "https://www.digitalcommerce360.com/feed/",
        "tier": 2,
        "category": "global_retail",
        "label": "Digital Commerce 360",
        "criteria": "保留电商技术实践：转化优化、自动化、个性化、定价策略、平台功能演变；重点是「技术如何提升商业指标」的实证案例",
    },
    {
        "name": "jd-retail-dive",
        "url": "https://www.retaildive.com/feeds/news/",
        "tier": 2,
        "category": "global_retail",
        "label": "Retail Dive",
        "criteria": "保留大型零售商的技术战略与竞争动态：Amazon/Walmart/Target的产品决策、技术投资方向、市场份额变化；不限AI，任何tech-driven的战略调整均是信号",
    },
    {
        "name": "jd-amazon-science",
        "url": "https://www.amazon.science/index.rss",   # fixed URL
        "tier": 2,
        "category": "global_retail",
        "label": "Amazon Science",
        "criteria": "全部保留 — Amazon一级信源，搜索/推荐/物流AI研究直接可对标京东",
    },
    {
        "name": "jd-walmart-tech",
        "url": "https://medium.com/feed/walmartglobaltech",
        "tier": 2,
        "category": "global_retail",
        "label": "Walmart Global Tech",
        "criteria": "全部保留 — Walmart技术团队一级信源，AI应用直接可对标",
    },
    {
        "name": "jd-shopify",
        "url": "https://www.shopify.com/news/feed",      # fixed URL
        "tier": 2,
        "category": "global_retail",
        "label": "Shopify Blog",
        "criteria": "保留商家工具创新、平台新功能、技术生态变化；Shopify的每次产品发布都是中小商家采用什么技术的领先指标；过滤营销成功案例和节日促销",
    },
    {
        "name": "jd-practical-ecom",
        "url": "https://www.practicalecommerce.com/feed",
        "tier": 2,
        "category": "global_retail",
        "label": "Practical Ecommerce",
        "criteria": "保留电商从业者实际使用的工具评测、自动化技术、平台功能变化；重点是实操层面的产品创新和效率提升",
    },

    # ── Tier 2: O2O / 本地生活 ───────────────────────────────────────────
    {
        "name": "jd-instacart-tech",
        "url": "https://tech.instacart.com/feed",
        "tier": 2,
        "category": "global_retail",
        "label": "Instacart Tech",
        "criteria": "全部保留 — 即时配送+AI推荐，与本地生活/O2O场景高度对标，含搜索/个性化/履约AI",
    },
    {
        "name": "jd-grab-engineering",
        "url": "https://engineering.grab.com/feed.xml",
        "tier": 1,
        "category": "best_minds",
        "label": "Grab Engineering",
        "criteria": "只保留推荐系统、配送调度AI、动态定价、东南亚电商技术内容；过滤纯后端运维",
    },

    # ── Tier 2: 国际业务 / Southeast Asia ───────────────────────────────
    {
        "name": "jd-techinasia",
        "url": "https://www.techinasia.com/feed",
        "tier": 2,
        "category": "global_retail",
        "label": "Tech in Asia",
        "criteria": "保留东南亚科技创业、中国出海企业动态、亚洲电商/物流/金融科技融资；全英文覆盖亚洲市场最全面",
    },
    {
        "name": "jd-krasia",
        "url": "https://kr-asia.com/feed",
        "tier": 2,
        "category": "global_retail",
        "label": "KrAsia",
        "criteria": "只保留东南亚/中国科技公司出海动态、电商AI、海外零售投资内容；过滤纯金融/政治",
    },
    {
        "name": "jd-shopee-blog",
        "url": "https://shopee.sg/blog/feed/",
        "tier": 2,
        "category": "global_retail",
        "label": "Shopee Blog",
        "criteria": "全部保留 — 东南亚最大电商平台，AI/推荐/物流技术直接对标京东国际",
    },

    # ── Tier 2: 财经 / Fintech ───────────────────────────────────────────
    {
        "name": "jd-finextra",
        "url": "https://www.finextra.com/rss/channel.aspx?channel=news",
        "tier": 2,
        "category": "global_retail",
        "label": "Finextra",
        "criteria": "只保留AI在金融风控、信贷决策、支付AI、反欺诈领域的技术动态；过滤纯监管合规",
    },
    {
        "name": "jd-pymnts",
        "url": "https://www.pymnts.com/feed/",
        "tier": 2,
        "category": "global_retail",
        "label": "PYMNTS",
        "criteria": "只保留支付AI、消费者信贷、BNPL技术、零售金融科技动态；过滤纯政策/监管",
    },

    # ── Tier 2: 效能与中间件 / Developer AI ─────────────────────────────
    {
        "name": "jd-github-blog",
        "url": "https://github.blog/feed/",
        "tier": 2,
        "category": "best_minds",
        "label": "GitHub Blog",
        "criteria": "保留开发者工具创新、编程效能突破、开源生态演变；GitHub代表全球最大开发者社区的行为数据，其产品方向即未来软件生产方式的预告；过滤社区活动和纯通知",
    },

    # ── Tier 2: 数据计算 ──────────────────────────────────────────────────
    {
        "name": "jd-databricks",
        "url": "https://www.databricks.com/feed",
        "tier": 2,
        "category": "best_minds",
        "label": "Databricks Blog",
        "criteria": "保留数据平台与AI基础设施的创新：LLM+数仓融合、实时ML、特征工程、大规模训练；Databricks的技术路线代表未来2年数据平台标准；过滤纯产品营销",
    },

    # ── Tier 2: 安全风控 ──────────────────────────────────────────────────
    {
        "name": "jd-google-security",
        "url": "http://feeds.feedburner.com/GoogleOnlineSecurityBlog",
        "tier": 2,
        "category": "best_minds",
        "label": "Google Security Blog",
        "criteria": "只保留AI安全、欺诈检测、对抗攻击防御、账号安全技术内容；过滤纯密码学/基础设施安全",
    },
    {
        "name": "jd-cloudflare-security",
        "url": "https://blog.cloudflare.com/tag/security/rss/",
        "tier": 2,
        "category": "best_minds",
        "label": "Cloudflare Security",
        "criteria": "只保留Bot检测、AI流量识别、爬虫对抗、DDoS防护技术；直接对标京东安全风控场景",
    },

    # ── Official AI Lab Blogs ─────────────────────────────────────────────
    {
        "name": "jd-openai-blog",
        "url": "https://openai.com/news/rss.xml",
        "tier": 1,
        "category": "best_minds",
        "label": "OpenAI Blog",
        "criteria": "全部保留 — OpenAI官方发布的模型更新、产品发布、安全研究、商业合作，均为一手信号",
    },
    # Anthropic has no public RSS feed — covered via TechCrunch AI + The Verge AI
    {
        "name": "jd-deepmind-blog",
        "url": "https://deepmind.google/blog/rss.xml",
        "tier": 1,
        "category": "best_minds",
        "label": "Google DeepMind Blog",
        "criteria": "全部保留 — DeepMind/Google官方研究成果，含Gemini系列、具身智能、多模态突破",
    },
    {
        "name": "jd-meta-engineering",
        "url": "https://engineering.fb.com/feed/",
        "tier": 1,
        "category": "best_minds",
        "label": "Meta Engineering Blog",
        "criteria": "全部保留 — Meta/Facebook官方工程博客，含Llama、推荐系统、内容理解、基础设施",
    },

    # ── Mainstream Tech News (AI-focused feeds) ───────────────────────────
    {
        "name": "jd-techcrunch-ai",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "tier": 2,
        "category": "best_minds",
        "label": "TechCrunch AI",
        "criteria": "保留技术驱动的产品发布、创业公司融资、大厂战略信号；重点是「谁在用什么技术做什么新产品」的第一手报道；过滤纯教程和无实质内容的新闻跟进",
    },
    {
        "name": "jd-verge-ai",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "tier": 2,
        "category": "best_minds",
        "label": "The Verge · AI",
        "criteria": "保留消费级科技产品的创新动态：大厂产品发布、用户行为改变、技术商业化信号、监管政策；The Verge代表科技早期采纳者的视角，是消费级产品趋势最准确的风向标",
    },
    {
        "name": "jd-venturebeat-ai",
        "url": "https://venturebeat.com/category/ai/feed/",
        "tier": 2,
        "category": "best_minds",
        "label": "VentureBeat AI",
        "criteria": "保留企业科技的产品创新：AI落地案例、新平台工具发布、企业采纳数据、竞争格局变化；重点是企业用技术创造新商业价值的实证；过滤无实质内容的新闻转载",
    },
    {
        "name": "jd-mit-tech-review",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
        "tier": 2,
        "category": "best_minds",
        "label": "MIT Technology Review · AI",
        "criteria": "全部保留 — MIT权威AI深度报道，覆盖技术趋势、监管、社会影响；质量高、噪音低",
    },
    {
        "name": "jd-stratechery",
        "url": "https://stratechery.com/feed/",
        "tier": 1,
        "category": "best_minds",
        "label": "Stratechery (Ben Thompson)",
        "criteria": "全部保留 — Ben Thompson对科技商业战略的深度分析，大厂竞争/平台战略/AI商业化必读",
    },

    # ── Chinese AI Specialized Media ──────────────────────────────────────
    # 量子位 (Qbitai) blocks RSS requests with 403 — covered via 36kr/leiphone/huxiu
    # 机器之心 (Jiqizhixin) has no working RSS feed — covered via Synced (English version)
    # ByteDance/TikTok Engineering has no public RSS feed
    # Taobao Tech (tech.taobao.org) is unreachable externally
    # BAAI Hub and HuggingFace Papers have no RSS endpoints

    # ── Chinese Tech Company Engineering Blogs ────────────────────────────
    {
        "name": "jd-meituan-tech",
        "url": "https://tech.meituan.com/feed",
        "tier": 2,
        "category": "best_minds",
        "label": "美团技术团队",
        "criteria": "全部保留 — 美团技术博客，直接竞对，含推荐系统、配送调度、LLM工程实践",
    },

    # ── AI Platform & Cloud Engineering Blogs ────────────────────────────
    {
        "name": "jd-google-ai-blog",
        "url": "https://blog.google/technology/ai/rss/",
        "tier": 1,
        "category": "best_minds",
        "label": "Google AI Blog",
        "criteria": "全部保留 — Google官方AI博客，含Gemini/Search AI/广告AI产品发布，直接竞对信号",
    },
    {
        "name": "jd-microsoft-research",
        "url": "https://www.microsoft.com/en-us/research/feed/",
        "tier": 1,
        "category": "best_minds",
        "label": "Microsoft Research Blog",
        "criteria": "保留AI基础研究、Copilot系列、Azure AI能力；过滤纯学术无应用价值内容",
    },
    {
        "name": "jd-aws-aiml",
        "url": "https://aws.amazon.com/blogs/machine-learning/feed/",
        "tier": 2,
        "category": "best_minds",
        "label": "AWS Machine Learning Blog",
        "criteria": "保留推荐系统、搜索、MLOps、大模型部署实践；Amazon技术博客直接对标京东AI Infra",
    },
    {
        "name": "jd-nvidia-developer",
        "url": "https://developer.nvidia.com/blog/feed/",
        "tier": 2,
        "category": "best_minds",
        "label": "NVIDIA Developer Blog",
        "criteria": "保留推理优化、训练加速、多模态模型、具身智能；过滤纯硬件规格内容",
    },
    {
        "name": "jd-huggingface-blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "tier": 1,
        "category": "best_minds",
        "label": "Hugging Face Blog",
        "criteria": "全部保留 — 开源AI生态的第一手发布平台；每篇文章代表开发者社区对某个AI能力的实际采纳，是产品应用哪些AI能力的最直接信号",
    },

    # ── Venture Capital & Smart Money ─────────────────────────────────────
    {
        "name": "jd-sequoia",
        "url": "https://www.sequoiacap.com/feed/",
        "tier": 1,
        "category": "smart_money",
        "label": "Sequoia Capital",
        "criteria": "全部保留 — 红杉资本投资方向即市场方向，每篇均为smart money信号",
    },
    {
        "name": "jd-lightspeed",
        "url": "https://lsvp.com/feed/",
        "tier": 1,
        "category": "smart_money",
        "label": "Lightspeed Venture",
        "criteria": "全部保留 — Lightspeed在AI/消费/企业SaaS的投资判断；中国、印度、美国均有覆盖",
    },
    {
        "name": "jd-ycombinator",
        "url": "https://www.ycombinator.com/blog/rss",
        "tier": 1,
        "category": "smart_money",
        "label": "Y Combinator Blog",
        "criteria": "全部保留 — YC批次公司即下一代产品方向预览；Request for Startups直接反映市场需求缺口",
    },

    # ── English-language Tech & Business Media ────────────────────────────
    {
        "name": "jd-platformer",
        "url": "https://www.platformer.news/feed",
        "tier": 1,
        "category": "best_minds",
        "label": "Platformer (Casey Newton)",
        "criteria": "全部保留 — 顶级科技记者Casey Newton的独家报道，大厂内幕/AI政策/产品战略最快披露",
    },
    {
        "name": "jd-wired",
        "url": "https://www.wired.com/feed/rss",
        "tier": 2,
        "category": "best_minds",
        "label": "Wired",
        "criteria": "保留技术对社会和商业的深层影响：消费者行为改变、新产品类别形成、科技监管趋势；Wired擅长捕捉技术趋势从边缘到主流的拐点信号；过滤文化艺术、纯科学和硬件评测",
    },
    {
        "name": "jd-fastcompany-design",
        "url": "https://www.fastcompany.com/co-design/rss",
        "tier": 1,
        "category": "product_innovation",
        "label": "Fast Company · Design",
        "criteria": "聚焦产品设计创新与用户体验突破：保留AI驱动的新交互模式、消费级产品设计范式转变、零售/电商UX创新案例、设计思维方法论落地；重点关注'别人还没做但12个月后会成标配'的产品创新信号；过滤纯视觉美学、艺术装置、品牌VI等与产品功能无关内容",
    },
    {
        "name": "jd-fastcompany-tech",
        "url": "https://www.fastcompany.com/technology/rss",
        "tier": 1,
        "category": "product_innovation",
        "label": "Fast Company · Technology",
        "criteria": "聚焦技术驱动的产品创新：保留新兴消费级AI应用、商业模式创新、用户行为研究洞察、科技公司产品战略转变；特别关注Fast Company年度'最具创新力公司'和'Innovation by Design'奖项相关报道；过滤纯技术研发、融资PR、政治监管等",
    },
    {
        "name": "jd-bof",
        "url": "https://www.businessoffashion.com/arc/outboundfeeds/rss/",
        "tier": 1,
        "category": "product_innovation",
        "label": "Business of Fashion",
        "criteria": "聚焦时尚零售×科技的产品创新：保留AI试穿/虚拟试衣、个性化推荐新范式、直播电商模式创新、供应链柔性化、消费者行为转变（特别是Z世代购物决策路径）、奢侈品数字化案例；这些是京东服饰/美妆品类12-24个月内的产品参照系；过滤纯时装周报道、品牌公关、明星代言",
    },
    {
        "name": "jd-bloomberg-businessweek",
        "url": "https://feeds.bloomberg.com/businessweek/news.rss",
        "tier": 1,
        "category": "product_innovation",
        "label": "Bloomberg Businessweek",
        "criteria": "聚焦商业模式创新与消费者行为研究：保留企业产品战略深度报道、消费者行为转变的数据分析、零售/电商行业结构性变化、AI商业化落地的真实案例；Bloomberg Businessweek的价值在于独家访谈和深度调查，能揭示公司内部产品决策逻辑；过滤宏观经济、政治、纯金融市场内容",
    },
    {
        "name": "jd-acm-interactions",
        "url": "https://dl.acm.org/action/showFeed?type=etoc&feed=rss&jc=interactions",
        "tier": 1,
        "category": "product_innovation",
        "label": "ACM Interactions · HCI",
        "criteria": "聚焦人机交互研究中的产品创新信号：保留AI界面设计新范式、对话式UI/多模态交互研究、用户认知与决策行为研究、电商场景下的交互创新（搜索/推荐/结账流程）；ACM Interactions是学术HCI研究转化为产品设计的最短路径，今天的论文就是18个月后的产品标配；过滤纯算法研究、数学推导、非产品化的基础科学",
    },
    {
        "name": "jd-bloomberg-tech",
        "url": "https://feeds.bloomberg.com/technology/news.rss",
        "tier": 2,
        "category": "best_minds",
        "label": "Bloomberg Technology",
        "criteria": "保留大厂的战略决策与财报信号：技术投资方向、并购逻辑、监管政策对产品的影响；不限AI，任何影响科技公司竞争格局的重大动作均保留；过滤纯硬件评测",
    },
    {
        "name": "jd-crunchbase-news",
        "url": "https://news.crunchbase.com/feed/",
        "tier": 2,
        "category": "smart_money",
        "label": "Crunchbase News",
        "criteria": "保留AI/电商/零售/物流/金融科技领域融资事件；资本流向是技术方向最领先的指标",
    },
    {
        "name": "jd-restofworld",
        "url": "https://restofworld.org/feed/",
        "tier": 2,
        "category": "best_minds",
        "label": "Rest of World",
        "criteria": "保留东南亚/印度/中国科技公司海外动态、新兴市场AI应用；直接对标京东国际业务",
    },

    # ── China-Focused English Media ───────────────────────────────────────
    {
        "name": "jd-technode",
        "url": "https://technode.com/feed/",
        "tier": 2,
        "category": "china_ecom",
        "label": "TechNode",
        "criteria": "全部保留 — 最权威的中国科技英文媒体，覆盖中国AI公司动态、政策监管、出海战略",
    },
    {
        "name": "jd-pandaily",
        "url": "https://pandaily.com/feed/",
        "tier": 2,
        "category": "china_ecom",
        "label": "Pandaily",
        "criteria": "保留中国大厂AI产品发布、出海动态、融资事件；有时比36kr更快报道中国科技英文版",
    },
    {
        "name": "jd-alizila",
        "url": "https://www.alizila.com/feed/",
        "tier": 2,
        "category": "china_ecom",
        "label": "Alizila (阿里巴巴官方英文)",
        "criteria": "全部保留 — 阿里巴巴官方英文新闻，竞对一手信号：淘宝/天猫/菜鸟/达摩院产品发布",
    },
    {
        "name": "jd-scmp-tech",
        "url": "https://www.scmp.com/rss/5/feed",
        "tier": 2,
        "category": "china_ecom",
        "label": "South China Morning Post · Tech",
        "criteria": "保留中国AI政策、科技公司战略、中美科技竞争动态；过滤港台政治内容",
    },

    # ── 政策监管 (Policy & Regulatory) ────────────────────────────────────
    {
        "name": "jd-eu-digital",
        "url": "https://digital-strategy.ec.europa.eu/en/rss.xml",
        "tier": 1,
        "category": "policy",
        "label": "EU Digital Strategy",
        "criteria": "保留AI监管法案、数字市场法、平台合规政策；欧盟监管往往领先其他地区2-3年",
    },
    {
        "name": "jd-eu-ai-act",
        "url": "https://artificialintelligenceact.eu/feed/",
        "tier": 1,
        "category": "policy",
        "label": "EU AI Act Tracker",
        "criteria": "专门跟踪欧盟AI法案立法进展、合规要求、高风险AI分类；直接影响京东欧洲业务和全球AI产品设计",
    },
    {
        "name": "jd-ftc-tech",
        "url": "https://www.ftc.gov/feeds/press-release-consumer-protection.xml",
        "tier": 1,
        "category": "policy",
        "label": "FTC Technology",
        "criteria": "保留AI监管执法、算法歧视、消费者数据保护、平台反垄断；美国监管动向影响全球科技公司战略",
    },
    {
        "name": "jd-nist-ai",
        "url": "https://www.nist.gov/news-events/news/rss.xml",
        "tier": 1,
        "category": "policy",
        "label": "NIST AI",
        "criteria": "保留AI风险管理框架(AI RMF)更新、AI安全测评标准、可信AI技术指南；NIST标准往往成为行业基线",
    },

    # ── 物流与供应链 ──────────────────────────────────────────────────────
    {
        "name": "jd-freightwaves",
        "url": "https://www.freightwaves.com/news/feed",
        "tier": 2,
        "category": "industry",
        "label": "FreightWaves",
        "criteria": "保留货运市场实时动态、AI运价预测、跨境物流技术、最后一公里创新；直接对标京东物流运营",
    },
    {
        "name": "jd-loadstar",
        "url": "https://theloadstar.com/feed/",
        "tier": 2,
        "category": "industry",
        "label": "The Loadstar",
        "criteria": "保留海运/航空货运市场分析、全球供应链风险、港口自动化、跨境物流平台动态",
    },
    {
        "name": "jd-supply-chain-dive",
        "url": "https://www.supplychaindive.com/feeds/news/",
        "tier": 2,
        "category": "industry",
        "label": "Supply Chain Dive",
        "criteria": "保留仓储自动化、最后一公里、跨境物流、逆向物流、AI路由优化；直接对标京东物流",
    },
    {
        "name": "jd-logistics-viewpoints",
        "url": "https://logisticsviewpoints.com/feed/",
        "tier": 2,
        "category": "industry",
        "label": "Logistics Viewpoints",
        "criteria": "保留WMS/TMS架构、AMR仓储机器人、AI需求预测、履约网络设计；深度分析优先于新闻",
    },
    {
        "name": "jd-dc-velocity",
        "url": "https://www.dcvelocity.com/rss",
        "tier": 2,
        "category": "industry",
        "label": "DC Velocity",
        "criteria": "保留配送中心自动化、AGV/AMR部署、冷链技术、人形机器人仓储应用",
    },

    # ── 具身智能与机器人 ──────────────────────────────────────────────────
    {
        "name": "jd-the-robot-report",
        "url": "https://www.therobotreport.com/feed/",
        "tier": 2,
        "category": "industry",
        "label": "The Robot Report",
        "criteria": "保留AMR/人形机器人商业部署、仓储机器人竞品动态、ROS2技术、具身AI进展",
    },
    {
        "name": "jd-ieee-spectrum-robotics",
        "url": "https://spectrum.ieee.org/feeds/topic/robotics.rss",
        "tier": 1,
        "category": "best_minds",
        "label": "IEEE Spectrum Robotics",
        "criteria": "保留VLA模型、物理AI、机器人感知规划执行；是学术界和工业界的桥梁，信号质量极高",
    },

    # ── 能源与可持续发展 ──────────────────────────────────────────────────
    {
        "name": "jd-cleantechnica",
        "url": "https://cleantechnica.com/feed/",
        "tier": 2,
        "category": "industry",
        "label": "CleanTechnica",
        "criteria": "保留EV充电网络、电池技术、清洁能源AI应用；过滤纯政策倡导和重复新闻",
    },
    {
        "name": "jd-carbon-brief",
        "url": "https://www.carbonbrief.org/feed/",
        "tier": 2,
        "category": "industry",
        "label": "Carbon Brief",
        "criteria": "保留碳核算方法论、Scope 3数据、GHG Protocol更新；直接影响京东供应链碳足迹测量",
    },
    {
        "name": "jd-trellis",
        "url": "https://trellis.net/feed/",
        "tier": 2,
        "category": "industry",
        "label": "Trellis (GreenBiz)",
        "criteria": "保留企业ESG数据平台、循环经济、智能建筑节能、可持续供应链；过滤纯政策倡导",
    },

    # ── 医疗健康 ──────────────────────────────────────────────────────────
    {
        "name": "jd-stat-health-tech",
        "url": "https://www.statnews.com/category/health-tech/feed",
        "tier": 1,
        "category": "industry",
        "label": "STAT Health Tech",
        "criteria": "保留FDA AI审批、LLM医疗诊断、AI医疗影像、数字健康平台；直接对标京东健康AI能力建设",
    },
    {
        "name": "jd-medcity-news",
        "url": "https://medcitynews.com/feed/",
        "tier": 2,
        "category": "industry",
        "label": "MedCity News",
        "criteria": "保留数字健康融资、AI诊断产品、患者体验设计、健康数据平台；过滤非技术医疗政策",
    },

    # ── 内容直播 / 社交社区 ───────────────────────────────────────────────
    {
        "name": "jd-digiday",
        "url": "https://digiday.com/feed/",
        "tier": 2,
        "category": "industry",
        "label": "Digiday",
        "criteria": "保留内容电商、直播带货、程序化广告、媒体+零售融合趋势；覆盖品牌直播技术和社媒电商演变",
    },
    {
        "name": "jd-naavik",
        "url": "https://naavik.co/digest/feed/",
        "tier": 2,
        "category": "industry",
        "label": "Naavik Digest",
        "criteria": "保留游戏社交机制、社区运营、直播互动、虚拟经济模型；游戏化电商和社交购物场景直接参考",
    },
    {
        "name": "jd-woshipm",
        "url": "https://www.woshipm.com/feed",
        "tier": 2,
        "category": "industry",
        "label": "人人都是产品经理",
        "criteria": "保留国内产品经理的实战方法论：用户增长、产品架构决策、AI产品设计、竞品分析框架；核心价值是国内产品思维的第一手总结，往往比媒体报道早6个月发现产品趋势",
    },

    # ── 广告营销 ──────────────────────────────────────────────────────────
    {
        "name": "jd-adexchanger",
        "url": "https://www.adexchanger.com/feed/",
        "tier": 1,
        "category": "industry",
        "label": "AdExchanger",
        "criteria": "保留程序化广告、Clean Room、AI竞价、隐私计算广告、归因模型；直接对标京东广告业务",
    },

    # ── 交互设计 × 全领域 ─────────────────────────────────────────────────
    {
        "name": "jd-nngroup",
        "url": "https://www.nngroup.com/feed/rss/",
        "tier": 1,
        "category": "best_minds",
        "label": "Nielsen Norman Group",
        "criteria": "保留AI UX研究、转化设计、多模态交互、用户研究方法论；NNG是UX领域最高信源",
    },
    {
        "name": "jd-ux-collective",
        "url": "https://uxdesign.cc/feed",
        "tier": 2,
        "category": "industry",
        "label": "UX Collective",
        "criteria": "保留AI产品交互设计、用户旅程、无障碍设计、转化优化实践；过滤纯视觉审美类",
    },
    {
        "name": "jd-smashing-magazine",
        "url": "https://www.smashingmagazine.com/feed/",
        "tier": 2,
        "category": "industry",
        "label": "Smashing Magazine",
        "criteria": "保留AI辅助设计系统、跨平台UX、端侧交互性能；过滤纯CSS/HTML基础教程",
    },

    # ── 基础效能 × 全领域 ─────────────────────────────────────────────────
    {
        "name": "jd-sre-weekly",
        "url": "https://sreweekly.com/feed/",
        "tier": 1,
        "category": "best_minds",
        "label": "SRE Weekly",
        "criteria": "保留AI辅助故障响应、异常检测、混沌工程、可观测性平台；SRE社区最高质量精选通讯",
    },
    {
        "name": "jd-infoq",
        "url": "https://www.infoq.com/feed/",
        "tier": 2,
        "category": "industry",
        "label": "InfoQ",
        "criteria": "保留MLOps实践、分布式系统、数据基础设施、AI编程效能；过滤基础入门教程",
    },

    # ── 基础通讯 ──────────────────────────────────────────────────────────
    {
        "name": "jd-rcr-wireless",
        "url": "https://www.rcrwireless.com/feed",
        "tier": 2,
        "category": "industry",
        "label": "RCR Wireless News",
        "criteria": "保留私有5G部署、AI-RAN、边缘计算、网络切片；关注仓储/物流场景的工业IoT网络应用",
    },

    # ── 汽车与出行服务 ────────────────────────────────────────────────────
    {
        "name": "jd-electrek",
        "url": "https://electrek.co/feed/",
        "tier": 2,
        "category": "industry",
        "label": "Electrek",
        "criteria": "保留充电网络基础设施、车载AI OS、EV平台商业模式、自动驾驶商业化；过滤纯车型评测",
    },

    # ── 金融与支付 ────────────────────────────────────────────────────────
    {
        "name": "jd-payments-dive",
        "url": "https://www.paymentsdive.com/feeds/news/",
        "tier": 1,
        "category": "industry",
        "label": "Payments Dive",
        "criteria": "核心信源：保留一切涉及结算基础设施竞争的内容——VISA/MC interchange费率争议、FedNow实时支付轨道、A2A账户直连支付、开放银行对卡组织的冲击；过滤纯零售促销新闻",
    },
    {
        "name": "jd-digital-transactions",
        "url": "https://www.digitaltransactions.net/feed/",
        "tier": 2,
        "category": "industry",
        "label": "Digital Transactions",
        "criteria": "保留interchange经济学分析、支付网络竞争格局（VISA/MC vs 新兴轨道）、商户手续费监管动向；专注支付产业链收益分配视角",
    },
    {
        "name": "jd-atlantic-council-cbdc",
        "url": "https://www.atlanticcouncil.org/category/issue/digital-currencies/feed/",
        "tier": 1,
        "category": "policy",
        "label": "Atlantic Council CBDC",
        "criteria": "保留全球CBDC进展（数字人民币/数字欧元/Fed CBDC）、稳定币作为结算层的监管框架、跨境支付主权竞争；Atlantic Council CBDC Tracker是全球被引最多的CBDC数据源",
    },
    {
        "name": "jd-coin-center",
        "url": "https://www.coincenter.org/feed/",
        "tier": 2,
        "category": "policy",
        "label": "Coin Center",
        "criteria": "保留稳定币作为支付轨道的政策走向、美国国会对加密支付的立法动态、Ripple/XRP跨境结算监管；Coin Center是美国最权威的加密货币政策智库",
    },
    {
        "name": "jd-sift-blog",
        "url": "https://sift.com/blog/feed/",
        "tier": 1,
        "category": "industry",
        "label": "Sift Blog",
        "criteria": "保留AI风控模型、支付欺诈检测、账号安全、交易可信度设计；直接对标京东安全风控",
    },
    {
        "name": "jd-stripe-blog",
        "url": "https://stripe.com/blog/feed.rss",
        "tier": 1,
        "category": "best_minds",
        "label": "Stripe Blog",
        "criteria": "保留支付API架构、支付状态机设计、ML欺诈检测、全球支付基础设施；Stripe是支付工程最高水准",
    },

    # ── 新增：已验证RSS的待接入信源 (2026-04-23) ─────────────────────────
    {
        "name": "jd-axios-ai",
        "url": "https://api.axios.com/feed/",
        "tier": 2,
        "category": "investigative",
        "label": "Axios AI",
        "criteria": "保留AI产品发布、大厂战略动态、融资速报；Axios以简洁高密度著称，信噪比高",
    },
    {
        "name": "jd-ars-technica",
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "tier": 2,
        "category": "investigative",
        "label": "Ars Technica",
        "criteria": "保留AI/ML技术深度分析、半导体、云计算、安全漏洞；面向工程师的高质量技术报道",
    },
    {
        "name": "jd-supplychainbrain",
        "url": "https://www.supplychainbrain.com/rss/articles",
        "tier": 2,
        "category": "industry",
        "label": "SupplyChainBrain",
        "criteria": "保留供应链AI应用、仓储自动化、需求预测技术、最后一公里创新；比DC Velocity更偏技术实践",
    },
    {
        "name": "jd-canary-media",
        "url": "https://www.canarymedia.com/rss.xml",
        "tier": 2,
        "category": "industry",
        "label": "Canary Media",
        "criteria": "保留清洁能源技术创新、电网AI优化、工业脱碳；关注京东物流仓储碳中和路径",
    },
    {
        "name": "jd-mobihealthnews",
        "url": "https://www.mobihealthnews.com/rss.xml",
        "tier": 2,
        "category": "industry",
        "label": "MobiHealthNews",
        "criteria": "保留数字健康AI应用、医疗设备IoT、患者数据平台；关注京东健康业务的竞对技术方向",
    },
    {
        "name": "jd-electrive",
        "url": "https://www.electrive.com/feed/",
        "tier": 2,
        "category": "industry",
        "label": "Electrive",
        "criteria": "保留电动汽车技术演进、充电基础设施、车企数字化；关注京东汽车业务和新能源物流车队",
    },
    {
        "name": "jd-fierce-electronics",
        "url": "https://www.fierceelectronics.com/rss/xml",
        "tier": 2,
        "category": "industry",
        "label": "Fierce Electronics",
        "criteria": "保留消费电子新品发布、芯片供应链、IoT设备趋势；对标京东3C品类和智能硬件选品方向",
    },

    # ── 财报与投资者关系 ──────────────────────────────────────────────────────
    # IR press releases: instant earnings announcements from key companies
    # Analyst commentary: Seeking Alpha earnings tag, WSJ Markets, Motley Fool
    # Note: jd_earnings_fetcher.py generates deeper briefings from actual SEC filings
    {
        "name": "jd-ir-jd",
        "url": "https://ir.jd.com/rss/news-releases.xml",
        "tier": 1,
        "category": "smart_money",
        "label": "JD.com IR",
        "criteria": "保留所有财务业绩公告、20-F年报提交、重大战略投资或资本运作；这是京东自身财务健康度和战略方向的一手信源",
    },
    {
        "name": "jd-ir-pdd",
        "url": "https://investor.pddholdings.com/rss/news-releases.xml",
        "tier": 1,
        "category": "smart_money",
        "label": "PDD Holdings IR",
        "criteria": "保留所有季报/年报财务结果、Temu海外扩张进展、GMV与货币化率数据；PDD是京东最直接的价格竞争对手",
    },
    {
        "name": "jd-ir-alibaba",
        "url": "https://www.alibabagroup.com/en-US/news/pressReleases/rss",
        "tier": 1,
        "category": "smart_money",
        "label": "Alibaba Group IR",
        "criteria": "保留季报/年报结果、云业务与AI投入、淘天/国际电商分拆进展、与京东直接竞争业务的数据；过滤员工活动和社会责任类公告",
    },
    {
        "name": "jd-sa-earnings",
        "url": "https://seekingalpha.com/tag/earnings/feed.xml",
        "tier": 2,
        "category": "industry",
        "label": "Seeking Alpha · Earnings",
        "criteria": "只保留与京东竞争格局相关的公司财报分析：JD、BABA、PDD、AMZN、SE（东南亚）、SHOP；过滤无关行业的财报",
    },
    {
        "name": "jd-wsj-markets",
        "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "tier": 2,
        "category": "industry",
        "label": "WSJ Markets",
        "criteria": "只保留中国科技/电商公司的市场动态、监管事件、重大财务结果；过滤美股大盘技术分析和与京东无关的行业新闻",
    },
    # Synthetic briefings from jd_earnings_fetcher.py are inserted with feed_name='jd-earnings-analysis'
    # They are scored by jd_scorer.py in the normal pipeline.
    # No RSS entry needed — the fetcher inserts directly into DB.

    # ── Newly confirmed RSS sources (verified working) ────────────────────

    # Tier 1: Best Minds — AI practitioners & researchers
    {
        "name": "jd-simonwillison",
        "url": "https://simonwillison.net/atom/everything/",
        "tier": 1,
        "category": "best_minds",
        "label": "Simon Willison",
        "criteria": "只保留AI工具/LLM工程实践/多模态/Agent相关文章；过滤纯Web开发和个人杂记",
    },
    {
        "name": "jd-latent-space",
        "url": "https://www.latent.space/feed",
        "tier": 1,
        "category": "best_minds",
        "label": "Latent Space (AI Engineers)",
        "criteria": "全部保留 — AI工程师社区最高质量播客/文章，覆盖模型推理/Agent/代码生成最新实践",
    },
    {
        "name": "jd-the-gradient",
        "url": "https://thegradientpub.substack.com/feed",
        "tier": 1,
        "category": "best_minds",
        "label": "The Gradient",
        "criteria": "全部保留 — 顶级AI研究者深度访谈与评论，斯坦福/MIT/DeepMind研究者一手观点",
    },
    {
        "name": "jd-towards-ds",
        "url": "https://medium.com/feed/towards-data-science",
        "tier": 1,
        "category": "best_minds",
        "label": "Towards Data Science",
        "criteria": "只保留LLM应用、推荐系统、搜索、MLOps工程实践类文章；过滤基础教程和数据可视化入门内容",
    },
    {
        "name": "jd-lesswrong",
        "url": "https://www.lesswrong.com/feed.xml",
        "tier": 1,
        "category": "best_minds",
        "label": "LessWrong",
        "criteria": "只保留AI能力边界、对齐与安全、Agent自主性、模型可解释性相关讨论；过滤纯哲学/认知偏差类内容",
    },

    # Tier 1: Key Player — LangChain ecosystem signal
    {
        "name": "jd-langchain-blog",
        "url": "https://blog.langchain.dev/rss.xml",
        "tier": 1,
        "category": "best_minds",
        "label": "LangChain Blog",
        "criteria": "全部保留 — LangChain/LangGraph是目前Agent框架的事实标准，每篇更新直接影响京东AI工程选型",
    },

    # 量子位 — China's leading AI media, has RSS (confirmed working)
    {
        "name": "jd-qbitai",
        "url": "https://www.qbitai.com/feed/",
        "tier": 2,
        "category": "china_ecom",
        "label": "量子位 (Qbitai)",
        "criteria": "只保留AI产品发布、大模型商业化、中国AI公司动态、电商AI应用相关内容；过滤活动预告和纯学术论文解读",
    },

    # Tier 2: Tech Community — filtered Hacker News (quality bar: ≥50 points, AI/LLM keywords)
    {
        "name": "jd-hackernews",
        "url": "https://hnrss.org/newest?q=AI+OR+LLM+OR+agent+OR+deepseek+OR+reasoning+OR+ecommerce&points=50",
        "tier": 2,
        "category": "tech_community",
        "label": "Hacker News · AI精选",
        "criteria": "只保留与AI工程/产品/电商相关的讨论帖；尤其关注评论区里工程师对新模型/新工具的第一反应——这是质量最纯的社区信号",
    },

    # ── US Tech Communities ────────────────────────────────────────────────
    {
        "name": "jd-reddit-ml",
        "url": "https://www.reddit.com/r/MachineLearning/top.rss?t=week&limit=25",
        "tier": 2,
        "category": "tech_community",
        "label": "Reddit r/MachineLearning",
        "criteria": "保留所有涉及AI能力被实际产品采用的讨论：新模型的产品化潜力、工程部署经验、AI工具的真实使用效果；也保留从业者对研究的第一反应（代表行业认知变化信号）；过滤求职、项目推广、纯新手问答",
    },
    {
        "name": "jd-reddit-localllama",
        "url": "https://www.reddit.com/r/LocalLLaMA/top.rss?t=week&limit=25",
        "tier": 2,
        "category": "tech_community",
        "label": "Reddit r/LocalLLaMA",
        "criteria": "全部保留——本地部署LLM的实测报告、量化方案、推理速度、模型对比、用户实际工作流改变；这里的产品体验比官方发布早2-4周，是AI产品落地的最真实信号",
    },
    {
        "name": "jd-reddit-artificial",
        "url": "https://www.reddit.com/r/artificial/top.rss?t=week&limit=25",
        "tier": 2,
        "category": "tech_community",
        "label": "Reddit r/artificial",
        "criteria": "保留有实质内容的AI产品体验、市场变化、创业动态帖子；尤其关注'AI改变了我的工作方式'类的真实用户反馈，以及AI新产品的讨论；过滤纯新闻转载和无讨论的链接分享",
    },
    {
        "name": "jd-producthunt-ai",
        "url": "https://www.producthunt.com/feed?category=artificial-intelligence",
        "tier": 2,
        "category": "tech_community",
        "label": "Product Hunt · AI",
        "criteria": "全部保留——Product Hunt上的AI新产品发布直接代表市场在投票哪类AI应用有需求；upvote数量是验证产品市场契合度的即时信号",
    },
    {
        "name": "jd-devto-ai",
        "url": "https://dev.to/api/articles?tag=ai&top=7&per_page=30",
        "tier": 2,
        "category": "tech_community",
        "label": "dev.to · AI",
        "criteria": "保留所有用AI构建产品的工程实践：AI API集成实战、AI产品架构、提示词工程落地案例、AI工具对比测评；开发者用AI构建什么、遇到什么坑，是产品创新的原始信号；过滤纯入门教程",
    },
    {
        "name": "jd-hn-showhn",
        "url": "https://news.ycombinator.com",
        "tier": 1,
        "category": "tech_community",
        "label": "Show HN · 产品发布",
        "criteria": "全部保留——Show HN是构建者展示真实产品/工具/服务的社区，points代表开发者实际需求的直接投票；关注AI工具、开发者工具、新平台、SaaS产品、AI驱动的新市场机会；不限于AI主题，任何用AI赋能的产品创新均保留",
    },
    {
        "name": "jd-lobsters-ai",
        "url": "https://lobste.rs/t/vibecoding.rss",
        "tier": 1,
        "category": "tech_community",
        "label": "Lobste.rs · vibecoding",
        "criteria": "全部保留——该tag汇聚工程师用AI工具实际构建/部署产品的第一手经验；工具评测、AI辅助开发真实体验、产品上线分享；invite-only社区信噪比极高，每篇均有价值",
    },

    # ── Chinese Tech Communities ───────────────────────────────────────────
    {
        "name": "jd-juejin-ai",
        "url": "https://juejin.cn/rss",
        "tier": 2,
        "category": "tech_community",
        "label": "掘金 Juejin",
        "criteria": "保留所有用AI构建产品/工具的工程实践文章：LLM集成、AI功能开发、Agent搭建、AI辅助编程实战；掘金工程师分享是国内AI产品落地最密集的信号源；不限于AI本身，关注AI在各类产品场景的应用",
    },
    # V2EX: handled by jd_hot_fetcher.py (hot API with reply counts) — not via RSS
    # Criteria for scoring (used by criteria_judge via FEED_CRITERIA_MAP):
    {
        "name": "jd-v2ex",
        "url": "https://www.v2ex.com/api/topics/hot.json",
        "tier": 2,
        "category": "tech_community",
        "label": "V2EX",
        "criteria": "保留所有涉及AI工具使用体验、AI产品评测、用AI做副业/创业、AI改变工作流的讨论；V2EX是国内独立开发者和工程师密度最高的社区，高回复帖子代表真实共鸣；不过滤任何AI应用相关讨论",
        "_fetch_via_hot_api": True,  # skip RSS fetch, handled by jd_hot_fetcher.py
    },
    {
        "name": "jd-sspai",
        "url": "https://sspai.com/feed",
        "tier": 2,
        "category": "tech_community",
        "label": "少数派 SSPAI",
        "criteria": "保留AI工具深度评测、AI产品使用体验、效率工具与AI结合的案例；少数派读者是国内最挑剔的产品用户，他们的评测代表真实用户对AI产品价值的判断",
    },
    # ── Chinese Media (editorial) — displayed in 竞品动向, NOT 社区热议 ─────
    {
        "name": "jd-36kr",
        "url": "https://36kr.com/feed",
        "tier": 2,
        "category": "media",
        "label": "36氪",
        "criteria": "保留AI创业公司融资动态、AI产品发布、AI在各行业的落地案例、科技公司AI战略；36氪是国内最重要的科技创业媒体，AI产品从0到1的早期信号集中于此；过滤娱乐、汽车非AI内容",
    },
    {
        "name": "jd-geekpark",
        "url": "https://www.geekpark.net/rss",
        "tier": 2,
        "category": "media",
        "label": "极客公园",
        "criteria": "保留AI产品发布、AI创业故事、科技公司AI战略、前沿AI应用体验；极客公园定位AI产品创新的中文第一媒体，报道深度和时效兼顾；过滤纯消费电子非AI评测",
    },
    {
        "name": "jd-ifanr",
        "url": "https://www.ifanr.com/feed",
        "tier": 2,
        "category": "media",
        "label": "爱范儿 iFanr",
        "criteria": "保留AI产品体验报告、消费级AI应用评测、AI硬件/软件产品发布；爱范儿代表国内科技消费者对AI产品的真实使用评价，是C端AI产品落地的重要信号",
    },
    {
        "name": "jd-ruanyifeng",
        "url": "https://feeds.feedburner.com/ruanyifeng",
        "tier": 2,
        "category": "media",
        "label": "阮一峰周刊",
        "criteria": "全部保留——阮一峰科技爱好者周刊是国内工程师阅读量最大的技术资讯整合，每期精选的AI工具、产品、资源代表工程师群体的关注焦点",
    },
    # ── Chinese Thread Communities — displayed in 社区热议 ────────────────
    {
        "name": "jd-linux-do",
        "url": "https://linux.do/top.rss?period=weekly",
        "tier": 2,
        "category": "tech_community",
        "label": "Linux.do",
        "criteria": "保留所有涉及AI工具使用、AI辅助开发、AI产品体验、用AI创业/副业的讨论帖；Linux.do是国内新兴的活跃技术社区（Discourse论坛），AI话题讨论浓度高，工程师密度大；按周热门排序，高浏览量帖子代表真实共鸣",
    },

    # ── Twitter/X — via nitter.net RSS ───────────────────────────────────
    # RSS URL pattern: https://nitter.net/{username}/rss
    # nitter.net is a privacy-friendly Twitter frontend with RSS support
    # (rsshub.app/twitter returns 404 as of 2025; nitter.net confirmed working)
    # Fallback instances if nitter.net goes down: nitter.1d4.us, nitter.poast.org

    # 顶尖研究者 — Frontier AI practitioners
    {
        "name": "jd-twitter-karpathy",
        "url": "https://nitter.net/karpathy/rss",
        "tier": 1,
        "category": "best_minds",
        "label": "Andrej Karpathy (Twitter)",
        "criteria": "全部保留 — 前Tesla/OpenAI，最具影响力的AI工程实践者，每条推特都是模型训练/LLM工程的一手观点",
    },
    {
        "name": "jd-twitter-ylecun",
        "url": "https://nitter.net/ylecun/rss",
        "tier": 1,
        "category": "best_minds",
        "label": "Yann LeCun (Twitter)",
        "criteria": "全部保留 — Meta首席AI科学家，在开源模型/AGI路线图上与OpenAI持续对话，代表最顶层学界-产业界的分歧信号",
    },
    {
        "name": "jd-twitter-drjimfan",
        "url": "https://nitter.net/drjimfan/rss",
        "tier": 1,
        "category": "best_minds",
        "label": "Jim Fan (Twitter)",
        "criteria": "全部保留 — NVIDIA具身智能/机器人研究负责人，关注物流/仓储机器人方向的必读信号",
    },
    {
        "name": "jd-twitter-fchollet",
        "url": "https://nitter.net/fchollet/rss",
        "tier": 1,
        "category": "best_minds",
        "label": "François Chollet (Twitter)",
        "criteria": "全部保留 — Keras创始人/ARC-AGI发起人，在AI推理能力边界/AGI进展上最清醒的批判者",
    },

    # 关键玩家 — Industry leaders
    {
        "name": "jd-twitter-sama",
        "url": "https://nitter.net/sama/rss",
        "tier": 1,
        "category": "best_minds",
        "label": "Sam Altman (Twitter)",
        "criteria": "全部保留 — OpenAI CEO，每次发声都是全球AI格局的方向标",
    },
    {
        "name": "jd-twitter-demishassabis",
        "url": "https://nitter.net/demishassabis/rss",
        "tier": 1,
        "category": "best_minds",
        "label": "Demis Hassabis (Twitter)",
        "criteria": "全部保留 — Google DeepMind CEO，科学AI/蛋白质折叠/模型安全方向的旗手",
    },

    # 顶尖研究者 — Extended frontier researchers
    {
        "name": "jd-twitter-ilyasut",
        "url": "https://nitter.net/ilyasut/rss",
        "tier": 1, "category": "best_minds",
        "label": "Ilya Sutskever (Twitter)",
        "criteria": "全部保留 — SSI创始人/OpenAI联合创始人，AGI安全与超级对齐方向的最高信号",
    },
    {
        "name": "jd-twitter-AndrewYNg",
        "url": "https://nitter.net/AndrewYNg/rss",
        "tier": 1, "category": "best_minds",
        "label": "Andrew Ng (Twitter)",
        "criteria": "全部保留 — DeepLearning.AI/Landing AI创始人，AI普及化与产业落地最权威声音",
    },
    {
        "name": "jd-twitter-rasbt",
        "url": "https://nitter.net/rasbt/rss",
        "tier": 1, "category": "best_minds",
        "label": "Sebastian Raschka (Twitter)",
        "criteria": "全部保留 — 实用LLM工程实践者，模型训练/微调/评测一线视角",
    },
    {
        "name": "jd-twitter-emollick",
        "url": "https://nitter.net/emollick/rss",
        "tier": 1, "category": "best_minds",
        "label": "Ethan Mollick (Twitter)",
        "criteria": "全部保留 — 沃顿商学院教授，AI对组织/工作/教育影响的最佳观察者，捕捉AI普及拐点信号",
    },
    {
        "name": "jd-twitter-GaryMarcus",
        "url": "https://nitter.net/GaryMarcus/rss",
        "tier": 1, "category": "best_minds",
        "label": "Gary Marcus (Twitter)",
        "criteria": "全部保留 — AI最有力的批判者，能识别过度炒作并提前预警模型失败风险",
    },
    {
        "name": "jd-twitter-xlr8harder",
        "url": "https://nitter.net/xlr8harder/rss",
        "tier": 1, "category": "best_minds",
        "label": "Mihail Eric (Twitter)",
        "criteria": "只保留AI产品/基础模型评测/Agent系统相关内容",
    },

    # 关键玩家 — Lab & platform leaders
    {
        "name": "jd-twitter-darioamodei",
        "url": "https://nitter.net/darioamodei/rss",
        "tier": 1, "category": "best_minds",
        "label": "Dario Amodei (Twitter)",
        "criteria": "全部保留 — Anthropic CEO，AI安全/能力前沿/政策的最高优先级信号",
    },
    {
        "name": "jd-twitter-gdb",
        "url": "https://nitter.net/gdb/rss",
        "tier": 1, "category": "best_minds",
        "label": "Greg Brockman (Twitter)",
        "criteria": "全部保留 — OpenAI联合创始人，产品路线图和组织动态的一手信号",
    },
    {
        "name": "jd-twitter-jeffdean",
        "url": "https://nitter.net/jeffdean/rss",
        "tier": 1, "category": "best_minds",
        "label": "Jeff Dean (Twitter)",
        "criteria": "全部保留 — Google DeepMind首席科学家，大规模系统与AI基础设施方向",
    },
    {
        "name": "jd-twitter-kaifulee",
        "url": "https://nitter.net/kaifulee/rss",
        "tier": 1, "category": "best_minds",
        "label": "Kai-Fu Lee 李开复 (Twitter)",
        "criteria": "全部保留 — 01.AI创始人，中美AI格局/中国大模型商业化最权威视角",
    },

    # 资本动向 — Investors & strategic thinkers
    {
        "name": "jd-twitter-pmarca",
        "url": "https://nitter.net/pmarca/rss",
        "tier": 1, "category": "smart_money",
        "label": "Marc Andreessen (Twitter)",
        "criteria": "只保留AI/技术/产业政策/中美科技竞争相关内容；过滤纯政治观点",
    },
    {
        "name": "jd-twitter-naval",
        "url": "https://nitter.net/naval/rss",
        "tier": 1, "category": "smart_money",
        "label": "Naval Ravikant (Twitter)",
        "criteria": "只保留AI对商业/创业/财富创造影响的观点；过滤纯哲学/个人修炼内容",
    },
    {
        "name": "jd-twitter-sarahguo",
        "url": "https://nitter.net/sarahguo/rss",
        "tier": 1, "category": "smart_money",
        "label": "Sarah Guo (Twitter)",
        "criteria": "全部保留 — Conviction VC创始人，AI应用层投资最前沿信号",
    },
    {
        "name": "jd-twitter-eladgil",
        "url": "https://nitter.net/eladgil/rss",
        "tier": 1, "category": "smart_money",
        "label": "Elad Gil (Twitter)",
        "criteria": "全部保留 — 顶级天使投资人，AI基础设施与应用层投资判断",
    },
    {
        "name": "jd-twitter-martin_casado",
        "url": "https://nitter.net/martin_casado/rss",
        "tier": 1, "category": "smart_money",
        "label": "Martin Casado (Twitter)",
        "criteria": "全部保留 — a16z合伙人，AI基础设施/企业AI落地的最锐利分析者",
    },
    {
        "name": "jd-twitter-chamath",
        "url": "https://nitter.net/chamath/rss",
        "tier": 1, "category": "smart_money",
        "label": "Chamath Palihapitiya (Twitter)",
        "criteria": "只保留AI/科技投资/中美竞争相关内容；过滤纯金融/政治评论",
    },

    # ── Product & Application Frontier ─────────────────────────────────────
    {
        "name": "jd-twitter-simonw",
        "url": "https://twitter.com/simonw",
        "tier": 1, "category": "product_builders",
        "label": "Simon Willison (Twitter)",
        "criteria": "全部保留 — Datasette创始人，每天发布AI工具实战测试结果；'这个能用/不能用'的第一手验证，是最诚实的LLM能力边界探针",
    },
    {
        "name": "jd-twitter-swyx",
        "url": "https://twitter.com/swyx",
        "tier": 1, "category": "product_builders",
        "label": "Shawn Wang swyx (Twitter)",
        "criteria": "只保留AI工程/AI产品构建/AI应用落地相关内容 — AI Engineer社区创始人，跟踪'什么在真实落地'而非'什么在论文里'",
    },
    {
        "name": "jd-twitter-goodside",
        "url": "https://twitter.com/goodside",
        "tier": 1, "category": "product_builders",
        "label": "Riley Goodside (Twitter)",
        "criteria": "全部保留 — Scale AI首席提示工程师，最早系统性探索GPT-4能力边界的实践者，每条推文都是LLM实战验证",
    },
    {
        "name": "jd-twitter-AravSrinivas",
        "url": "https://twitter.com/AravSrinivas",
        "tier": 1, "category": "product_builders",
        "label": "Aravind Srinivas (Twitter)",
        "criteria": "全部保留 — Perplexity CEO，建造最成功的AI原生消费品，每次发声都是AI产品设计/用户增长的真实信号",
    },
    {
        "name": "jd-twitter-tobi",
        "url": "https://twitter.com/tobi",
        "tier": 1, "category": "product_builders",
        "label": "Tobi Lütke (Twitter)",
        "criteria": "只保留AI工具在商业/电商运营/产品决策中的实际应用内容 — Shopify CEO，最激进的AI内部采用者之一，直接分享AI如何改变零售业",
    },
    {
        "name": "jd-twitter-patrickc",
        "url": "https://twitter.com/patrickc",
        "tier": 1, "category": "product_builders",
        "label": "Patrick Collison (Twitter)",
        "criteria": "全部保留 — Stripe CEO，极少数兼具产品直觉与宏观思维的科技领袖，对'什么是优秀产品'和'互联网如何改变商业'有最深刻的一手洞察",
    },
    {
        "name": "jd-twitter-levie",
        "url": "https://twitter.com/levie",
        "tier": 1, "category": "product_builders",
        "label": "Aaron Levie (Twitter)",
        "criteria": "只保留AI在企业软件/工作流中的实际落地、AI改变SaaS产品形态的内容；过滤纯商业评论 — Box CEO，企业AI真实采用速度的第一手感知者",
    },
    {
        "name": "jd-twitter-eugeneyan",
        "url": "https://twitter.com/eugeneyan",
        "tier": 1, "category": "product_builders",
        "label": "Eugene Yan (Twitter)",
        "criteria": "全部保留 — 亚马逊应用ML，专注推荐系统/搜索/LLM真实部署的一线工程师，每篇都是从实验室到生产的实战经验",
    },
    {
        "name": "jd-twitter-jeremyphoward",
        "url": "https://twitter.com/jeremyphoward",
        "tier": 1, "category": "product_builders",
        "label": "Jeremy Howard (Twitter)",
        "criteria": "全部保留 — Fast.ai创始人，最实用的ML教育者和工具构建者，专注'普通人能用的AI'这个产品命题",
    },
    {
        "name": "jd-twitter-garrytan",
        "url": "https://twitter.com/garrytan",
        "tier": 1, "category": "smart_money",
        "label": "Garry Tan (Twitter)",
        "criteria": "只保留AI创业/产品构建/YC项目相关内容 — YC CEO，每天接触数百个AI产品pitch，对'什么在被真实构建'有无与伦比的广度视角",
    },

    # ── Chinese Tech Voices on Twitter ─────────────────────────────────────
    {
        "name": "jd-twitter-dotey",
        "url": "https://twitter.com/dotey",
        "tier": 1, "category": "chinese_voices",
        "label": "宝玉xp (Twitter)",
        "criteria": "只保留AI产品体验/模型能力/工具评测/中文AI应用相关内容 — 中文AI社区最大的翻译/评论账号，翻译顶级AI论文和产品更新，代表中文技术社区对AI产品的第一手解读",
    },
    {
        "name": "jd-twitter-satyanadella",
        "url": "https://twitter.com/satyanadella",
        "tier": 1, "category": "product_builders",
        "label": "Satya Nadella (Twitter)",
        "criteria": "只保留AI在企业/生产力工具/平台中的战略部署内容 — Microsoft CEO，将AI最快速地嵌入主流工作流（Copilot/Azure），对企业AI落地速度有最真实的一线数据",
    },
]

# ── X/Twitter endorsement weights ────────────────────────────────────────────
# Used by jd_twitter_endorsements.py to compute per-article endorsement boost.
# Weight = how much a single RT/link from this account amplifies an article's signal.
# Scale: 0.05 (minor amplification) to 0.30 (paradigm-defining figure)
X_ENDORSER_WEIGHTS = {
    # Frontier researchers — highest epistemic authority
    "karpathy":      0.30,
    "ylecun":        0.28,
    "ilyasut":       0.28,
    "fchollet":      0.25,
    "AndrewYNg":     0.25,
    "jeffdean":      0.22,
    "drjimfan":      0.20,
    "rasbt":         0.18,
    "emollick":      0.18,
    "GaryMarcus":    0.15,  # contrarian — valuable as counter-signal
    "xlr8harder":    0.12,
    # Lab & platform CEOs
    "sama":          0.25,
    "darioamodei":   0.25,
    "demishassabis":0.22,
    "gdb":           0.18,
    "kaifulee":      0.20,  # China-specific weight elevated
    # Investors
    "pmarca":        0.18,
    "sarahguo":      0.20,
    "eladgil":       0.18,
    "martin_casado": 0.15,
    "naval":         0.12,
    "chamath":       0.10,
}

CATEGORY_LABELS = {
    "smart_money":  "💰 Smart Money",
    "best_minds":   "🧠 Best Minds",
    "investigative":"🔍 深度调查",
    "china_ecom":   "🇨🇳 中国电商",
    "global_retail":"🌐 全球零售",
}

TIER_LABELS = {
    1: "🌪 Tier 1 · 风向标",
    2: "📡 Tier 2 · 确认信号",
}
