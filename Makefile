PAPERS := $(notdir $(wildcard papers/*/*))
CATEGORIES := $(notdir $(wildcard papers/*))
# Python of the virtualenv made by `make deps`, else the system one
PY = $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
.PHONY: all check readme deps clean $(PAPERS) $(CATEGORIES)

all:
	$(PY) engine/build.py
	$(PY) engine/readme.py

check:
	$(PY) engine/build.py --check
	$(PY) engine/readme.py --check

readme:
	$(PY) engine/readme.py

$(PAPERS) $(CATEGORIES):
	$(PY) engine/build.py $@

# uv when available: the stock Python of Debian and Ubuntu has neither pip nor venv
deps:
	npm ci
	if command -v uv >/dev/null; then \
		uv venv --allow-existing .venv && uv pip install --python .venv/bin/python -r requirements.txt; \
	else \
		python3 -m venv .venv && .venv/bin/pip install -r requirements.txt; \
	fi
	.venv/bin/python -m playwright install --only-shell chromium

clean:
	rm -rf build dist
