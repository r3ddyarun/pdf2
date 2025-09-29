# PDF Redaction Service Makefile

.PHONY: help install test lint format clean docker-build docker-up docker-down docker-logs

# Default target
help:
	@echo "PDF Redaction Service - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install     - Install Python dependencies"
	@echo "  test        - Run test suite"
	@echo "  lint        - Run linting checks"
	@echo "  format      - Format code with black and isort"
	@echo "  clean       - Clean up temporary files"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build - Build Docker images"
	@echo "  docker-up    - Start all services with Docker Compose"
	@echo "  docker-down  - Stop all services"
	@echo "  docker-logs  - Show logs for all services"
	@echo ""
	@echo "Database:"
	@echo "  db-init     - Initialize ClickHouse database"
	@echo "  db-migrate  - Run database migrations"
	@echo ""
	@echo "Monitoring:"
	@echo "  metrics     - Show Prometheus metrics"
	@echo "  logs        - Show application logs"

# Development Commands
install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-watch:
	pytest tests/ -v --cov=app -f

lint:
	flake8 app/ tests/
	mypy app/
	black --check app/ tests/
	isort --check-only app/ tests/

format:
	black app/ tests/
	isort app/ tests/

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage

# Service Commands
start-services:
	@echo "Starting ClickHouse database..."
	@if ! pgrep -f "clickhouse-server" > /dev/null; then \
		echo "ClickHouse not running. Please start it manually:"; \
		echo "  brew install clickhouse"; \
		echo "  clickhouse server --config-file /usr/local/etc/clickhouse-server/config.xml"; \
	else \
		echo "ClickHouse is already running"; \
	fi

# Database Commands
db-init:
	@echo "Initializing ClickHouse database..."
	@clickhouse-client --query "CREATE DATABASE IF NOT EXISTS pdf_redaction" || echo "ClickHouse not available"

db-migrate:
	@echo "Running database migrations..."
	@clickhouse-client --database=pdf_redaction --multiquery < clickhouse/init.sql || echo "ClickHouse not available"

# Monitoring Commands
metrics:
	curl -s http://localhost:9090/metrics | grep pdf_redaction

logs:
	@echo "Application logs are displayed in the terminal where the server is running"

# Utility Commands
start-dev:
	python -m uvicorn app.combined_app:app --reload --host 0.0.0.0 --port 8000

start-combined:
	python start_combined.py

start-prod:
	python start_production.py

start-ui:
	streamlit run app/streamlit_app.py --server.port 8501

health-check:
	curl -f http://localhost:8000/health || echo "Service is down"

# Production Commands
deploy:
	@echo "For production deployment, use:"
	@echo "  make start-dev  # Development mode"
	@echo "  gunicorn app.combined_app:app -w 4 -k uvicorn.workers.UvicornWorker  # Production"

backup-db:
	@echo "Backup ClickHouse database:"
	@echo "  clickhouse-backup create"

# Security Commands
security-scan:
	safety check
	bandit -r app/

# Documentation
docs:
	python -c "import webbrowser; webbrowser.open('http://localhost:8000/docs')"

# All-in-one development setup
dev-setup: install
	@echo "Setting up development environment..."
	@echo "1. Installing dependencies..."
	@echo "2. Setting up environment file..."
	@cp env.example .env || echo "env.example not found"
	@echo "3. Development environment ready!"
	@echo ""
	@echo "Next steps:"
	@echo "  make start-dev    # Start combined application"
	@echo "  make test         # Run tests"

# Full stack development
dev-full: start-dev
	@echo "Combined application starting..."
	@echo "Main App: http://localhost:8000"
	@echo "Streamlit UI: http://localhost:8000/ui"
	@echo "API Docs: http://localhost:8000/docs"

# Cleanup development environment
dev-cleanup:
	@echo "Stopping application..."
	@pkill -f "uvicorn.*combined_app" || true
	@echo "Development environment cleaned up"

# Generate test PDF files
generate-test-pdfs:
	@echo "Generating test PDF files..."
	@python3 generate_test_pdfs.py --count 2 --type all
	@echo "Test PDFs generated in test_pdfs/ directory"

# Run redaction tests
test-redaction:
	@echo "Testing PDF redaction service..."
	@python3 test_redaction.py --report
	@echo "Test results saved to test_report.txt"

# Quick test with just sensitive PDFs
test-sensitive:
	@echo "Generating sensitive test PDFs..."
	@python3 generate_test_pdfs.py --count 1 --type sensitive
	@echo "Testing sensitive PDF redaction..."
	@python3 test_redaction.py --files "sensitive_*.pdf" --report

# Clean test files
clean-tests:
	@echo "Cleaning test files..."
	@rm -rf test_pdfs/
	@rm -rf redacted_outputs/
	@rm -f test_report.txt
	@echo "Test files cleaned"
