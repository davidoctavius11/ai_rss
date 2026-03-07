# AI RSS — Codex Agent Guide

This file is read automatically by Codex at startup. Follow every rule here.

---

## Runtime: you are talking to DeepSeek, not OpenAI

All your API calls go through a local proxy (`deepseek-proxy.py`) running on
`http://localhost:3000`. That proxy translates your requests to the DeepSeek
Chat Completions API. Consequences:

- **Model in use**: `deepseek-chat` (regardless of what the config says)
- **Supported message roles**: `system`, `user`, `assistant`, `tool` only.
  The proxy remaps `developer` → `system` automatically, but do not rely on
  OpenAI-specific roles or features.
- **No vision, no function-calling schema differences**: stick to plain text
  tool calls and text responses.

---

## Proxy: deepseek-proxy.py

| What | Detail |
|------|--------|
| File | `/Users/ioumvp/ai_rss/deepseek-proxy.py` |
| Port | `3000` |
| Managed by | macOS launchd (`com.ioumvp.deepseek-proxy`) — auto-starts at login |
| Logs | `~/Library/Logs/deepseek-proxy.log` |
| Health check | `curl http://localhost:3000/health` → `{"status":"ok"}` |

**Do not start or stop the proxy manually.** It is always running.
If `curl http://localhost:3000/health` fails, tell the user to run:
```
launchctl load ~/Library/LaunchAgents/com.ioumvp.deepseek-proxy.plist
```

### Known pitfalls fixed in the proxy (do not regress)
1. **Role remapping** — `developer` and `latest_reminder` roles are mapped to
   `system`. DeepSeek rejects unknown roles with `invalid_request_error`.
2. **SSE format translation** — Codex expects Responses API events
   (`response.output_text.delta`, `response.completed`, …). DeepSeek returns
   Chat Completions chunks. The proxy translates between them.
3. **Timeout** — upstream timeout is 120 s (env `UPSTREAM_TIMEOUT`).
4. **No buffering** — responses include `Cache-Control: no-cache` and
   `X-Accel-Buffering: no`.

---

## Project layout

```
ai_rss/
├── deepseek-proxy.py       # Codex↔DeepSeek translation proxy
├── config.py               # 58 RSS feed sources with per-feed criteria
├── fetcher.py              # RSS fetch + DB write
├── fulltext_fetcher.py     # Full-text scraping (browser UA spoofing)
├── criteria_judge.py       # AI scoring (0-100) + learning resonance injection
├── multi_perspective.py    # Cluster-based story synthesis (strategic/execution/cross-media)
├── app_ai_filtered.py      # Flask app: /feed, /item/<id>, /summary
├── generator.py            # RSS XML builder (_strip_markdown, _mp_block, _story_note)
├── podcast_pipeline.py     # Podcast generation pipeline
├── db.py                   # DB schema + init
├── data/ai_rss.db          # SQLite: articles + multi_perspectives tables
├── scripts/auto_refresh.sh # Cron script: fetch → fulltext → score → synthesize → restart
├── PRACTICE_HISTORY.md     # Full project evolution log (read this first)
└── ARCHITECTURE.md         # Mermaid system diagram
```

Cross-project knowledge log (outside this folder):
```
~/Agents/knowledge_log/
├── concepts.json           # 11 domain concepts from real project work (Ebbinghaus schedule)
└── projects/ai_rss.md      # CTO-level debrief: decisions, gotchas, future direction
```

---

## Environment

- Python: `/opt/homebrew/bin/python3` (3.14)
- Virtualenv: `venv/` (activate before running scripts)
- **IMPORTANT**: The shell has stale env vars (`DEEPSEEK_API_KEY`, `OPENAI_API_KEY=anything`) set in `~/.zshrc` that are WRONG. Always read credentials directly from `.env` using `dotenv_values()`, never `os.getenv()` for API keys.
- `.env` in project root is the source of truth: `OPENAI_API_KEY` (real DeepSeek key), `OPENAI_BASE_URL=https://api.deepseek.com/v1`

```python
# Correct pattern (used in criteria_judge.py and multi_perspective.py):
from dotenv import dotenv_values
_env = dotenv_values(os.path.join(os.path.dirname(__file__), '.env'))
client = OpenAI(
    api_key=_env.get('DEEPSEEK_API_KEY') or _env.get('OPENAI_API_KEY'),
    base_url=_env.get('OPENAI_BASE_URL', 'https://api.deepseek.com/v1')
)
```

---

## Key constants (app_ai_filtered.py)

| Constant | Value | Meaning |
|---|---|---|
| `FILTER_THRESHOLD` | 50 | Min score to include article in feed |
| `RECENCY_DAYS` | 90 | Max article age (unless evergreen) |
| `EVERGREEN_SCORE` | 80 | Score threshold to override age limit |

---

## Database schema

**`articles`** table key columns:
- `id`, `feed_name`, `article_title`, `article_link`, `published_date`
- `raw_content` — RSS summary, `content` — full text (scraped)
- `criteria_score` (0-100), `criteria_reason` (includes learning resonance if set)
- `fulltext_fetched` (bool)

**`multi_perspectives`** table:
- `article_link` (UNIQUE), `article_title`, `summary` (synthesis text), `cluster_json` (JSON array of contributing articles)

---

## Learning system (added 2026-03-07)

The RSS feed doubles as a daily learning surface. `criteria_judge.py` loads `~/Agents/knowledge_log/concepts.json` and weaves a learning connection into the `criteria_reason` for relevant articles:

> *"文章深入分析了容器CPU配额问题 — 与我们用LaunchAgents管理进程的实践相关，都涉及资源分配和进程控制"*

`multi_perspective.py` similarly injects the knowledge context into the synthesis prompt, producing an optional "与我们项目的关联" paragraph when relevant.

**Future direction**: Unify `criteria_reason` + `multi_perspective summary` into a single holistic AI-generated brief per article. The multi-view structure (战略层面 / 执行层面 / 延伸思考) is preserved and loved — it gets carried into the unified brief, not replaced.

---

## Common commands

```bash
# Fetch new articles
python fetcher.py

# Score unscored articles
python criteria_judge.py --threshold 50

# Fetch full text then score (default)
python criteria_judge.py

# Generate multi-perspective syntheses (run after scoring)
python multi_perspective.py

# Start the web app locally
python app_ai_filtered.py   # → http://localhost:5006

# Restart via LaunchAgent (preferred)
launchctl unload ~/Library/LaunchAgents/com.ioumvp.ai-rss-app.plist
launchctl load  ~/Library/LaunchAgents/com.ioumvp.ai-rss-app.plist

# Warm the public feed
curl -s https://rss.borntofly.ai/feed | grep -c "<item>"

# Check all feeds health
python check_all_feeds.py
```

---

## Common gotchas

- `sqlite3.Row` has no `.get()` — use `row['col']` direct indexing
- `ALTER TABLE ADD COLUMN`: wrap in `try/except` for idempotency
- RSS clients (Reeder) sort by `pubDate`, not XML entry order — can't control display order server-side
- Markdown shows raw in RSS (`###`, `**`) — always call `_strip_markdown()` before inserting into feed descriptions
- LaunchAgent reload: unload first, then load (not restart)
- `sleep` on macOS: `sleep 2 && cmd` works; `sleep 2s` does not

---

## What NOT to do

- Do not commit `.env`, `data/`, `output/`, or `*.log`
- Do not change `api_base` in `~/.codex/config.toml` — it must stay `http://localhost:3000/v1`
- Do not use `os.getenv()` for API keys — use `dotenv_values()` (stale shell vars will override)
- Do not add OpenAI-only features (Assistants API, Batch API, vision) — DeepSeek won't support them
- Do not install packages globally — use the `venv`
- Do not append new sections to RSS descriptions — integrate learning notes into existing fields
