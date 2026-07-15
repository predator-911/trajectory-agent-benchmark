.PHONY: install test test-unit test-workflow test-eval test-regression lint demo eval graph clean

install:
	pip install -e ".[dev]"

test:
	pytest -v

test-unit:
	pytest -v tests/unit

test-workflow:
	pytest -v tests/workflow

test-eval:
	pytest -v tests/evaluation

test-regression:
	pytest -v tests/regression

lint:
	ruff check src/ tests/

demo:
	python -m agentic_logistics.cli demo --scenario scenario_01_port_congestion.json --provider mock

eval:
	python -m agentic_logistics.cli eval

graph:
	python -m agentic_logistics.cli graph

clean:
	find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -f reports/eval_results/*.json reports/eval_results/*.md
	rm -f reports/audit_logs/*.jsonl
