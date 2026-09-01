PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
PYTHON_BOOTSTRAP ?= pyenv exec python

.PHONY: setup format lint type test security check schemas schema-check api worker context-check infra-up infra-down infra-accept personal-cut-check personal-cut

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

schemas:
	$(PYTHON) scripts/generate_contracts.py

schema-check:
	$(PYTHON) scripts/generate_contracts.py --check

check: lint type test security context-check schema-check

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

personal-cut-check:
	$(PYTHON) scripts/personal_cut.py --config product/personal_cut.example.json

personal-cut:
	$(PYTHON) scripts/personal_cut.py --config product/personal_cut.example.json --run
