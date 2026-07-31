# Developer shortcuts. The venv interpreter is the default; override with
# `make PY=python3 test` if needed.
PY ?= .venv/bin/python

.PHONY: help check compile lint test run restart logs status migrate css

help:
	@echo "Develop:"
	@echo "  make check    - compile + lint + tests (run this before committing)"
	@echo "  make test     - run the pytest suite (needs the compose db running)"
	@echo "  make lint     - ruff over the codebase"
	@echo "  make compile  - byte-compile the Python sources"
	@echo "  make run      - start a dev server in this terminal on 127.0.0.1:8000"
	@echo ""
	@echo "Live service on this box:"
	@echo "  make restart  - apply edited code (compile-check, restart, health-check)"
	@echo "  make status   - is it up?"
	@echo "  make logs     - follow the app journal"

check: compile lint test

# Every app subpackage level — a syntax error anywhere
# must fail the gate before it can crash the live service.
compile:
	$(PY) -m py_compile app/*.py app/*/*.py app/*/*/*.py

lint:
	$(PY) -m ruff check .

# Tests create/drop a throwaway renews_test database on the compose Postgres,
# so `docker compose up -d db` must be running (it always is on this box).
test:
	$(PY) -m pytest -q

run:
	$(PY) -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Apply pending schema migrations (renews.service also does this on start)
migrate:
	.venv/bin/alembic -c alembic/alembic.ini upgrade head

# Regenerate the static Tailwind build after changing classes in templates/JS
css:
	tailwindcss -c static/tailwind.config.js -i static/css/tailwind.src.css -o static/css/tailwind.css --minify

# The dev loop for the live service: edit files, then `make restart`.
# Compile-checks first so a typo cannot take the site down, health-checks after.
restart:
	$(PY) -m py_compile app/*.py app/*/*.py app/*/*/*.py
	systemctl restart renews
	@# init_db runs in ExecStartPre, so the port takes a few seconds to bind
	@for i in $$(seq 1 15); do \
		curl -sf http://127.0.0.1:8000/health >/dev/null && echo "health: ok" && exit 0; \
		sleep 1; \
	done; \
	echo "health check FAILED"; journalctl -u renews -n 20 --no-pager; exit 1

status:
	@systemctl status renews --no-pager | head -12

logs:
	journalctl -u renews -n 50 -f
