# Corgi Recommender Service Makefile
# Automates development workflow for the Corgi recommendation engine

# Default environment variables
export POSTGRES_DB ?= corgi_recommender
export POSTGRES_USER ?= your_username
export POSTGRES_PASSWORD ?= your_password
export PORT ?= 5001
export HOST ?= 0.0.0.0
export FLASK_ENV ?= development
export DEBUG ?= True

# ANSI escape codes for colorful output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
BOLD := \033[1m
RESET := \033[0m

# Default target
.PHONY: help
help:
	@echo "$(BOLD)Corgi Recommender Service Development Tasks$(RESET)"
	@echo "$(CYAN)make run$(RESET)             - Start the Flask API server"
	@echo "$(CYAN)make reset-db$(RESET)        - Reset the database (drop and recreate schema)"
	@echo "$(CYAN)make validate$(RESET)        - Run full validation suite"
	@echo "$(CYAN)make dry-validate$(RESET)    - Run validation in dry-run mode"
	@echo "$(CYAN)make check$(RESET)           - Run quick health check"
	@echo "$(CYAN)make install$(RESET)         - Install dependencies"
	@echo "$(CYAN)make clean$(RESET)           - Clean up temporary files"
	@echo "$(CYAN)make env-check$(RESET)       - Verify environment variables"
	@echo ""
	@echo "Environment settings:"
	@echo "  POSTGRES_DB=$(POSTGRES_DB)"
	@echo "  POSTGRES_USER=$(POSTGRES_USER)"
	@echo "  PORT=$(PORT)"
	@echo ""
	@echo "Example: make run POSTGRES_USER=postgres POSTGRES_PASSWORD=secret"

# Check if required environment variables are set
.PHONY: env-check
env-check:
	@echo "$(YELLOW)Checking environment variables...$(RESET)"
	@echo "POSTGRES_DB=$(POSTGRES_DB)"
	@echo "POSTGRES_USER=$(POSTGRES_USER)"
	@if [ -z "$(POSTGRES_PASSWORD)" ]; then \
		echo "$(RED)Warning: POSTGRES_PASSWORD is not set or empty!$(RESET)"; \
	else \
		echo "POSTGRES_PASSWORD=********"; \
	fi
	@echo "PORT=$(PORT)"
	@echo "HOST=$(HOST)"
	@echo "FLASK_ENV=$(FLASK_ENV)"
	@echo "$(GREEN)Environment check complete.$(RESET)"

# Install dependencies
.PHONY: install
install:
	@echo "$(YELLOW)Installing dependencies...$(RESET)"
	pip install -r requirements.txt
	@echo "$(GREEN)Dependencies installed successfully.$(RESET)"

# Reset database
.PHONY: reset-db
reset-db: env-check
	@echo "$(YELLOW)Resetting database schema...$(RESET)"
	./setup_db.sh --reset
	@echo "$(GREEN)Database reset complete.$(RESET)"

# Start the Flask API server
.PHONY: run
run: env-check
	@echo "$(YELLOW)Starting Corgi Recommender Service on $(HOST):$(PORT)...$(RESET)"
	python3 -m flask --app app run --debug --host=$(HOST) --port=$(PORT)

# Run validator
.PHONY: validate
validate: env-check
	@echo "$(YELLOW)Running validation suite...$(RESET)"
	./corgi_validator.py --output validation_report.json --verbose
	@echo "$(GREEN)Validation complete. See validation_report.json for details.$(RESET)"

# Run validator in dry-run mode
.PHONY: dry-validate
dry-validate:
	@echo "$(YELLOW)Running validation in dry-run mode...$(RESET)"
	./corgi_validator.py --dry-run --verbose
	@echo "$(GREEN)Dry validation complete.$(RESET)"

# Run health check
.PHONY: check
check: env-check
	@echo "$(YELLOW)Running health check...$(RESET)"
	python3 tools/dev_check.py
	@echo "$(GREEN)Health check complete.$(RESET)"

# Check API paths
.PHONY: check-paths
check-paths:
	@echo "$(YELLOW)Checking API path compatibility...$(RESET)"
	python3 -c 'from corgi_validator import check_api_paths; check_api_paths()'
	@echo "$(GREEN)API paths check complete.$(RESET)"

# Clean up generated files
.PHONY: clean
clean:
	@echo "$(YELLOW)Cleaning up temporary files...$(RESET)"
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type f -name "coverage.xml" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type f -name "*.log" -delete
	rm -f validation_report.json
	@echo "$(GREEN)Cleanup complete.$(RESET)"