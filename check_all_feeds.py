#!/usr/bin/env python3
# check_all_feeds.py - RSS源健康诊断工具
import sys
import time
import requests
import feedparser
from datetime import datetime

# 导入你的配置
try:
    import config
except ImportError:
    print("❌ 错误: 找不到 config.py，请确保你在 smart_rss 目录下")
    sys.exit(1)

# ============ 配置 ============
TIMEOUT = 15          # 每个源超时时间（秒）
DELAY = 1.5           # 源之间延迟，避免被ban
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

# 颜色输出（终端友好）
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_color(text, color):
    print(f"{color}{text}{RESET}")

def test_feed(url, name):
    """测试单个RSS源，返回详细诊断信息"""
    result = {
        "name": name,
        "url": url,
        "status": "unknown",
        "status_code": None,
        "articles": 0,
        "error": None,
        "response_time": None,
        "feed_type": None,
        "latest_title": None
    }
    
    # 1. 基础网络连通性测试
    try:
        start = time.time()
        headers = {'User-Agent': USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
        result["response_time"] = round(time.time() - start, 2)
        result["status_code"] = resp.status_code
        
        if resp.status_code != 200:
            result["status"] = "http_error"
            result["error"] = f"HTTP {resp.status_code}"
            return result
    except requests.exceptions.Timeout:
        result["status"] = "timeout"
        result["error"] = "连接超时（15秒）"
        return result
    except requests.exceptions.SSLError as e:
        result["status"] = "ssl_error"
        result["error"] = f"SSL证书错误: {str(e)[:50]}"
        return result
    except requests.exceptions.ConnectionError as e:
        result["status"] = "connection_error"
        result["error"] = f"连接失败: {str(e)[:50]}"
        return result
    except Exception as e:
        result["status"] = "network_error"
        result["error"] = str(e)[:100]
        return result
    
    # 2. RSS解析测试
    try:
        feed = feedparser.parse(resp.content)
        
        # 检查是否是有效的RSS/Atom
        if hasattr(feed, 'version') and feed.version:
            result["feed_type"] = feed.version
        elif hasattr(feed, 'namespaces') and feed.namespaces:
            result["feed_type"] = "Atom"
        else:
            result["feed_type"] = "unknown"
        
        # 检查是否有文章
        if hasattr(feed, 'entries'):
            result["articles"] = len(feed.entries)
            if feed.entries and len(feed.entries) > 0:
                latest = feed.entries[0]
                if hasattr(latest, 'title'):
                    result["latest_title"] = latest.title[:80] + "..." if len(latest.title) > 80 else latest.title
        
        # 判断整体状态
        if feed.bozo and feed.bozo_exception:
            # 有解析警告，但可能仍可用
            result["status"] = "warning"
            result["error"] = f"解析警告: {str(feed.bozo_exception)[:100]}"
        elif result["articles"] > 0:
            result["status"] = "ok"
        else:
            result["status"] = "no_articles"
            result["error"] = "没有解析到任何文章"
            
    except Exception as e:
        result["status"] = "parse_error"
        result["error"] = f"解析失败: {str(e)[:100]}"
    
    return result

def main():
    print("\n" + "=" * 80)
    print_color("🔍 RSS源健康诊断工具", BLUE)
    print_color(f"⏱️  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", BLUE)
    print("=" * 80)
    
    all_feeds = config.RSS_FEEDS
    feeds = [f for f in all_feeds if f.get("enabled", True) is not False]
    skipped = len(all_feeds) - len(feeds)
    print(f"📡 待测源总数: {len(feeds)} 个（已跳过 {skipped} 个禁用源）\n")
    
    results = []
    working = []
    failed = []
    warning = []
    
    for i, feed in enumerate(feeds, 1):
        name = feed.get('name', '未命名')
        url = feed.get('url', '')
        
        print(f"[{i:2d}/{len(feeds)}] 📍 {name[:40]:<40} ", end='', flush=True)
        
        result = test_feed(url, name)
        results.append(result)
        
        # 输出状态
        if result["status"] == "ok":
            print_color(f"✅ 成功", GREEN)
            working.append(result)
        elif result["status"] == "warning":
            print_color(f"⚠️  警告", YELLOW)
            warning.append(result)
        else:
            print_color(f"❌ 失败", RED)
            failed.append(result)
        
        # 输出详细信息（缩进）
        print(f"     ├─ URL: {url[:80]}...")
        if result["status_code"]:
            print(f"     ├─ HTTP状态: {result['status_code']}")
        if result["response_time"]:
            print(f"     ├─ 响应时间: {result['response_time']}秒")
        if result["feed_type"]:
            print(f"     ├─ Feed类型: {result['feed_type']}")
        if result["articles"] > 0:
            print(f"     ├─ 文章数量: {result['articles']}篇")
        if result["latest_title"]:
            print(f"     ├─ 最新文章: {result['latest_title'][:60]}...")
        if result["error"]:
            print(f"     └─ ❗ 错误信息: {result['error']}")
        else:
            print(f"     └─ ✅ 状态正常")
        
        # 源之间延迟
        if i < len(feeds):
            time.sleep(DELAY)
        print()
    
    # ============ 汇总报告 ============
    print("=" * 80)
    print_color("📊 诊断汇总报告", BLUE)
    print("=" * 80)
    
    print(f"\n✅ 完全可用: {len(working)} 个")
    for w in working[:10]:  # 只显示前10个
        print(f"   • {w['name']}: {w['articles']}篇文章")
    if len(working) > 10:
        print(f"     ... 还有 {len(working)-10} 个")
    
    if warning:
        print(f"\n⚠️  有警告（可能可用但建议检查）: {len(warning)} 个")
        for w in warning:
            print(f"   • {w['name']}")
            print(f"     ├─ URL: {w['url']}")
            print(f"     └─ 问题: {w['error']}")
    
    if failed:
        print(f"\n❌ 完全失败: {len(failed)} 个")
        for f in failed:
            print(f"   • {f['name']}")
            print(f"     ├─ URL: {f['url']}")
            print(f"     └─ 原因: {f['error']}")
    
    # ============ 生成可用的config片段 ============
    print("\n" + "=" * 80)
    print_color("🛠️  可用源配置生成", BLUE)
    print("=" * 80)
    
    if working or warning:
        print("\n📋 以下是可以直接使用的源（复制到config.py）:\n")
        print("RSS_FEEDS = [")
        
        # 先输出完全可用的
        for w in working:
            # 从原config找到对应的完整配置
            original = next((f for f in feeds if f['url'] == w['url']), None)
            if original:
                print(f"    {original},")
        
        # 再输出有警告但可能可用的
        for w in warning:
            original = next((f for f in feeds if f['url'] == w['url']), None)
            if original:
                print(f"    # 有解析警告，但可能可用")
                print(f"    {original},")
        
        print("]")
    else:
        print("\n❌ 没有可用的源，请检查网络或更换源")
    
    # ============ 建议 ============
    print("\n" + "=" * 80)
    print_color("💡 后续建议", BLUE)
    print("=" * 80)
    
    if failed:
        print(f"\n1. 失败的 {len(failed)} 个源需要替换或删除")
        print("   可以在浏览器中手动打开URL，确认是否真的失效")
    
    if warning:
        print(f"\n2. 有警告的 {len(warning)} 个源建议观察几天")
        print("   如果频繁出现抓取失败，考虑替换")
    
    print(f"\n3. 建议每季度运行一次这个诊断脚本")
    print("   命令: python check_all_feeds.py")
    
    print("\n" + "=" * 80)
    print_color("🏁 诊断完成", BLUE)
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
