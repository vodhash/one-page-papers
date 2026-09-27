PAPERS := $(notdir $(wildcard papers/*/*))
CATEGORIES := $(notdir $(wildcard papers/*))
# Python of the virtualenv made by `make deps`, else the system one
PY = $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
# papers built at a time, each in a browser of its own: one per processor, up to 8, by default
JOBS ?= $(shell n=$$(nproc 2>/dev/null || echo 1); [ $$n -gt 8 ] && n=8; echo $$n)
.PHONY: all check readme us changed deps clean site serve $(PAPERS) $(CATEGORIES)

all:
	$(PY) engine/build.py --jobs $(JOBS)
	$(PY) engine/readme.py

check:
	$(PY) engine/build.py --check --jobs $(JOBS)
	$(PY) engine/readme.py --check

readme:
	$(PY) engine/readme.py

# the PDFs and previews that differ from the last commit: what the next commit would carry
changed:
	@git status --short -- dist docs

# the US formats (letter, tabloid, 18x24, 24x36) into release/us/, which git ignores
us:
	$(PY) engine/build.py --us --jobs $(JOBS)

# the showcase site into site/, from meta.yaml and the PDFs of dist/; previews need pdftoppm (poppler-utils)
site:
	$(PY) engine/site.py

# the site on http://localhost:8000/
serve: site
	$(PY) -m http.server --directory site --bind 127.0.0.1 8000

$(PAPERS) $(CATEGORIES):
	$(PY) engine/build.py $@ --jobs $(JOBS)

# uv when available: the stock Python of Debian and Ubuntu has neither pip nor venv
deps:
	npm ci
	if command -v uv >/dev/null; then \
		uv venv --allow-existing .venv && uv pip install --python .venv/bin/python -r requirements.txt; \
	else \
		python3 -m venv .venv && .venv/bin/pip install -r requirements.txt; \
	fi
	.venv/bin/python -m playwright install --only-shell chromium
	git config core.hooksPath .githooks

clean:
	rm -rf build
