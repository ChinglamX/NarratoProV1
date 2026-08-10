PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
PYTHON_BOOTSTRAP ?= pyenv exec python

.PHONY: setup format lint type test security check api worker context-check infra-up infra-down infra-accept

setup:
	$(PYTHON_BOOTSTRAP) -m venv .venv
	$(PIP) install -e '.[dev]'

format:
	.venv/bin/ruff format .
	.venv/bin/ruff check --fix .

lint:
	.venv/bin/ruff format --check .
	.venv/bin/ruff check .

type:
	.venv/bin/mypy

test:
	$(PYTHON) -m pytest --cov --cov-report=term-missing

security:
	.venv/bin/bandit -q -r apps packages workflows scripts

context-check:
	$(PYTHON) scripts/check_context_integrity.py
	$(PYTHON) scripts/check_architecture.py

check: lint type test security context-check

api:
	$(PYTHON) -m apps.api.main

worker:
	$(PYTHON) -m apps.worker.main

infra-up:
	docker compose --env-file deploy/compose/.env.example -f deploy/compose/docker-compose.yml up -d

infra-down:
	docker compose --env-file deploy/compose/.env.example -f deploy/compose/docker-compose.yml down

infra-accept:
	$(PYTHON) scripts/accept_local_infra.py
