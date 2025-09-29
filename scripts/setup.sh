#!/bin/bash

# PDF Redaction Service Setup Script
# This script sets up the development environment

set -e

echo "🔒 PDF Redaction Service Setup"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.9+ is installed
check_python() {
    print_status "Checking Python version..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
            print_success "Python $PYTHON_VERSION is installed"
        else
            print_error "Python 3.9+ is required. Found Python $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 is not installed"
        exit 1
    fi
}

# Check if Docker is installed
check_docker() {
    print_status "Checking Docker installation..."
    if command -v docker &> /dev/null; then
        print_success "Docker is installed"
        
        if command -v docker-compose &> /dev/null; then
            print_success "Docker Compose is installed"
        else
            print_error "Docker Compose is not installed"
            exit 1
        fi
    else
        print_error "Docker is not installed"
        exit 1
    fi
}

# Create virtual environment
setup_venv() {
    print_status "Setting up Python virtual environment..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi
    
    source venv/bin/activate
    print_success "Virtual environment activated"
}

# Install Python dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if [ -f "requirements.txt" ]; then
        pip install --upgrade pip
        pip install -r requirements.txt
        print_success "Dependencies installed"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
}

# Setup environment file
setup_env() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f "env.example" ]; then
            cp env.example .env
            print_success "Environment file created from template"
            print_warning "Please edit .env file with your configuration"
        else
            print_error "env.example not found"
            exit 1
        fi
    else
        print_warning ".env file already exists"
    fi
}

# Start ClickHouse for development
start_clickhouse() {
    print_status "Starting ClickHouse for development..."
    
    # Check if ClickHouse container is already running
    if docker ps | grep -q "clickhouse-dev"; then
        print_warning "ClickHouse container is already running"
    else
        docker run -d \
            --name clickhouse-dev \
            -p 8123:8123 \
            -p 9000:9000 \
            clickhouse/clickhouse-server:latest
        
        print_success "ClickHouse started on ports 8123 (HTTP) and 9000 (TCP)"
        
        # Wait for ClickHouse to be ready
        print_status "Waiting for ClickHouse to be ready..."
        sleep 10
        
        # Initialize database
        docker exec clickhouse-dev clickhouse-client --query "CREATE DATABASE IF NOT EXISTS pdf_redaction"
        print_success "ClickHouse database initialized"
    fi
}

# Run tests
run_tests() {
    print_status "Running tests..."
    
    if command -v pytest &> /dev/null; then
        pytest tests/ -v
        print_success "Tests completed"
    else
        print_warning "pytest not installed, skipping tests"
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p temp
    mkdir -p uploads
    
    print_success "Directories created"
}

# Main setup function
main() {
    echo "Starting setup process..."
    echo ""
    
    check_python
    check_docker
    setup_venv
    install_dependencies
    setup_env
    create_directories
    start_clickhouse
    run_tests
    
    echo ""
    print_success "Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file with your AWS credentials and configuration"
    echo "2. Start the API server: make start-dev"
    echo "3. Start the Streamlit UI (in another terminal): make start-ui"
    echo "4. Access the API documentation at: http://localhost:8000/docs"
    echo "5. Access the Streamlit UI at: http://localhost:8501"
    echo ""
    echo "For Docker deployment:"
    echo "1. Configure your .env file"
    echo "2. Run: make docker-up"
    echo ""
}

# Run main function
main "$@"
