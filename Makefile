.PHONY: check test

check:
	uv run ruff format .
	uv run ruff check .
	uv run pytest

test:
	uv run pytest