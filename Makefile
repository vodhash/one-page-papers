PAPERS := $(notdir $(wildcard papers/*/*))
CATEGORIES := $(notdir $(wildcard papers/*))
# Python of the virtualenv made by `make deps`, else the system one
PY = $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
# papers built at a time, each in a browser of its own: one per processor, up to 8, by default
JOBS ?= $(shell n=$$(nproc 2>/dev/null || echo 1); [ $$n -gt 8 ] && n=8; echo $$n)
.PHONY: all check readme us changed deps clean site serve upload engine-test engine-dist engine-publish $(PAPERS) $(CATEGORIES)

all:
	$(PY) engine/build.py --jobs $(JOBS)
	$(PY) engine/readme.py

# as the CI: no large file in git, every poster fits (writing dist/, not docs/), the catalog is up to date
check:
	$(PY) engine/sizes.py
	$(PY) engine/build.py --check --jobs $(JOBS)
	$(PY) engine/readme.py --check

readme:
	$(PY) engine/readme.py

# the previews that differ from the last commit: what the next commit would carry (dist/ is not in git)
changed:
	@git status --short -- docs

# the US formats (letter, tabloid, 18x24, 24x36) into release/us/, which git ignores
us:
	$(PY) engine/build.py --us --jobs $(JOBS)

# the showcase site into site/, from meta.yaml and the PDFs of dist/ (run make first); previews need
# pdftoppm (poppler-utils)
site:
	$(PY) engine/site.py

# the site on http://localhost:8000/
serve: site
	$(PY) -m http.server --directory site --bind 127.0.0.1 8000

# the PDFs of dist/ that differ from the bucket of files.onepagepapers.com, as the pages workflow
# does, with the R2_* variables of engine/upload.py and boto3 (requirements-deploy.txt)
upload:
	$(PY) engine/upload.py

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

# build/ holds the cache of the posters (build/cache/): after this, every poster is laid out again
clean:
	rm -rf build

# the onepage-engine package of engine/: its tests, its wheel and sdist in engine/dist/, and their
# upload to the index of UV_PUBLISH_URL, as UV_PUBLISH_USERNAME with UV_PUBLISH_PASSWORD
engine-test:
	$(PY) -m pytest -q engine/tests

engine-dist:
	rm -rf engine/dist
	uv build engine --out-dir engine/dist

engine-publish: engine-dist
	uv publish engine/dist/*
