.PHONY: install test lint smoke demo ci clean

install:
	pip install -e packages/hu-core[dev] -e packages/hu-plugins-hindsight

test:
	pytest packages/hu-core/tests/ -q

lint:
	ruff check packages/hu-core/

smoke:
	HUAP_LLM_MODE=stub huap trace run hello examples/graphs/hello.yaml --out /tmp/smoke.jsonl
	huap trace view /tmp/smoke.jsonl

demo:
	huap demo --no-open

ci:
	huap ci run suites/smoke/suite.yaml --html reports/smoke.html

clean:
	rm -rf huap_demo/ reports/ ci_demo/ __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
