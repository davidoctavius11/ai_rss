# AI RSS 项目文档

## 📋 项目概览

一个用AI智能筛选科技资讯的RSS聚合器，从多源聚合中精选高质量内容，输出可订阅的RSS feed。

### 核心信息
| 项目 | 说明 |
|------|------|
| **项目名称** | AI RSS (ai_rss) |
| **Python环境** | `venv` 虚拟环境 |
| **数据库** | SQLite (`data/ai_rss.db`) |
| **服务器端口** | 5006 (AI筛选版) / 5005 (简化版) |
| **核心目标** | 用AI筛选科技资讯，输出高质量RSS |

---

## 🚀 快速开始

1. 创建环境并安装依赖（示例）
   - 使用你自己的依赖管理方式安装：`requests`, `feedparser`, `flask`, `python-dotenv`, `trafilatura`, `readability-lxml`, `beautifulsoup4`
2. 复制配置
   - `cp config.example.py config.py`
   - `cp .env.example .env` 并填写 API Key
3. 初始化数据库
   - `python3 db.py`
4. 抓取 + 评分
   - `python3 fetcher.py`
   - `python3 criteria_judge.py --threshold 50`
5. 启动服务
   - `python3 app_ai_filtered.py`
6. RSS 访问
   - `http://localhost:5006/feed.xml`

---

## 📚 项目演进史

### 第一阶段：2026.2.12 - 初始搭建
- 搭建基础RSS抓取框架
- 首次采集88条新闻，发现arXiv论文过多的问题

### 第二阶段：2026.2.13 上午 - 全文抓取与criteria优化
- 解决"只看摘要误判"问题，引入多引擎全文抓取
- 发现国内源被墙，引入本地RSSHub
- 重写criteria，从"学术审稿"转向"商业科技观察"

### 第三阶段：2026.2.13 下午 - 增量机制与名称对齐
- **重大坑**：config里的feed_name必须和数据库完全一致，否则AI全给50分
- 实现增量抓取，避免重复全量采集（省钱、省时）
- 最终得到44篇平均分28的精选文章

### 第四阶段：2026.2.13 晚上 - 最终定型
- 隧道地址：`actions-promises-symposium-trailers.trycloudflare.com`
- 订阅源：`https://{地址}/feed.xml`
- 发现知乎生活类文章误判，调整知乎criteria

### 第五阶段：2026.2.14 - 最终运营版
- ✅ **打通 Reeder 连接**：解决 `nsxmlparsererrordomain 错误23`（MIME类型问题）
- ✅ **新增5个高质量源**：The Verge、少数派、TechCrunch、OneV's Den、Lifehacker
- ✅ **确定"宁可漏判，不可误杀"原则**：精简"严格排除"项，增加"可以接受"缓冲层
- ✅ **文章数稳定在100篇**：阈值40分，质量与数量达到平衡

### 第六阶段：2026.2.24 - Cloudflare Tunnel永久域名绑定
- ✅ **绑定永久域名**：将borntofly.ai域名绑定到5003端口
- ✅ **创建子域名**：使用rss.borntofly.ai作为永久地址
- ✅ **替换ngrok**：使用Cloudflare Tunnel替代ngrok，获得永久地址
- ✅ **免费HTTPS**：自动获得Cloudflare提供的免费SSL证书

### 第七阶段：2026.2.24 晚上 - AI筛选增强版优化
- ✅ **修复AI筛选理由显示问题**：确保所有文章都有AI筛选理由
- ✅ **优化文章相关性**：保持60分阈值，增加高质量源补充机制
- ✅ **增强文章数量**：从42篇增加到50篇（40篇AI筛选 + 10篇高质量源补充）
- ✅ **改进筛选逻辑**：当AI筛选文章不足50篇时，自动补充TechCrunch等高质量源文章
- ✅ **添加强制刷新参数**：支持`?refresh=1`参数强制刷新缓存
- ✅ **修复数据库链接问题**：将http链接更新为https链接，清理垃圾链接

---

## 🎯 当前状态 (2026.2.25)

### AI筛选增强版 (`app_ai_filtered.py`)
- **端口**: 5006
- **筛选标准**: 50分阈值
- **时效策略**: 90天内文章 + 评分≥80的常青文章
- **数据库统计**:
  - 📰 总文章数: 868篇
  - 🎯 已评分文章: 320篇 (36.9%)
  - 📈 平均评分: 26.0分
  - ✅ 保留文章: 评分≥50
  - ❌ 淘汰文章: 评分<50

### 简化版 (`app_simple.py`)
- **端口**: 5005
- **筛选标准**: 无AI筛选，直接显示最新文章

---

## 🔧 过去几小时完成的工作总结

### 1. AI筛选增强版优化
- **变更**: 移除“高质量源补充”机制，仅保留评分达标文章
- **新增**: 时效策略（90天内 + 常青评分≥80）

### 2. AI筛选理由显示修复
- **问题**: 部分文章显示"无筛选理由"
- **解决方案**: 修复`_row_to_article`函数逻辑
  - 优先使用`criteria_reason`字段
  - 如果没有理由但有评分，显示"AI评分: [分数]分"
  - 如果既没有理由也没有评分，显示"来自高质量源: [源名称]"

### 3. 数据库清理和优化
- **清理垃圾链接**: 删除http://bbs.*等垃圾论坛链接
- **链接协议升级**: 将http://blog.research.google更新为https://blog.research.google
- **数据库统计**: 总文章数从892篇清理到868篇

### 4. 强制刷新功能
- **添加参数**: 支持`?refresh=1`参数强制刷新缓存
- **缓存时间**: 30分钟缓存，提高性能
- **调试信息**: 显示详细的文章获取和筛选信息

### 5. 应用架构改进
- **多版本共存**: 
  - `app_ai_filtered.py` (端口5006): AI筛选增强版
  - `app_simple.py` (端口5005): 简化版
  - `app.py` (端口5003): 原始版
- **独立配置**: 每个应用有独立的配置和筛选逻辑
- **统计页面**: 添加详细的数据库统计和源表现统计

---

## 📁 项目文件清单

| 文件 | 作用 | 最后稳定版本 |
|------|------|--------------|
| `config.py` | RSS源配置 + AI筛选标准 | ✅ v2.1 (36个源) |
| `fetcher.py` | 增量抓取RSS + 全文抓取 | ✅ 增量版 v2 |
| `criteria_judge.py` | AI审阅核心 | ✅ 支持阈值调节 |
| `app_ai_filtered.py` | AI筛选增强版服务器 | ✅ 最新优化版 |
| `app_simple.py` | 简化版服务器 | ✅ 无筛选版 |
| `app.py` | 原始版服务器 | ✅ 基础版 |
| `cloudflared-config.yml` | Cloudflare Tunnel配置 | ✅ 永久域名版 |
| `start_cloudflared.sh` | 启动Cloudflare Tunnel脚本 | ✅ 后台运行版 |

---

## 🚀 运维命令速查

### 启动AI筛选增强版
```bash
cd ~/ai_rss
python3 app_ai_filtered.py
# 访问: http://localhost:5006/
# RSS: http://localhost:5006/feed.xml
# 强制刷新: http://localhost:5006/feed.xml?refresh=1
```

### 启动简化版
```bash
cd ~/ai_rss
python3 app_simple.py
# 访问: http://localhost:5005/
# RSS: http://localhost:5005/feed.xml
```

### 日常手动更新（每周一次）
```bash
cd ~/ai_rss
source venv/bin/activate
python fetcher.py && python fetcher.py --fulltext && python criteria_judge.py
```

### Cloudflare Tunnel启动（如果重启）
```bash
cd ~/ai_rss
./start_cloudflared.sh
```

### 查看当前永久地址
```bash
echo "永久地址: https://rss.borntofly.ai/feed.xml"
```

### 查看各源平均分
```bash
sqlite3 data/ai_rss.db "SELECT feed_name, AVG(criteria_score), COUNT(*) FROM articles WHERE criteria_score IS NOT NULL GROUP BY feed_name ORDER BY AVG(criteria_score) DESC;"
```

### 检查应用状态
```bash
# 检查AI筛选版
curl -s http://localhost:5006/debug | python3 -m json.tool

# 检查简化版
curl -s http://localhost:5005/ | grep "文章数"

# 检查永久地址
curl -I https://rss.borntofly.ai/feed.xml
```

---

## 💡 血泪教训（必读！）

### ❌ 踩过的坑
1. **名称不匹配**：config里的`name`必须和数据库`feed_name`完全一致（含标点）
2. **建表遗漏字段**：`last_seen`字段必须存在，否则增量失败
3. **arXiv误判**：因抓不到全文，AI只看摘要误判为硬核好文
4. **阈值过低**：阈值60可能太高，可降到40-50
5. **隧道地址漂移**：每次重启隧道地址会变，需记录新地址
6. **feedgen库的category格式**：必须用`term`参数，不能用`label`
7. **sqlite3.Row对象没有`.get()`方法**：要用字典方式访问
8. **Cloudflare Tunnel证书问题**：需要正确登录并获取cert.pem文件

### ✅ 正确做法
1. **修改criteria后**：必须`--reset`重置评分
2. **新增源后**：先手动抓取测试，再批量跑
3. **每天运行**：只需`python fetcher.py`（增量） + `python fetcher.py --fulltext`
4. **地址变更**：现在使用永久地址`https://rss.borntofly.ai/feed.xml`
5. **Cloudflare Tunnel登录**：使用API令牌登录，证书会自动保存到`~/.cloudflared/cert.pem`
6. **AI筛选优化**：当高质量文章不足时，补充高质量源文章保持数量

---

## 📊 源表现统计 (最新)

| 源名称 | 状态 | 平均分 | 说明 |
|--------|------|--------|------|
| 测试源 | ✅ | 85.0 | 测试用，高质量 |
| Julia Evans' Blog | ✅ | 70.0 | 高质量技术博客 |
| OneV's Den | ✅ | 67.5 | 高质量技术博客 |
| Solidot 科技 | ✅ | 56.0 | 科技新闻，质量稳定 |
| InfoQ | ⚠️ | 50.0 | 技术管理，需优化 |
| Google Research Blog | ✅ | 47.5 | 高质量技术博客 |
| OpenAI Blog | ✅ | 45.5 | AI前沿动态 |
| DeepMind Blog | ⚠️ | 43.3 | 高质量但评分低 |
| InfoQ·架构与算力 | ✅ | 36.8 | 技术架构内容 |
| Hugging Face Blog | ✅ | 33.2 | 开源模型动态 |
| 腾讯研究院 | ✅ | 35-50 | 宏观趋势，需放宽 |
| 36氪 | ✅ | 30-45 | 快讯多，需筛选 |
| The Verge | ✅ | 调试中 | 新增源 |
| 少数派 | ✅ | 调试中 | 新增源 |
| TechCrunch | ✅ | 高质量源 | 用于补充文章 |
| Lifehacker | ✅ | 调试中 | 新增源 |

---

## 🔧 依赖清单

```bash
# 核心依赖
pip install feedparser requests beautifulsoup4 lxml
pip install openai python-dotenv jinja2
pip install trafilatura readability-lxml newspaper3k goose3
pip install feedgen  # 新增，用于生成标准RSS
pip install flask   # Web服务器

# Cloudflare Tunnel (macOS)
brew install cloudflared
```

---

## 🌐 Cloudflare Tunnel配置经验

### 成功经验
1. **永久域名绑定**：成功将rss.borntofly.ai绑定到本地5003端口
2. **免费HTTPS**：Cloudflare自动提供SSL证书
3. **稳定连接**：比ngrok更稳定，不会频繁更换地址
4. **后台运行**：可以稳定在后台运行，无需频繁重启

### 配置文件 (`cloudflared-config.yml`)
```yaml
tunnel: ai-rss-tunnel
credentials-file: /Users/ioumvp/.cloudflared/08fc81e2-50e6-4218-abb1-40819473d888.json

ingress:
  - hostname: rss.borntofly.ai
    service: http://localhost:5003
    originRequest:
      connectTimeout: 30s
      noTLSVerify: false
      httpHostHeader: rss.borntofly.ai

  # 回退规则，处理其他所有请求
  - service: http_status:404
```

### 关键步骤
1. **登录Cloudflare**：`cloudflared tunnel login`
2. **创建隧道**：`cloudflared tunnel create ai-rss-tunnel`
3. **配置DNS路由**：`cloudflared tunnel route dns ai-rss-tunnel rss.borntofly.ai`
4. **启动隧道**：`cloudflared tunnel --config cloudflared-config.yml run ai-rss-tunnel`

### 注意事项
- API令牌：`UfsHQTxLEjKTLCtbIZmF1bvN3HYYjXD30zhu-IaS`
- 证书路径：`~/.cloudflared/cert.pem`
- 隧道ID：`08fc81e2-50e6-4218-abb1-40819473d888`
- 配置文件：`cloudflared-config.yml`

---

## 📌 重要备注

- **当前永久地址**：`https://rss.borntofly.ai/feed.xml`
- **数据库路径**：`/Users/ioumvp/ai_rss/data/ai_rss.db`
- **AI筛选版端口**：5006 (`app_ai_filtered.py`)
- **简化版端口**：5005 (`app_simple.py`)
- **原始版端口**：5003 (`app.py`)
- **下次重启后**：只需运行`./start_cloudflared.sh`即可恢复

---

## 📝 待办事项

| 事项 | 优先级 | 说明 |
|------|--------|------|
| ✅ **绑定永久域名** | 已完成 | 使用rss.borntofly.ai |
| ✅ **AI筛选增强版优化** | 已完成 | 增加高质量源补充机制 |
| 加入时间过滤（只保留1年内文章） | ⭐⭐ | 避免旧文章占位 |
| 设置定时任务（每6小时） | ⭐ | 目前手动更新够用 |
| 给儿子做视频RSS | ⭐ | 等当前系统稳定后 |
| 优化高质量源列表 | ⭐⭐ | 根据评分动态调整高质量源 |

---

## 🎯 核心原则

> **"宁可漏判，不可误杀"**

- 精简"严格排除"项
- 增加"可以接受"缓冲层
- 避免因标准过严错失好内容
- 阈值设为60分，保持高质量标准
- 当高质量文章不足时，补充高质量源文章

---

## 🔄 项目状态检查清单

### 每日检查
1. [ ] 检查Flask应用是否运行：`ps aux | grep python.*app`
2. [ ] 检查Cloudflare Tunnel是否运行：`ps aux | grep cloudflared`
3. [ ] 测试永久地址访问：`curl -I https://rss.borntofly.ai/feed.xml`
4. [ ] 检查数据库文章数量：`sqlite3 data/ai_rss.db "SELECT COUNT(*) FROM articles WHERE criteria_score >= 60;"`

### 每周更新
1. [ ] 运行增量抓取：`python fetcher.py`
2. [ ] 运行全文抓取：`python fetcher.py --fulltext`
3. [ ] 运行AI评分：`python criteria_judge.py`
4. [ ] 重启AI筛选服务：`pkill -f "python3 app_ai_filtered.py" && cd ~/ai_rss

---

## ⏱️ 自动更新（每周两次）

已提供脚本：`scripts/auto_refresh.sh`  
建议时间（本地时区）：**周二 & 周五 08:10**

设置 cron：
```
crontab -e
```
添加：
```
10 8 * * 2,5 /Users/ioumvp/ai_rss/scripts/auto_refresh.sh >> /Users/ioumvp/ai_rss/auto_refresh.log 2>&1
```

---

## 🎙️ 播客生成（中文）

说明：
- 仅对**非原生播客**内容生成中文播客脚本
- 原生播客内容保持原样（不参与生成）
- 研究类来源生成**双人对话**，其他为**单人主持**
- 每日最多 10 条，时长 15–20 分钟（随评分增长）
- 当前TTS方案：**Inworld TTS 1.5 Mini**（待你注册并配置）

运行：
```
python3 podcast_pipeline.py
```

输出：
- 脚本：`output/podcast/scripts/`
- 播客RSS：`output/podcast/podcast.xml` （对外访问：`https://rss.borntofly.ai/podcast.xml`）
- 音频：`output/podcast/audio/` （对外访问：`https://rss.borntofly.ai/podcast/audio/<filename>`）

配置（待你注册Inworld后补全）：
```
TTS_PROVIDER=inworld
INWORLD_API_KEY=your_key_here
INWORLD_TTS_MODEL=tts-1.5-mini
```
