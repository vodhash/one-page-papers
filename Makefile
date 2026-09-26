PAPERS := $(notdir $(wildcard papers/*))
.PHONY: all deps clean $(PAPERS)

all:
	python3 engine/build.py

$(PAPERS):
	python3 engine/build.py $@

deps:
	npm install
	pip install -r requirements.txt
	python3 -m playwright install chromium

clean:
	rm -rf build
