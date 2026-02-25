# AI RSS 项目文档

## 📌 项目概览
AI RSS 是一个“AI 评分 + 规则策略”的资讯聚合系统，用来从多源 RSS 中筛选高质量内容，并提供可订阅的 RSS 输出。

**目标**：稳定、可解释、可运营的高质量信息流（面向 Reeder / Feedly）。

---

## ✅ 当前行为（最新）

- **评分阈值**：`>= 50`
- **时效策略**：`90 天内` 或 `评分 >= 80`（常青）
- **RSS 输出**：无上限（当前为动态数量）
- **RSS 地址**：`https://rss.borntofly.ai/feed.xml`
  - 若客户端缓存严重，可用 `https://rss.borntofly.ai/feed.xml?refresh=1`

---

## 🚀 快速开始

1. 安装依赖
```
pip install -r requirements.txt
```

2. 复制配置
```
cp config.example.py config.py
cp .env.example .env
```

3. 初始化数据库
```
python3 db.py
```

4. 抓取 + 评分
```
python3 fetcher.py
python3 criteria_judge.py --threshold 50
```

5. 启动服务
```
python3 app_ai_filtered.py
```

6. 本地访问
```
http://localhost:5006/feed.xml
```

---

## 🔁 自动化更新（已安装 cron）
每周 **周二 & 周五 08:10** 自动运行：
- 增量抓取
- 全文补全
- 评分
- 重启服务

脚本：`scripts/auto_refresh.sh`

---

## 🎙️ 播客模块（规划中）

- 只对 **非原生播客** 内容生成脚本  
- 研究类来源 → **双人对话**  
- 其他 → **单人主持**  
- 每日最多 10 条  
- 时长 **15–20 分钟**（随评分增长）  
- 中文输出  
- 计划接入 **Inworld TTS 1.5 Mini**

运行：
```
python3 podcast_pipeline.py
```

输出：
- `output/podcast/scripts/`
- `output/podcast/podcast.xml` （未来访问：`https://rss.borntofly.ai/podcast.xml`）

配置（待 Inworld 注册完成）：
```
TTS_PROVIDER=inworld
INWORLD_API_KEY=your_key_here
INWORLD_TTS_MODEL=tts-1.5-mini
```

---

## 🧭 架构图 & 实践历史

- 架构图：`ARCHITECTURE.md`
- 实践历史：`PRACTICE_HISTORY.md`

---

## 🛠 运维常用命令

重启服务：
```
pkill -f "python3 app_ai_filtered.py"
nohup python3 /Users/ioumvp/ai_rss/app_ai_filtered.py > /Users/ioumvp/ai_rss/app_ai_filtered.log 2>&1 &
```

手动刷新 RSS：
```
curl -s "https://rss.borntofly.ai/feed.xml?refresh=1" >/dev/null
```

健康检查：
```
python3 check_all_feeds.py
```

---

## 📁 关键文件

- `config.py`：RSS 源与筛选标准
- `fetcher.py`：增量抓取
- `fulltext_fetcher.py`：全文补全
- `criteria_judge.py`：AI 评分
- `app_ai_filtered.py`：RSS 服务
- `podcast_pipeline.py`：播客脚本管线

