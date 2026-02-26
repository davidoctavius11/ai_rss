#!/usr/bin/env bash
set -euo pipefail

# Auto refresh pipeline: fetch -> fulltext -> judge -> restart app -> warm feed

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[auto] $(date) start"

# 1) Fetch latest articles
python3 fetcher.py

# 2) Fulltext for recent articles (improves scoring)
python3 fulltext_fetcher.py --days 90 --limit 200

# 3) Score with threshold 50
python3 criteria_judge.py --threshold 50

# 3.5) Multi-perspective synthesis (CTO/CEO focused)
python3 multi_perspective.py

# 4) Restart service
pkill -f "python3 app_ai_filtered.py" || true
nohup python3 app_ai_filtered.py > app_ai_filtered.log 2>&1 &

# 5) Warm the feed
curl -s "http://localhost:5006/feed.xml?refresh=1" >/dev/null || true

echo "[auto] $(date) done"
