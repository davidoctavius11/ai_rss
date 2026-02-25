.PHONY: venv deps db fetch fulltext judge run run-simple health health-all

VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

venv:
	python3 -m venv $(VENV)

deps: venv
	$(PIP) install -r requirements.txt

db:
	$(PY) db.py

fetch:
	$(PY) fetcher.py

fulltext:
	$(PY) fulltext_fetcher.py --days 90 --limit 120

judge:
	$(PY) criteria_judge.py --threshold 50

run:
	$(PY) app_ai_filtered.py

run-simple:
	$(PY) app_simple.py

health:
	$(PY) check_feeds.py

health-all:
	$(PY) check_all_feeds.py
