.PHONY: install check migrate seed-demo serve test-browser
install:
	uv sync --locked
	uv run --locked python scripts/configure.py
check:
	uv run --locked ruff check src tests scripts alembic
	uv run --locked ruff format --check src tests scripts alembic
	uv run --locked mypy
	uv run --locked pytest
migrate:
	uv run --locked crous-queue migrate
seed-demo:
	uv run --locked python scripts/seed_demo.py
serve:
	uv run --locked crous-queue serve
test-browser:
	uv run --locked pytest tests/browser
