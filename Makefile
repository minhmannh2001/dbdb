# DBDB rebuild — common commands (see README.md).
PYTHON3 ?= python3
PIP ?= ./.venv/bin/pip
PYTEST ?= ./.venv/bin/pytest

.PHONY: venv install test

venv:
	$(PYTHON3) -m venv .venv
	$(PIP) install -U pip

install: venv
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

test:
	$(PYTEST) -q

benchmark:
	./.venv/bin/python benchmark.py
