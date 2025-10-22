UV := $(shell command -v uv 2>/dev/null)
PY ?= python3.13
VENV := .venv

.PHONY: help venv install dev test lint fmt week day build publish clean init-config list-templates resolve-week export

help:
	@echo "Targets:"
	@echo "  venv          - Prepare project environment"
	@echo "  install       - Install runtime deps"
	@echo "  dev           - Install dev deps (pytest, ruff, mypy, Pillow)"
	@echo "  test          - Run pytest"
	@echo "  lint          - Ruff lint"
	@echo "  fmt           - Ruff format"
	@echo "  week          - Resolve ISO week: make week DATE=YYYY-MM-DD [CFG=...]"
	@echo "  day           - Resolve date:    make day  DATE=YYYY-MM-DD [CFG=...]"
	@echo "  init-config   - Generate config: make init-config MOM=... DAD=... CHILD=... [OUT=...]"
	@echo "  list-templates- Show packaged templates"
	@echo "  build         - Build wheel+sdist"
	@echo "  publish       - Upload dist/* to PyPI (manual)"
	@echo "  export        - Export schedule artifacts"
	@echo "  clean         - Remove build artifacts"

ifeq ($(UV),)

venv:
	$(PY) -m venv $(VENV)

install: venv
	. $(VENV)/bin/activate && pip install -U pip && pip install -e .

dev: venv
	. $(VENV)/bin/activate && pip install -U pip && pip install -e .[dev]

test:
	. $(VENV)/bin/activate && pytest

lint:
	. $(VENV)/bin/activate && ruff check .

fmt:
	. $(VENV)/bin/activate && ruff format .

week:
	@if [ -z "$(DATE)" ]; then echo "Usage: make week DATE=YYYY-MM-DD [CFG=path.json]"; exit 2; fi
	. $(VENV)/bin/activate && family-schedulekit resolve --week-of $(DATE) $(if $(CFG),--config $(CFG),)

day:
	@if [ -z "$(DATE)" ]; then echo "Usage: make day DATE=YYYY-MM-DD [CFG=path.json]"; exit 2; fi
	. $(VENV)/bin/activate && family-schedulekit resolve $(DATE) $(if $(CFG),--config $(CFG),)

init-config:
	@if [ -z "$(MOM)" ] || [ -z "$(DAD)" ]; then echo "Usage: make init-config MOM='ParentA' DAD='ParentB' CHILD='Child1' [CHILD2='Child2'] [OUT=schema/my.json] [TEMPLATE=generic]"; exit 2; fi
	. $(VENV)/bin/activate && family-schedulekit init --mom "$(MOM)" --dad "$(DAD)" \
		$(if $(CHILD),--child "$(CHILD)",) \
		$(if $(CHILD2),--child "$(CHILD2)",) \
		$(if $(CHILD3),--child "$(CHILD3)",) \
		--template $(if $(TEMPLATE),$(TEMPLATE),generic) \
		-o $(if $(OUT),$(OUT),schema/my-schedule.json) -f

list-templates:
	. $(VENV)/bin/activate && family-schedulekit list-templates

build:
	. $(VENV)/bin/activate && pip install -U build && python -m build

publish:
	@echo ">>> Ensure TWINE_USERNAME='__token__' and TWINE_PASSWORD are set"
	. $(VENV)/bin/activate && pip install -U twine && python -m twine upload dist/*

export:
	@if [ -z "$(START)" ]; then echo "Usage: make export START=YYYY-MM-DD [WEEKS=12] [CFG=schema/example-schedule.json] [OUT=out] [FMTS='csv json jsonl ics md']"; exit 2; fi
	. $(VENV)/bin/activate && family-schedulekit export --start $(START) --weeks $(if $(WEEKS),$(WEEKS),12) \
		--config $(if $(CFG),$(CFG),schema/example-schedule.json) \
		--outdir $(if $(OUT),$(OUT),out) --formats $(if $(FMTS),$(FMTS),csv json jsonl ics md)

resolve-week:
	@if [ -z "$(DATE)" ]; then echo "Usage: make resolve-week DATE=YYYY-MM-DD [CFG=path.json]"; exit 2; fi
	. $(VENV)/bin/activate && family-schedulekit resolve --week-of $(DATE) $(if $(CFG),--config $(CFG),)

else

venv:
	$(UV) sync

install: venv
	@echo "uv sync complete (runtime deps)"

dev:
	$(UV) sync --extra dev

test:
	$(UV) run --extra dev pytest

lint:
	$(UV) run --extra dev ruff check .

fmt:
	$(UV) run --extra dev ruff format .

week:
	@if [ -z "$(DATE)" ]; then echo "Usage: make week DATE=YYYY-MM-DD [CFG=path.json]"; exit 2; fi
	$(UV) run family-schedulekit resolve --week-of $(DATE) $(if $(CFG),--config $(CFG),)

day:
	@if [ -z "$(DATE)" ]; then echo "Usage: make day DATE=YYYY-MM-DD [CFG=path.json]"; exit 2; fi
	$(UV) run family-schedulekit resolve $(DATE) $(if $(CFG),--config $(CFG),)

init-config:
	@if [ -z "$(MOM)" ] || [ -z "$(DAD)" ]; then echo "Usage: make init-config MOM='ParentA' DAD='ParentB' CHILD='Child1' [CHILD2='Child2'] [OUT=schema/my.json] [TEMPLATE=generic]"; exit 2; fi
	$(UV) run family-schedulekit init --mom "$(MOM)" --dad "$(DAD)" \
		$(if $(CHILD),--child "$(CHILD)",) \
		$(if $(CHILD2),--child "$(CHILD2)",) \
		$(if $(CHILD3),--child "$(CHILD3)",) \
		--template $(if $(TEMPLATE),$(TEMPLATE),generic) \
		-o $(if $(OUT),$(OUT),schema/my-schedule.json) -f

list-templates:
	$(UV) run family-schedulekit list-templates

build:
	$(UV) run --extra dev python -m build

publish:
	@echo ">>> Ensure TWINE_USERNAME='__token__' and TWINE_PASSWORD are set"
	$(UV) pip install twine >/dev/null 2>&1 || true
	$(UV) run python -m twine upload dist/*

export:
	@if [ -z "$(START)" ]; then echo "Usage: make export START=YYYY-MM-DD [WEEKS=12] [CFG=schema/example-schedule.json] [OUT=out] [FMTS='csv json jsonl ics md']"; exit 2; fi
	$(UV) run family-schedulekit export --start $(START) --weeks $(if $(WEEKS),$(WEEKS),12) \
		--config $(if $(CFG),$(CFG),schema/example-schedule.json) \
		--outdir $(if $(OUT),$(OUT),out) --formats $(if $(FMTS),$(FMTS),csv json jsonl ics md)

resolve-week:
	@if [ -z "$(DATE)" ]; then echo "Usage: make resolve-week DATE=YYYY-MM-DD [CFG=path.json]"; exit 2; fi
	$(UV) run family-schedulekit resolve --week-of $(DATE) $(if $(CFG),--config $(CFG),)

endif

clean:
	rm -rf $(VENV) build/ dist/ *.egg-info .pytest_cache/ __pycache__ **/__pycache__
