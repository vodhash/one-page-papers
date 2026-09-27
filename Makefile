PAPERS := $(notdir $(wildcard papers/*/*))
CATEGORIES := $(notdir $(wildcard papers/*))
# Python of the virtualenv made by `make deps`, else the system one
PY = $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
.PHONY: all check readme us deps clean site serve $(PAPERS) $(CATEGORIES)

all:
	$(PY) engine/build.py
	$(PY) engine/readme.py

check:
	$(PY) engine/build.py --check
	$(PY) engine/readme.py --check

readme:
	$(PY) engine/readme.py

# the US formats (letter, tabloid, 18x24, 24x36) into release/us/, which git ignores
us:
	$(PY) engine/build.py --us

# the showcase site into site/, from meta.yaml and the PDFs of dist/; previews need pdftoppm (poppler-utils)
site:
	$(PY) engine/site.py

# the site on http://localhost:8000/
serve: site
	$(PY) -m http.server --directory site --bind 127.0.0.1 8000

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
	rm -rf build
