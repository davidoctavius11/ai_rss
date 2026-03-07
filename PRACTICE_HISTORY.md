# 项目演进史（实践记录）

## 第一阶段：2026.2.12 - 初始搭建
- 搭建基础RSS抓取框架
- 首次采集88条新闻，发现arXiv论文过多的问题

## 第二阶段：2026.2.13 上午 - 全文抓取与criteria优化
- 解决"只看摘要误判"问题，引入多引擎全文抓取
- 发现国内源被墙，引入本地RSSHub
- 重写criteria，从"学术审稿"转向"商业科技观察"

## 第三阶段：2026.2.13 下午 - 增量机制与名称对齐
- **重大坑**：config里的feed_name必须和数据库完全一致，否则AI全给50分
- 实现增量抓取，避免重复全量采集（省钱、省时）
- 最终得到44篇平均分28的精选文章

## 第四阶段：2026.2.13 晚上 - 最终定型
- 隧道地址：`actions-promises-symposium-trailers.trycloudflare.com`
- 订阅源：`https://{地址}/feed.xml`
- 发现知乎生活类文章误判，调整知乎criteria

## 第五阶段：2026.2.14 - 最终运营版
- ✅ **打通 Reeder 连接**：解决 `nsxmlparsererrordomain 错误23`（MIME类型问题）
- ✅ **新增5个高质量源**：The Verge、少数派、TechCrunch、OneV's Den、Lifehacker
- ✅ **确定"宁可漏判，不可误杀"原则**：精简"严格排除"项，增加"可以接受"缓冲层
- ✅ **文章数稳定在100篇**：阈值40分，质量与数量达到平衡

## 第六阶段：2026.2.24 - Cloudflare Tunnel永久域名绑定
- ✅ **绑定永久域名**：将borntofly.ai域名绑定到5003端口
- ✅ **创建子域名**：使用rss.borntofly.ai作为永久地址
- ✅ **替换ngrok**：使用Cloudflare Tunnel替代ngrok，获得永久地址
- ✅ **免费HTTPS**：自动获得Cloudflare提供的免费SSL证书

## 第七阶段：2026.2.24 晚上 - AI筛选增强版优化
- ✅ **修复AI筛选理由显示问题**：确保所有文章都有AI筛选理由
- ✅ **优化文章相关性**：保持60分阈值，增加高质量源补充机制
- ✅ **增强文章数量**：从42篇增加到50篇（40篇AI筛选 + 10篇高质量源补充）
- ✅ **改进筛选逻辑**：当AI筛选文章不足50篇时，自动补充TechCrunch等高质量源文章
- ✅ **添加强制刷新参数**：支持`?refresh=1`参数强制刷新缓存
- ✅ **修复数据库链接问题**：将http链接更新为https链接，清理垃圾链接

## 第八阶段：2026.2.25 - 生产级改造与稳定化
- ✅ **移除高质量源补充**：只保留评分达标文章
- ✅ **阈值调整**：评分阈值从60改为50
- ✅ **时效策略**：90天内文章 + 常青分≥80
- ✅ **缓存策略**：RSS接口强制刷新，解决Reeder缓存问题
- ✅ **全文抓取前置**：评分前自动补全全文（提升评分准确性）
- ✅ **时间标准化**：统一published_date为ISO‑8601 UTC，修复时效计算
- ✅ **新增架构类源**：面向CTO/首席架构成长内容
- ✅ **自动化运维**：cron每周两次自动更新
- ✅ **播客管线雏形**：脚本生成与评分策略已就绪（待Inworld TTS接入）

## 第九阶段：2026.3 - Particle式多视角故事合成
受Particle新闻App启发，将孤立文章升级为「故事全貌」。
- ✅ **多视角合成**：`multi_perspective.py` 关键词聚类（每组5篇），DeepSeek综合生成战略层/执行层分析
- ✅ **内容质量过滤**：只对全文≥500字或摘要≥300字的深度文章生成合成（排除短新闻）
- ✅ **跨媒体视角**：自动检测中文/英文来源混合，触发中西方媒体框架对比分析
- ✅ **cluster_json**：存储每篇合成涉及的原文来源（标题/媒体/链接），内页展示溯源列表
- ✅ **成员反向指针**：非种子文章显示🔗回链，指向所属故事的种子文章
- ✅ **🧠 标题前缀**：种子文章标题加🧠前缀，在Reeder中可视化识别（RSS客户端按pubDate排序，无法控制XML顺序）
- ✅ **Markdown清洗**：`_strip_markdown()` 过滤`###`/`**`等标记，RSS描述纯文本输出
- ✅ **新增5个英文深度源**：Wired、Ars Technica、MIT Technology Review、VentureBeat、机器之心（共58个源）
- ✅ **BA受众定位**：合成提示词明确面向「数据驱动的业务分析师」，聚焦BA与产品/算法团队协作的实践价值
- **关键坑**：`sqlite3.Row` 不支持 `.get()`，必须用直接索引 `row['col']`
- **关键坑**：RSS客户端（Reeder）按pubDate排序，忽略XML条目顺序

## 第十阶段：2026.3.7 - 学习系统 & 知识图谱
将RSS订阅从被动信息消费升级为「边做边学」的主动成长闭环。
- ✅ **学习关联注入**：`criteria_judge.py` 加载 `~/Agents/knowledge_log/concepts.json`，将学习关联自然拼接在ai_reason末尾（格式：`理由 — 学习关联`）
- ✅ **合成提示词增强**：`multi_perspective.py` 在战略/执行/延伸思考之外，新增可选「与我们项目的关联」段落，仅在有实质关联时输出
- ✅ **知识图谱创建**：`~/Agents/knowledge_log/concepts.json`，收录来自ai_rss实践的11个概念，覆盖Infrastructure/Backend/Networking/AI Integration/Data Pipeline/System Architecture六个领域，含Ebbinghaus复习时间表
- ✅ **项目复盘**：`~/Agents/knowledge_log/projects/ai_rss.md`，CTO视角的架构决策表、关键坑、未来方向
- ✅ **env变量修复**：两个文件改用 `dotenv_values()` 直接读取 `.env` 文件，绕过shell中残留的过期`DEEPSEEK_API_KEY`变量
- **愿景**：未来将ai_reason + 多视角合成统一为一个整体简报（holistic brief），学习关联是其中一个自然维度
- **下一步**：添加 One Useful Thing / Lenny's Newsletter 等Substack源；Ebbinghaus定期复习会话
