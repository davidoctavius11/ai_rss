# 系统架构图（CTO 视角）

```mermaid
flowchart LR
  %% Sources
  subgraph S[内容源层]
    S1[外部RSS源 (Tech/Research/Architecture)]
    S2[RSSHub 本地转发]
  end

  %% Ingestion
  subgraph I[采集与解析层]
    I1[fetcher.py 增量抓取]
    I2[fulltext_fetcher.py 全文提取与清洗]
  end

  %% Storage
  subgraph D[数据层]
    D1[(SQLite: articles)]
    D2[(SQLite: podcast_episodes)]
  end

  %% Scoring & Policy
  subgraph P[评分与策略层]
    P1[criteria_judge.py AI评分 + 理由]
    P2[策略规则 阈值>=50 + 90天时效 + 常青>=80]
  end

  %% Delivery
  subgraph R[交付层]
    R1[app_ai_filtered.py feed.xml]
    R2[Cloudflare Tunnel rss.borntofly.ai]
    R3[客户端 Reeder/Feedly]
  end

  %% Automation
  subgraph O[自动化与运维层]
    O1[cron 每周两次]
    O2[auto_refresh.sh 抓取-全文-评分-重启]
  end

  %% Podcast
  subgraph C[播客扩展层]
    C1[podcast_pipeline.py 选题/脚本/长度控制]
    C2[TTS 引擎 Inworld TTS 1.5 Mini]
    C3["podcast.xml"]
  end

  S1 --> I1
  S2 --> I1
  I1 --> D1
  I2 --> D1
  D1 --> P1 --> P2
  P2 --> R1 --> R2 --> R3
  O1 --> O2 --> I1
  O2 --> I2
  O2 --> P1
  O2 --> R1
  D1 --> C1 --> D2
  C1 --> C2 --> C3
```
