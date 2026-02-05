.PHONY: install install-dev run gui cli test clean help

help:
	@echo "SIK Radio Configurator - Available commands:"
	@echo ""
	@echo "  make install      - Install the package in standard mode"
	@echo "  make install-dev  - Install in development mode with test dependencies"
	@echo "  make gui          - Launch the GUI application"
	@echo "  make cli          - Show CLI help"
	@echo "  make test         - Run unit tests"
	@echo "  make clean        - Remove build artifacts and cache"
	@echo "  make lint         - Run code style checks (if available)"
	@echo ""
	@echo "Examples:"
	@echo "  make gui                          - Start GUI"
	@echo "  make test                         - Run tests"
	@echo ""

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-cov flake8

gui:
	python -m src.gui.main

cli:
	python cli.py --help

test:
	python -m pytest tests/ -v

test-coverage:
	python -m pytest tests/ -v --cov=src --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

lint:
	flake8 src/ cli.py examples.py --max-line-length=100 --ignore=E501

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf build/ dist/ *.egg-info
	rm -rf htmlcov/ .pytest_cache/ .coverage
	@echo "Cleaned up build artifacts"

.DEFAULT_GOAL := help
