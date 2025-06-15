# Makefile for Gnosis Mystic Development

.PHONY: help install dev-install test lint format clean build docs setup

# Default target
help:
	@echo "🔮 Gnosis Mystic Development Commands"
	@echo ""
	@echo "Setup Commands:"
	@echo "  setup          - Create project structure and setup development environment"
	@echo "  install        - Install package and dependencies"
	@echo "  dev-install    - Install in development mode with dev dependencies"
	@echo ""
	@echo "Development Commands:"
	@echo "  test           - Run test suite"
	@echo "  test-cov       - Run tests with coverage report"
	@echo "  lint           - Run linting checks"
	@echo "  format         - Format code with black and ruff"
	@echo "  typecheck      - Run type checking with mypy"
	@echo ""
	@echo "Build Commands:"
	@echo "  build          - Build package"
	@echo "  docs           - Build documentation"
	@echo "  clean          - Clean build artifacts"
	@echo ""
	@echo "Quick Commands:"
	@echo "  quick-test     - Run fast tests only"
	@echo "  quick-check    - Run format, lint, and quick tests"

# Setup and Installation
setup:
	@echo "🔮 Setting up Gnosis Mystic development environment..."
	python scripts/setup_project.py
	pip install -e ".[dev]"
	pre-commit install

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"
	pre-commit install

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=mystic --cov-report=html --cov-report=term-missing

quick-test:
	pytest tests/unit/ -v -m "not slow"

benchmark:
	pytest tests/benchmarks/ -v

# Code Quality
lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/
	ruff format src/ tests/

typecheck:
	mypy src/

# Build and Documentation
build:
	python -m build

docs:
	mkdocs build

docs-serve:
	mkdocs serve

# Maintenance
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Combined commands
quick-check: format lint quick-test

all-checks: format lint typecheck test

# Development helpers
demo:
	python scripts/demo_functions.py

health-check:
	python scripts/health_check.py

# Docker commands (future)
docker-build:
	docker build -t gnosis-mystic .

docker-run:
	docker run -it gnosis-mystic

# Release commands (future)
release-test:
	python -m twine upload --repository testpypi dist/*

release:
	python -m twine upload dist/*