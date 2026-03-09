.PHONY: lint test render clean format

lint: format
	ruff check pymotion/ tests/
	mypy --strict pymotion/

format:
	ruff format pymotion/ tests/

test:
	pytest -v

render:
	python -m pymotion render examples/hello_world.py

clean:
	rm -rf __pycache__ .mypy_cache .ruff_cache htmlcov dist build *.egg-info .pytest_cache .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
