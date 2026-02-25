# AI RSS 项目文档

## 📋 项目概览

一个用AI智能筛选科技资讯的RSS聚合器，从35+个优质源中精选高质量内容，输出可订阅的RSS feed。

### 核心信息
| 项目 | 说明 |
|------|------|
| **项目名称** | AI RSS (ai_rss) |
| **部署路径** | `/Users/ioumvp/ai_rss` |
| **Python环境** | `venv` 虚拟环境 |
| **数据库** | SQLite (`data/ai_rss.db`) |
| **服务器端口** | 5003 |
| **当前永久地址** | `https://rss.borntofly.ai/feed.xml` |
| **文章数量** | 100篇 (≥40分) |
| **核心目标** | 用AI筛选科技资讯，输出高质量RSS |

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

---

## 🎯 核心代码片段

### 增量抓取核心逻辑
```python
# fetcher.py 关键代码
def fetch_articles_from_feed(feed_url, feed_name, max_entries=30):
    latest_time = get_latest_published_time(feed_name)
    for entry in feed_data.entries[:max_entries]:
        if latest_time and published_time <= latest_time:
            continue  # 跳过旧文章
        # 只处理新文章
```

### 审阅优先顺序
```python
# criteria_judge.py 关键逻辑
CASE 
    WHEN content IS NOT NULL AND length(content) > 200 THEN content 
    ELSE raw_content 
END as content_to_judge
# 有全文用全文，没全文用摘要
```

### 知乎源的正确criteria
```python
{
    "name": "知乎每日精选",  # ⚠️ 必须和数据库完全一致
    "criteria": """只保留与**人工智能、大模型、前沿科技、产业趋势**强相关的内容。
    严格排除：自然科学、生活常识、饮食文化、动物植物、情感问答。"""
}
```

### 新增源的criteria模板
```python
{
    "name": "The Verge Full Feed",
    "url": "https://www.theverge.com/rss/full.xml",
    "priority": "high",
    "criteria": """
    【重点关注 Priority Focus】
    - 全球科技巨头的AI/算力战略动向、并购、投资、组织架构调整
    - AI芯片/硬件产业的竞争格局、供应链分析
    - 重大AI产品或服务发布背后的产业逻辑
    - 科技政策对市场和企业的影响
    
    【可以接受 Acceptable】
    - 有深度产业分析的消费电子产品报道
    - 对科技行业有深远影响的技术趋势分析
    - 知名科技公司创始人的深度访谈
    
    【严格排除 Strictly Exclude】
    - 纯消费电子产品评测、游戏新闻、娱乐内容
    - 短讯类快报、无深度分析的产品发布通稿
    """
}
```

---

## 📁 项目文件清单

| 文件 | 作用 | 最后稳定版本 |
|------|------|--------------|
| `config.py` | RSS源配置 + AI筛选标准 | ✅ v2.1 (35个源) |
| `fetcher.py` | 增量抓取RSS + 全文抓取 | ✅ 增量版 v2 |
| `criteria_judge.py` | AI审阅核心 | ✅ 支持阈值调节 |
| `rebuild_standard_rss.py` | 生成标准RSS XML | ✅ feedgen版 |
| `serve_with_cache.py` | 防缓存服务器 | ✅ 解决Reeder问题 |
| `cloudflared-config.yml` | Cloudflare Tunnel配置 | ✅ 永久域名版 |
| `start_cloudflared.sh` | 启动Cloudflare Tunnel脚本 | ✅ 后台运行版 |

---

## 🚀 运维命令速查

### 日常手动更新（每周一次）
```bash
cd ~/ai_rss
source venv/bin/activate
python fetcher.py && python fetcher.py --fulltext && python criteria_judge.py && python3 rebuild_standard_rss.py
```

### 服务器启动（如果重启）
```bash
cd ~/ai_rss/output
python3 serve_with_cache.py  # 用防缓存版
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

### 检查Cloudflare Tunnel状态
```bash
export CLOUDFLARE_API_TOKEN="UfsHQTxLEjKTLCtbIZmF1bvN3HYYjXD30zhu-IaS" && cloudflared tunnel info ai-rss-tunnel
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

---

## 📊 源表现统计

| 源名称 | 状态 | 平均分 | 说明 |
|--------|------|--------|------|
| 腾讯研究院 | ✅ | 35-50 | 宏观趋势，需放宽 |
| 36氪 | ✅ | 30-45 | 快讯多，需筛选 |
| InfoQ | ✅ | 40-60 | 技术管理，质量高 |
| Google Research | ✅ | 50-70 | 高质量技术博客 |
| DeepMind | ✅ | 50-70 | 高质量技术博客 |
| Hugging Face | ✅ | 45-65 | 开源模型动态 |
| Dan Luu | ✅ | 55-75 | 深度技术分析 |
| Solidot | ✅ | 30-50 | 科技新闻 |
| 知乎每日精选 | ⚠️ | 调整中 | 需严格限制主题 |
| arXiv | ⚠️ | 20-40 | 大幅降权处理 |
| The Verge | ✅ | 调试中 | 新增源 |
| 少数派 | ✅ | 调试中 | 新增源 |
| TechCrunch | ✅ | 调试中 | 新增源 |
| OneV's Den | ✅ | 调试中 | 新增源 |
| Lifehacker | ✅ | 调试中 | 新增源 |

---

## 🔧 依赖清单

```bash
# 核心依赖
pip install feedparser requests beautifulsoup4 lxml
pip install openai python-dotenv jinja2
pip install trafilatura readability-lxml newspaper3k goose3
pip install feedgen  # 新增，用于生成标准RSS

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
- **服务器进程 PID**：39479 (Flask应用)
- **隧道进程 PID**：49919 (Cloudflare Tunnel)
- **下次重启后**：只需运行`./start_cloudflared.sh`即可恢复

---

## 📝 待办事项

| 事项 | 优先级 | 说明 |
|------|--------|------|
| ✅ **绑定永久域名** | 已完成 | 使用rss.borntofly.ai |
| 加入时间过滤（只保留1年内文章） | ⭐⭐ | 避免旧文章占位 |
| 设置定时任务（每6小时） | ⭐ | 目前手动更新够用 |
| 给儿子做视频RSS | ⭐ | 等当前系统稳定后 |

---

## 🎯 核心原则

> **"宁可漏判，不可误杀"**

- 精简"严格排除"项
- 增加"可以接受"缓冲层
- 避免因标准过严错失好内容
- 阈值设为40分，平衡质量与数量

---

## 🔄 项目状态检查清单

### 每日检查
1. [ ] 检查Flask应用是否运行：`ps aux | grep python.*app`
2. [ ] 检查Cloudflare Tunnel是否运行：`ps aux | grep cloudflared`
3. [ ] 测试永久地址访问：`curl -I https://rss.borntofly.ai/feed.xml`
4. [ ] 检查数据库文章数量：`sqlite3 data/ai_rss.db "SELECT COUNT(*) FROM articles WHERE criteria_score >= 40;"`

### 每周更新
1. [ ] 运行增量抓取：`python fetcher.py`
2. [ ] 运行全文抓取：`python fetcher.py --fulltext`
3. [ ] 运行AI评分：`python criteria_judge.py`
4. [ ] 重新生成RSS：`python3 rebuild_standard_rss.py`

---

**这份文档记录了AI RSS项目的完整演进历程和所有关键决策。在开始任何新任务前，请先阅读此文档了解项目状态和历史经验。**