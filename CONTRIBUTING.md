# Contributing

Thanks for helping improve this project.

## Workflow
1. Create a feature branch from `main`.
2. Make focused changes.
3. Run the basic checks (see below).
4. Open a PR with a clear description and screenshots/logs if relevant.

## Local Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy configs:
   - `cp config.example.py config.py`
   - `cp .env.example .env`
4. Initialize DB:
   - `python3 db.py`

## Basic Checks
- Health check: `python3 check_all_feeds.py`
- Fetch: `python3 fetcher.py`
- Fulltext (optional): `python3 fulltext_fetcher.py --days 90 --limit 50`
- Judge: `python3 criteria_judge.py --threshold 50`

## Notes
- Do not commit `.env`, `data/`, `output/`, or logs.
- Keep changes small and composable.
