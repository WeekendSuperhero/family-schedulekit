PY ?= python3.13
PIP := $(PY) -m pip
VENV := .venv
ACT := . $(VENV)/bin/activate &&

.PHONY: help venv install dev test lint fmt week day build publish clean init-config list-templates resolve-week

help:
	@echo "Targets:"
	@echo "  venv          - Create a Python 3.13 virtualenv"
	@echo "  install       - Install package (runtime deps)"
	@echo "  dev           - Install with dev deps (pytest, ruff, mypy)"
	@echo "  test          - Run pytest"
	@echo "  lint          - Ruff lint"
	@echo "  fmt           - Ruff format"
	@echo "  week          - Resolve ISO week: make week DATE=YYYY-MM-DD [CFG=...]"
	@echo "  day           - Resolve date:    make day  DATE=YYYY-MM-DD [CFG=...]"
	@echo "  init-config   - Generate config: make init-config MOM=... DAD=... CHILD=... [OUT=...]"
	@echo "  list-templates- Show packaged templates"
	@echo "  build         - Build wheel+sdist"
	@echo "  publish       - Upload dist/* to PyPI (manual)"
	@echo "  clean         - Remove build artifacts"

venv:
	$(PY) -m venv $(VENV)

install: venv
	$(ACT) $(PIP) install -U pip
	$(ACT) $(PIP) install -e .

dev: venv
	$(ACT) $(PIP) install -U pip
	$(ACT) $(PIP) install -e .[dev]

test:
	$(ACT) pytest

lint:
	$(ACT) ruff check .

fmt:
	$(ACT) ruff format .

week:
	@if [ -z "$(DATE)" ]; then echo "Usage: make week DATE=YYYY-MM-DD [CFG=path.json]"; exit 2; fi
	$(ACT) family-schedulekit resolve --week-of $(DATE) $(if $(CFG),--config $(CFG),)

day:
	@if [ -z "$(DATE)" ]; then echo "Usage: make day DATE=YYYY-MM-DD [CFG=path.json]"; exit 2; fi
	$(ACT) family-schedulekit resolve $(DATE) $(if $(CFG),--config $(CFG),)

init-config:
	@if [ -z "$(MOM)" ] || [ -z "$(DAD)" ]; then echo "Usage: make init-config MOM='ParentA' DAD='ParentB' CHILD='Child1' [CHILD2='Child2'] [OUT=schema/my.json] [TEMPLATE=generic]"; exit 2; fi
	$(ACT) family-schedulekit init --mom "$(MOM)" --dad "$(DAD)" \
		$(if $(CHILD),--child "$(CHILD)",) \
		$(if $(CHILD2),--child "$(CHILD2)",) \
		$(if $(CHILD3),--child "$(CHILD3)",) \
		--template $(if $(TEMPLATE),$(TEMPLATE),generic) \
		-o $(if $(OUT),$(OUT),schema/my-schedule.json) -f

list-templates:
	$(ACT) family-schedulekit list-templates

build:
	$(ACT) $(PIP) install -U build
	$(ACT) $(PY) -m build

publish:
	@echo ">>> Ensure TWINE_USERNAME='__token__' and TWINE_PASSWORD are set"
	$(ACT) $(PIP) install -U twine
	$(ACT) $(PY) -m twine upload dist/*

export:
	@if [ -z "$(START)" ]; then echo "Usage: make export START=YYYY-MM-DD [WEEKS=12] [CFG=schema/example-schedule.json] [OUT=out] [FMTS='csv json jsonl ics md']"; exit 2; fi
	$(ACT) family-schedulekit export --start $(START) --weeks $(if $(WEEKS),$(WEEKS),12) \
		--config $(if $(CFG),$(CFG),schema/example-schedule.json) \
		--outdir $(if $(OUT),$(OUT),out) --formats $(if $(FMTS),$(FMTS),csv json jsonl ics md)

resolve-week:
	@if [ -z "$(DATE)" ]; then echo "Usage: make resolve-week DATE=YYYY-MM-DD [CFG=path.json]"; exit 2; fi
	$(ACT) family-schedulekit resolve --week-of $(DATE) $(if $(CFG),--config $(CFG),)

clean:
	rm -rf $(VENV) build/ dist/ *.egg-info .pytest_cache/ __pycache__ **/__pycache__
