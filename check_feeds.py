import config
from fetcher import fetch_articles_from_feed

print("🔍 RSS源可用性诊断")
print("=" * 60)

working = []
broken = []

for feed in config.RSS_FEEDS:
    if feed.get("enabled", True) is False:
        print(f"\n📡 跳过（已禁用）: {feed['name']}")
        continue
    print(f"\n📡 测试: {feed['name']}")
    print(f"   URL: {feed['url']}")
    
    articles = fetch_articles_from_feed(feed['url'], feed['name'])
    
    if articles:
        print(f"   ✅ 成功! 抓取到 {len(articles)} 篇文章")
        print(f"   最新: {articles[0]['title'][:60]}...")
        working.append(feed['name'])
    else:
        print(f"   ❌ 失败")
        broken.append(feed['name'])

print("\n" + "=" * 60)
print("📊 诊断结果:")
print(f"   ✅ 可用源 ({len(working)}): {', '.join(working) if working else '无'}")
print(f"   ❌ 不可用源 ({len(broken)}): {', '.join(broken) if broken else '无'}")
print("=" * 60)
