.PHONY: install data sql run test lint

install:
	pip install -e ".[dev]"

data:
	python scripts/download_data.py

sql:              ## answer the SQL questions -> reports/sql_answers.md
	python -m airq.db

run:              ## SQL + forecasts + figures -> reports/ (~1 min)
	python -m airq.pipeline

test:
	pytest -q

lint:
	ruff check src tests scripts
	ruff format --check src tests scripts
