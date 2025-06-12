# Corgi Recommender Service Makefile
# Automates development workflow for the Corgi recommendation engine

# Load environment variables from .env file if it exists
-include .env
export

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
	@echo ""
	@echo "$(BOLD)🚀 Automated Development Workflow:$(RESET)"
	@echo "$(CYAN)make dev$(RESET)             - Start automated development workflow"
	@echo "$(CYAN)make dev-status$(RESET)      - Show development service status"
	@echo "$(CYAN)make dev-stop$(RESET)        - Stop all development services"
	@echo "$(CYAN)make dev-health$(RESET)      - Run health check"
	@echo "$(CYAN)make dev-browser$(RESET)     - Run browser check"
	@echo ""
	@echo "$(BOLD)📦 Core Services:$(RESET)"
	@echo "$(CYAN)make run$(RESET)             - Start the Flask API server"
	@echo "$(CYAN)make gui$(RESET)             - Run the setup GUI for demos"
	@echo "$(CYAN)make reset-db$(RESET)        - Reset the database (drop and recreate schema)"
	@echo ""
	@echo "$(BOLD)🧪 Testing & Validation:$(RESET)"
	@echo "$(CYAN)make validate$(RESET)        - Run full validation suite"
	@echo "$(CYAN)make dry-validate$(RESET)    - Run validation in dry-run mode"
	@echo "$(CYAN)make check$(RESET)           - Run quick health check"
	@echo "$(CYAN)make proxy-test$(RESET)      - Test proxy interaction endpoints"
	@echo "$(CYAN)make check-docs$(RESET)      - Validate documentation files"
	@echo "$(CYAN)make final-test$(RESET)      - Run final sanity test suite"
	@echo "$(CYAN)make nightly-check$(RESET)   - Run nightly validation checks"
	@echo ""
	@echo "$(BOLD)🛠️  Utilities:$(RESET)"
	@echo "$(CYAN)make install$(RESET)         - Install dependencies"
	@echo "$(CYAN)make clean$(RESET)           - Clean up temporary files"
	@echo "$(CYAN)make env-check$(RESET)       - Verify environment variables"
	@echo "$(CYAN)make run-agent profile=NAME$(RESET) - Run a synthetic agent test
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

# Start the Setup GUI
.PHONY: gui
gui: env-check
	@echo "$(YELLOW)Starting Corgi Recommender Setup GUI on $(HOST):$(PORT)...$(RESET)"
	@echo "$(GREEN)Access the GUI at: http://$(HOST):$(PORT)/setup$(RESET)"
	ENABLE_SETUP_GUI=true python3 -m flask --app app run --debug --host=$(HOST) --port=$(PORT)

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

# Run synthetic agent tests
.PHONY: run-agent
run-agent:
	@if [ -z "$(profile)" ] && [ "$(report)" != "true" ]; then \
		echo "$(RED)Error: profile parameter is required unless using report=true$(RESET)"; \
		echo "Usage: make run-agent profile=tech_fan"; \
		exit 1; \
	fi
	@args=""; \
	if [ -n "$(profile)" ]; then args="$$args profile=$(profile)"; fi; \
	if [ -n "$(max_tokens)" ]; then args="$$args max_tokens=$(max_tokens)"; fi; \
	if [ -n "$(limit_interactions)" ]; then args="$$args limit_interactions=$(limit_interactions)"; fi; \
	if [ "$(tools_enabled)" = "true" ]; then args="$$args tools_enabled=true"; fi; \
	if [ "$(no_llm)" = "true" ]; then args="$$args no_llm=true"; fi; \
	if [ "$(headless)" = "true" ]; then args="$$args headless=true"; fi; \
	if [ -n "$(output_dir)" ]; then args="$$args output_dir=$(output_dir)"; fi; \
	if [ -n "$(privacy_level)" ]; then args="$$args privacy_level=$(privacy_level)"; fi; \
	if [ -n "$(time_of_day)" ]; then args="$$args time_of_day=$(time_of_day)"; fi; \
	if [ -n "$(goal)" ]; then args="$$args goal=$(goal)"; fi; \
	if [ -n "$(host)" ]; then args="$$args host=$(host)"; fi; \
	if [ "$(report)" = "true" ]; then args="$$args report=true"; fi; \
	echo "$(YELLOW)Running agent with: $$args$(RESET)"; \
	./run-agent.sh $$args
	@echo "$(GREEN)Agent run complete.$(RESET)"

# Build and run the agent Docker container
.PHONY: agent-docker
agent-docker:
	@echo "$(YELLOW)Building agent Docker container...$(RESET)"
	docker build -t corgi-agent -f agents/Dockerfile .
	@args=""; \
	if [ -n "$(profile)" ]; then args="$$args --profile $(profile)"; fi; \
	if [ -n "$(max_tokens)" ]; then args="$$args --max-tokens $(max_tokens)"; fi; \
	if [ -n "$(limit_interactions)" ]; then args="$$args --max-interactions $(limit_interactions)"; fi; \
	if [ "$(tools_enabled)" = "true" ]; then args="$$args --tools-enabled"; fi; \
	if [ "$(no_llm)" = "true" ]; then args="$$args --no-llm"; fi; \
	if [ -n "$(privacy_level)" ]; then args="$$args --privacy-level $(privacy_level)"; fi; \
	if [ -n "$(time_of_day)" ]; then args="$$args --time-of-day $(time_of_day)"; fi; \
	if [ -n "$(goal)" ]; then args="$$args --goal $(goal)"; fi; \
	if [ -n "$(host)" ]; then args="$$args --host $(host)"; fi; \
	if [ "$(report)" = "true" ]; then args="$$args --analyze-logs"; fi; \
	echo "$(YELLOW)Running Docker container with: $$args$(RESET)"; \
	docker run -it --rm \
		-v $(PWD)/.env:/app/.env:ro \
		-v $(PWD)/logs:/app/logs \
		--network=host \
		corgi-agent $$args
	@echo "$(GREEN)Docker agent run complete.$(RESET)"

# Run multiple agents in parallel (no-llm mode for performance)
.PHONY: multi-agent
multi-agent:
	@if [ -z "$(profiles)" ]; then \
		echo "$(RED)Error: profiles parameter is required$(RESET)"; \
		echo "Usage: make multi-agent profiles=\"tech_fan news_skeptic meme_lover\""; \
		exit 1; \
	fi
	@echo "$(YELLOW)Running multiple agents: $(profiles)$(RESET)"
	@mkdir -p logs/multi_runs
	@timestamp=$$(date +"%Y%m%d_%H%M%S"); \
	for profile in $(profiles); do \
		echo "Starting agent: $$profile"; \
		./run-agent.sh profile=$$profile no_llm=true output_dir=logs/multi_runs/$$profile\_$$timestamp headless=true & \
	done; \
	wait
	@echo "$(GREEN)Multiple agent runs complete.$(RESET)"

# Generate report from agent logs
.PHONY: agent-report
agent-report:
	@echo "$(YELLOW)Generating agent report...$(RESET)"
	./run-agent.sh report=true
	@echo "$(GREEN)Report generation complete.$(RESET)"

# Run final sanity test
.PHONY: final-test
final-test:
	@echo "$(YELLOW)Running final sanity test...$(RESET)"
	cd tools && ./final_sanity_test.sh
	@echo ""
	@echo "$(GREEN)===============================================$(RESET)"
	@echo "$(GREEN)Final instructions for project maintenance:$(RESET)"
	@echo "$(GREEN)===============================================$(RESET)"
	@echo "$(CYAN)1. Remember to take a snapshot of the database before shutdown$(RESET)"
	@echo "$(CYAN)2. Archive logs to preserve interaction history$(RESET)"
	@echo "$(CYAN)3. Update documentation if any last-minute changes were made$(RESET)"
	@echo "$(CYAN)4. Tag the final version in git: git tag v1.0.0-final$(RESET)"
	@echo "$(CYAN)5. Push tags to remote: git push --tags$(RESET)"

# Validate documentation
.PHONY: check-docs
check-docs:
	@echo "$(YELLOW)Validating documentation...$(RESET)"
	cd tools && ./validate_docs.py
	@echo "$(GREEN)Documentation validation complete.$(RESET)"

# Run nightly validation checks
.PHONY: nightly-check
nightly-check:
	@echo "$(YELLOW)Running nightly validation checks...$(RESET)"
	@mkdir -p logs
	@timestamp=$$(date +"%Y-%m-%d_%H-%M-%S")
	@echo "==============================================" >> logs/nightly_checks.log
	@echo "Nightly Check: $$timestamp" >> logs/nightly_checks.log
	@echo "==============================================" >> logs/nightly_checks.log
	
	@echo "$(CYAN)1. Running health check...$(RESET)"
	@python3 tools/dev_check.py | tee -a logs/nightly_checks.log
	
	@echo "$(CYAN)2. Running validator in dry-run mode...$(RESET)"
	@./corgi_validator.py --dry-run | tee -a logs/nightly_checks.log
	
	@echo "$(CYAN)3. Running final test...$(RESET)"
	@cd tools && ./final_sanity_test.sh | tee -a ../logs/nightly_checks.log
	
	@echo "$(CYAN)4. Checking documentation...$(RESET)"
	@cd tools && ./validate_docs.py --check-only | tee -a ../logs/nightly_checks.log
	
	@echo "Completed at: $$(date)" >> logs/nightly_checks.log
	@echo "$(GREEN)Nightly check complete. Results logged to logs/nightly_checks.log$(RESET)"

# Test the proxy with simulated interactions
.PHONY: proxy-test
proxy-test:
	@echo "$(YELLOW)Testing proxy interaction endpoints...$(RESET)"
	@# Test favourite interaction
	@echo "$(CYAN)Testing favourite interaction...$(RESET)"
	curl -i -X POST -H "Content-Type: application/json" \
		-H "Authorization: Bearer test_token" \
		-H "X-Mastodon-Instance: mastodon.social" \
		http://localhost:$(PORT)/api/v1/statuses/123456/favourite
	@echo "\n"
	
	@# Test bookmark interaction
	@echo "$(CYAN)Testing bookmark interaction...$(RESET)"
	curl -i -X POST -H "Content-Type: application/json" \
		-H "Authorization: Bearer test_token" \
		-H "X-Mastodon-Instance: mastodon.social" \
		http://localhost:$(PORT)/api/v1/statuses/123456/bookmark
	@echo "\n"
	
	@# Test reblog interaction
	@echo "$(CYAN)Testing reblog interaction...$(RESET)"
	curl -i -X POST -H "Content-Type: application/json" \
		-H "Authorization: Bearer test_token" \
		-H "X-Mastodon-Instance: mastodon.social" \
		http://localhost:$(PORT)/api/v1/statuses/123456/reblog
	@echo "\n"
	
	@# Check interaction logs
	@if [ -f "logs/proxy_interactions.log" ]; then \
		echo "$(CYAN)Recent interaction logs:$(RESET)"; \
		tail -n 10 logs/proxy_interactions.log; \
	else \
		echo "$(RED)No interaction logs found$(RESET)"; \
	fi
	
	@echo "$(GREEN)Proxy test complete.$(RESET)"

# =============================================================================
# 🚀 AUTOMATED DEVELOPMENT WORKFLOW
# =============================================================================

# Start automated development workflow
.PHONY: dev
dev:
	@echo "$(BOLD)🚀 Starting Automated Development Workflow$(RESET)"
	@echo "$(YELLOW)This will start both backend and frontend with automatic monitoring$(RESET)"
	./dev-monitor start

# Show development service status
.PHONY: dev-status
dev-status:
	@echo "$(YELLOW)Checking development service status...$(RESET)"
	./dev-monitor status

# Stop all development services
.PHONY: dev-stop
dev-stop:
	@echo "$(YELLOW)Stopping all development services...$(RESET)"
	./dev-monitor stop

# Run health check only
.PHONY: dev-health
dev-health:
	@echo "$(YELLOW)Running automated health check...$(RESET)"
	./dev-monitor health --verbose

# Run browser check only  
.PHONY: dev-browser
dev-browser:
	@echo "$(YELLOW)Running automated browser check...$(RESET)"
	./dev-monitor browser --verbose

# Run intelligent browser agent test
.PHONY: dev-test
dev-test:
	@echo "$(YELLOW)🤖 Running intelligent browser tests...$(RESET)"
	python3 scripts/development/browser_agent.py

# Run browser agent with visible browser
.PHONY: dev-test-headed
dev-test-headed:
	@echo "$(YELLOW)🤖 Running browser tests with visible browser...$(RESET)"
	python3 scripts/development/browser_agent.py --headed

# Run continuous browser testing
.PHONY: dev-test-continuous
dev-test-continuous:
	@echo "$(YELLOW)🤖 Starting continuous browser testing...$(RESET)"
	python3 scripts/development/browser_agent.py --continuous --interval 30

# Robust server startup with automatic cleanup
.PHONY: dev-start-robust
dev-start-robust:
	@echo "[RULE] Ensuring clean port before starting API server..."
	./manage_server_port.sh stop api
	@echo "[RULE] Starting API server..."
	./manage_server_port.sh start api

# Install development workflow dependencies
.PHONY: dev-install
dev-install:
	@echo "$(YELLOW)Installing development workflow dependencies...$(RESET)"
	pip install aiohttp selenium playwright
	@echo "$(GREEN)Installing Playwright browsers...$(RESET)"
	playwright install chromium
	@echo "$(GREEN)Development dependencies installed.$(RESET)"
	@echo "$(CYAN)✅ Playwright is now ready for intelligent browser testing!$(RESET)"