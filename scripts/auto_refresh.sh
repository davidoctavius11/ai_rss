#!/usr/bin/env bash
set -euo pipefail

# Auto refresh pipeline (横纵研究所版):
# fetch → fulltext → judge → identify research objects → restart app → warm feed

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="$ROOT_DIR/venv/bin/python3"

echo "[auto] $(date) start"

# Pull latest code from GitHub so new routes / fixes take effect automatically
git -C "$ROOT_DIR" pull --ff-only origin main 2>&1 | head -5 || echo "[auto] git pull skipped"

# Hardcode venv python — cron doesn't load ~/.zshrc so PATH-based lookups fail
PY="/Users/ioumvp/ai_rss/venv/bin/python"

# DeepSeek API key — must be set explicitly since cron has no shell env
export DEEPSEEK_API_KEY="sk-7bccd90533ef4ee4a15d323fd4ff8439"
export OPENAI_API_KEY="$DEEPSEEK_API_KEY"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"

# Proxy (GUI VPN): set both HTTP and SOCKS for Python requests
export HTTP_PROXY="http://127.0.0.1:10080"
export HTTPS_PROXY="http://127.0.0.1:10080"

# 1) Fetch latest articles
$PY fetcher.py

# 2) Fulltext for recent articles (improves scoring)
$PY fulltext_fetcher.py --days 90 --limit 200

# 3) Score with threshold 50
$PY criteria_judge.py --threshold 50

# 3a) Per-feed scoring for new sources (community + Chinese tech media)
for FEED in \
    jd-36kr jd-geekpark jd-ifanr jd-ruanyifeng jd-juejin-ai jd-linux-do \
    jd-v2ex jd-sspai jd-reddit-ml jd-reddit-localllama jd-reddit-artificial \
    jd-producthunt-ai jd-devto-ai jd-huggingface-blog \
    jd-lobsters-ai jd-hn-showhn; do
    $PY criteria_judge.py --feed "$FEED" 2>/dev/null || true
done

# 3.5) Multi-perspective synthesis (CTO/CEO focused)
# Skip failures here (e.g., missing/invalid API key) so refresh still completes.
$PY multi_perspective.py || echo "[auto] multi_perspective skipped (error)"

# 4) Restart app_simple.py (main public app — port 5005, Cloudflare tunnel target)
pkill -f "app_simple.py" || true
sleep 1
nohup $PY "$ROOT_DIR/app_simple.py" > "$ROOT_DIR/app_simple.log" 2>&1 &

# 5) Restart app_ai_filtered.py (secondary feed service — port 5006)
pkill -f "app_ai_filtered.py" || true
nohup $PY app_ai_filtered.py > app_ai_filtered.log 2>&1 &

# 6) Warm the feed cache
curl -s "http://localhost:5005/jd" >/dev/null || true
curl -s "http://localhost:5006/feed.xml?refresh=1" >/dev/null || true

echo "[auto] $(date) done"
