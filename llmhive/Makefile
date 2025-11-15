.PHONY: dev test fmt run-local migrate

VENV?=.venv

setup:
	python -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -e .[dev]

dev: setup

test:
	pytest

fmt:
	@echo "Formatting is handled by your preferred tool (e.g. black, ruff)."

run-local:
	uvicorn llmhive.app.main:app --host 0.0.0.0 --port 8080 --reload

migrate:
	alembic upgrade head
