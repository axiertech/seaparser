PYTHON ?= .venv/bin/python

.PHONY: prepare-python check frontend-check migration-plan
# Godkänt projektmandat; körs inte automatiskt av check.
prepare-python:
	python3 -m venv .venv
	.venv/bin/python -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements.lock

check:
	$(PYTHON) -B -m scripts.check
	$(MAKE) frontend-check

frontend-check:
	npm --prefix frontend run check
	npm --prefix frontend test

migration-plan:
	$(PYTHON) -B -m scripts.migrate --environment development

# Isolated review only; no webroot copying, service restart or tile download.
.PHONY: land-preview
land-preview:
	node frontend/build.mjs
	$(PYTHON) -B -m scripts.land_preview --bundle --output frontend/land-dist
