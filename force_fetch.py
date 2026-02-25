#!/usr/bin/env python3
import sqlite3
import subprocess
import sys

print("🔄 强制重新抓取所有源...")

# 备份当前数据库
subprocess.run(["cp", "data/ai_rss.db", "data/ai_rss.db.backup"])

# 运行抓取（这里假设fetcher.py可以接受--force参数）
# 如果不支持，可能需要临时修改fetcher.py
result = subprocess.run([sys.executable, "fetcher.py", "--force"], 
                       capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("错误:", result.stderr)

# 抓取全文
result = subprocess.run([sys.executable, "fetcher.py", "--fulltext", "--force"], 
                       capture_output=True, text=True)
print(result.stdout)

# 重新审阅
result = subprocess.run([sys.executable, "criteria_judge.py"], 
                       capture_output=True, text=True)
print(result.stdout)

# 生成RSS
result = subprocess.run([sys.executable, "rebuild_feed.py"], 
                       capture_output=True, text=True)
print(result.stdout)

print("✅ 完成！")
