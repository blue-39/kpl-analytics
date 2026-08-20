.PHONY: install demo backfill build-data audit api web test

install:
	python3 -m venv .venv
	.venv/bin/pip install -e '.[dev]'
	cd frontend && pnpm install

demo:
	.venv/bin/kpl-analytics seed-demo

backfill:
	.venv/bin/kpl-analytics backfill --days 730

build-data:
	.venv/bin/kpl-analytics build

audit:
	.venv/bin/kpl-analytics audit

api:
	.venv/bin/kpl-analytics serve --reload

web:
	cd frontend && pnpm run dev

test:
	.venv/bin/ruff check .
	.venv/bin/pytest -q
	cd frontend && pnpm run lint && pnpm test
