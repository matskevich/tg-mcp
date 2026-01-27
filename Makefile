# S16-Leads Makefile
# ==================

.PHONY: install test test-limiter test-fast run-security-check clean setup-dirs help sync-env check-env

# Default target
help:
	@echo "Available targets:"
	@echo "  sync-env        - Sync .env from env.sample (add missing keys)"
	@echo "  check-env       - Check what's missing in .env"
	@echo "  install         - Install dependencies"
	@echo "  setup-dirs      - Create required directories"
	@echo "  test            - Run all tests"
	@echo "  test-limiter    - Run only anti-spam limiter tests"
	@echo "  test-fast       - Run tests without slow integration tests"
	@echo "  run-security    - Run security check script"
	@echo "  clean           - Clean up temporary files"

# Sync .env from env.sample - добавляет недостающие ключи
sync-env:
	@echo "🔧 Syncing .env from .env.sample..."
	@if [ ! -f .env ]; then \
		echo "📁 Creating .env from .env.sample"; \
		cp .env.sample .env; \
		echo "✅ .env created with all default values"; \
	else \
		echo "📝 Checking for missing keys in .env..."; \
		python3 scripts/sync_env.py; \
	fi

# Check what's missing in .env without modifying
check-env:
	@echo "🔍 Checking .env completeness..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file does not exist"; \
		echo "💡 Run 'make sync-env' to create it"; \
	else \
		python3 scripts/check_env.py; \
	fi

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt

# Set up required directories
setup-dirs:
	@echo "📁 Creating directories..."
	mkdir -p data/sessions data/export data/anti_spam data/logs
	mkdir -p gconf/data/sessions gconf/export
	mkdir -p vahue/data/sessions vahue/export
	chmod 700 data/sessions
	@echo "✅ Directories created"

# Run all tests
test: install
	@echo "🧪 Running all tests..."
	python -m pytest tests/ -v

# Run only anti-spam limiter tests
test-limiter: install
	@echo "🧪 Running anti-spam limiter tests..."
	python -m pytest tests/test_limiter.py -v

# Run fast tests (skip slow integration tests)
test-fast: install
	@echo "🧪 Running fast tests..."
	python -m pytest tests/ -v -m "not slow"

# Run security check
run-security:
	@echo "🔒 Running security check..."
	python scripts/security_check.py

# Clean temporary files
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -f test_export.json
	@echo "✅ Cleanup complete"

# Development setup
dev-setup: sync-env setup-dirs install
	@echo "🚀 Development environment ready!"
	@echo "💡 Next steps:"
	@echo "  1. Edit .env with your API credentials"
	@echo "  2. Run 'make test-limiter' to test anti-spam system"
	@echo "  3. Run 'make check-env' to verify configuration"

# Check anti-spam status
check-anti-spam:
	@echo "🛡️  Checking anti-spam system status..."
	@python -c "from tganalytics.infra.limiter import get_rate_limiter; limiter = get_rate_limiter(); print('📊 Stats:', limiter.get_stats())" 2>/dev/null || echo "❌ Anti-spam system not initialized"

# Show current .env status
env-status: check-env check-anti-spam

# CLI shortcuts (require GROUP_ID variable)
info:
	@if [ -z "$(GROUP_ID)" ]; then echo "❌ Usage: make info GROUP_ID=-1001234567890"; exit 1; fi
	PYTHONPATH=. python -c "from apps.s16leads.cli import asyncio, main; asyncio.run(main())" info $(GROUP_ID)

participants:
	@if [ -z "$(GROUP_ID)" ]; then echo "❌ Usage: make participants GROUP_ID=-1001234567890 LIMIT=100"; exit 1; fi
	PYTHONPATH=. python -c "from apps.s16leads.cli import asyncio, main; asyncio.run(main())" participants $(GROUP_ID) --limit $(or $(LIMIT),100)

export:
	@if [ -z "$(GROUP_ID)" ]; then echo "❌ Usage: make export GROUP_ID=-1001234567890 OUTPUT=data/export/members.json"; exit 1; fi
	PYTHONPATH=. python -c "from apps.s16leads.cli import asyncio, main; asyncio.run(main())" export $(GROUP_ID) --output $(or $(OUTPUT),data/export/members.json) --format $(or $(FORMAT),json)

# =====================================================
# ANTI-SPAM COMPLIANCE AND SECURITY CHECKS
# =====================================================

# Check anti-spam compliance for all Telegram API calls
anti-spam-check:
	@echo "🔍 Checking anti-spam compliance..."
	python scripts/check_anti_spam_compliance.py

# Run comprehensive security checks
security-check:
	@echo "🔒 Running comprehensive security checks..."
	@echo "=== Bandit Security Scan ==="
	bandit -r src/ examples/ -f json -o security-report.json 2>/dev/null || bandit -r src/ examples/
	@echo "=== Anti-spam Compliance ==="
	python scripts/check_anti_spam_compliance.py

# Code quality checks
lint:
	@echo "🔍 Running code linting..."
	flake8 src/ examples/ tests/ scripts/ --max-line-length=100 --ignore=E203,W503

# Format code
format:
	@echo "🎨 Formatting code..."
	black src/ examples/ tests/ scripts/
	isort src/ examples/ tests/ scripts/

# Check code formatting
format-check:
	@echo "🎨 Checking code formatting..."
	black --check src/ examples/ tests/ scripts/
	isort --check src/ examples/ tests/ scripts/

# Install development dependencies
dev-install:
	@echo "📦 Installing development dependencies..."
	pip install -r requirements.txt
	pip install pre-commit black isort flake8 bandit yamllint pytest-mock
	@echo "✅ Development dependencies installed"

# Set up pre-commit hooks
pre-commit-setup: dev-install
	@echo "🪝 Setting up pre-commit hooks..."
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "✅ Pre-commit hooks installed"

# Run pre-commit on all files
pre-commit-run:
	@echo "🪝 Running pre-commit on all files..."
	pre-commit run --all-files

# Comprehensive checks (CI pipeline)
check-all: format-check lint anti-spam-check security-check test
	@echo "✅ All checks completed successfully!"

# Telegram API safety audit
telegram-api-audit:
	@echo "🔍 Running comprehensive Telegram API audit..."
	@echo "=== 1. Checking for unsafe client calls ==="
	@echo "Searching for direct client.* calls without safe_call wrapper..."
	@grep -r "await.*client\." src/ examples/ --include="*.py" | \
		grep -v "safe_call\|_safe_api_call\|client\.start\|client\.disconnect\|client\.get_me" || \
		echo "✅ No unsafe client calls found"
	@echo ""
	@echo "=== 2. Checking for missing safe_call imports ==="
	@echo "Looking for files that might need safe_call imports..."
	@for file in $$(find src/ examples/ -name "*.py" -type f); do \
		if grep -q "client\." "$$file" && ! grep -q "safe_call\|_safe_api_call" "$$file" && ! grep -q "__init__" "$$file"; then \
			echo "⚠️  $$file might need safe_call import"; \
		fi; \
	done || echo "✅ All files with client calls have safe_call imports"
	@echo ""
	@echo "=== 3. Running anti-spam compliance check ==="
	python scripts/check_anti_spam_compliance.py
	@echo ""
	@echo "=== 4. Checking rate limiter usage ==="
	@python -c "from tganalytics.infra.limiter import get_rate_limiter; limiter = get_rate_limiter(); stats = limiter.get_stats(); print('📊 Rate Limiter Stats:'); [print(f'   {k}: {v}') for k, v in stats.items()]" 2>/dev/null || echo "❌ Rate limiter not accessible"

# Quick development checks (before commit)
dev-check: format lint anti-spam-check
	@echo "✅ Development checks completed!"

# Help with new anti-spam commands
help-security:
	@echo "🛡️  Security and Anti-spam Commands:"
	@echo "  anti-spam-check     - Check all Telegram API calls for safe_call usage"
	@echo "  security-check      - Run bandit security scan + anti-spam check"  
	@echo "  telegram-api-audit  - Comprehensive audit of Telegram API usage"
	@echo "  lint               - Run code linting with flake8"
	@echo "  format             - Format code with black and isort"
	@echo "  format-check       - Check if code is properly formatted"
	@echo "  pre-commit-setup   - Install pre-commit hooks for automatic checks"
	@echo "  pre-commit-run     - Run all pre-commit checks manually"
	@echo "  check-all          - Run all checks (format, lint, security, tests)"
	@echo "  dev-check          - Quick checks before committing"
