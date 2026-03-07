# 系统架构图（CTO 视角）

```mermaid
flowchart LR
  %% Sources
  subgraph S["内容源层"]
    S1["外部RSS源 58个\nTech/Research/Architecture/Substack"]
    S2["RSSHub 本地转发"]
  end

  %% Ingestion
  subgraph I["采集与解析层"]
    I1["fetcher.py 增量抓取"]
    I2["fulltext_fetcher.py 全文提取与清洗"]
  end

  %% Storage
  subgraph D["数据层"]
    D1["SQLite articles\n(score + reason + content)"]
    D2["SQLite multi_perspectives\n(summary + cluster_json)"]
  end

  %% Scoring & Synthesis
  subgraph P["评分与合成层"]
    P1["criteria_judge.py\nAI评分0-100 + 学习关联注入"]
    P2["策略规则\n阈值≥50 + 90天时效 + 常青≥80"]
    P3["multi_perspective.py\n关键词聚类→DeepSeek合成\n战略/执行/跨媒体/学习关联"]
  end

  %% Knowledge
  subgraph K["学习系统层"]
    K1["~/Agents/knowledge_log/concepts.json\n11个实践领域概念\nEbbinghaus复习计划"]
    K2["projects/ai_rss.md\nCTO级项目复盘"]
  end

  %% Delivery
  subgraph R["交付层"]
    R1["app_ai_filtered.py\n/feed XML + /item 内页 + /summary"]
    R2["generator.py\n_strip_markdown + _mp_block + _story_note"]
    R3["Cloudflare Tunnel\nrss.borntofly.ai"]
    R4["客户端 Reeder\n🧠种子文章 + 🔗成员回链"]
  end

  %% Automation
  subgraph O["自动化与运维层"]
    O1["cron 每周三次\nSun/Tue/Fri"]
    O2["auto_refresh.sh\n抓取→全文→评分→合成→重启"]
    O3["LaunchAgents\nFlask + Tunnel + DeepSeek-Proxy"]
  end

  S1 --> I1
  S2 --> I1
  I1 --> D1
  I2 --> D1
  K1 --> P1
  K1 --> P3
  D1 --> P1 --> P2
  D1 --> P3 --> D2
  P2 --> R1
  D2 --> R1
  R1 --> R2 --> R3 --> R4
  O1 --> O2 --> I1
  O2 --> I2
  O2 --> P1
  O2 --> P3
  O2 --> R1
  O3 -.-> R1
  O3 -.-> R3
```

## 数据流说明

1. **采集**：fetcher.py 增量抓取58个源 → SQLite articles
2. **全文**：fulltext_fetcher.py 用UA伪装抓取全文（有墙则降级摘要）
3. **评分**：criteria_judge.py 加载知识图谱 → DeepSeek打分 + 学习关联写入reason
4. **聚类**：multi_perspective.py 关键词聚类（≤5篇/组）→ DeepSeek生成故事全貌
5. **交付**：Flask生成RSS XML → Cloudflare Tunnel → Reeder

## 关键设计决策

| 决策点 | 选择 | 替代方案 |
|---|---|---|
| 数据库 | SQLite（单文件，零配置） | PostgreSQL（多服务器写入时迁移） |
| 进程管理 | LaunchAgents（macOS原生） | Docker（需跨机器时迁移） |
| AI提供商 | DeepSeek（OpenAI兼容接口） | 改`base_url`即可切换GPT-4 |
| 内容投递 | Cloudflare Tunnel（无需公网IP） | 云服务器（需更高可用性时迁移） |
| 聚类算法 | 关键词重叠（快速无成本） | 向量嵌入（生产级精度） |
| 调度 | Cron 3次/周 | Celery+Redis（高频或实时需求） |

## 未来方向

- **整体简报（Holistic Brief）**：将criteria_reason + multi_perspective合成为单一AI生成简报，保留战略/执行/延伸思考结构
- **Ebbinghaus复习**：基于knowledge_log定期生成复习问题，会话开始时触发
- **更多Substack源**：One Useful Thing、Lenny's Newsletter
- **ai_diary / ai_health / ai_trade**：知识图谱扩展至其他项目实践领域
