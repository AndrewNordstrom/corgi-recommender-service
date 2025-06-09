#!/bin/sh
# Corgi Recommender Service - Docker Development Control Script
# This script manages the Docker environment with clean startup and profile support

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo "${RED}[ERROR]${NC} $1"
}

# Function to check if .env file exists
check_env_file() {
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from env.example..."
        if [ -f env.example ]; then
            cp env.example .env
            print_success ".env file created. Please update it with your configuration."
        else
            print_error "env.example not found. Please create .env file manually."
            exit 1
        fi
    fi
}

# Function to clean up existing containers and networks
cleanup() {
    print_info "Cleaning up existing Docker resources..."
    docker-compose down -v --remove-orphans 2>/dev/null || true
    
    # Remove any dangling containers
    docker container prune -f 2>/dev/null || true
    
    # Remove any dangling volumes
    docker volume prune -f 2>/dev/null || true
    
    print_success "Cleanup complete!"
}

# Function to start services in standalone mode
start_standalone() {
    print_info "Starting Corgi API in standalone mode..."
    check_env_file
    cleanup
    
    print_info "Building and starting services..."
    docker-compose --profile standalone up --build -d
    
    print_success "Standalone services started!"
    print_info "Corgi API available at: http://localhost:${CORGI_API_HOST_PORT:-5002}"
    print_info "PostgreSQL available at: localhost:${POSTGRES_HOST_PORT:-5432}"
    print_info "Redis available at: localhost:${REDIS_HOST_PORT:-6379}"
}

# Function to start services in demo mode
start_demo() {
    print_info "Starting full stack in demo mode..."
    check_env_file
    cleanup
    
    print_info "Building and starting services..."
    docker-compose --profile demo up --build -d
    
    print_success "Demo services started!"
    print_info "ELK Client available at: http://localhost:${ELK_CLIENT_HOST_PORT:-3000}"
    print_info "Corgi API available at: http://localhost:${CORGI_API_HOST_PORT:-5002}"
    print_info "PostgreSQL available at: localhost:${POSTGRES_HOST_PORT:-5432}"
    print_info "Redis available at: localhost:${REDIS_HOST_PORT:-6379}"
}

# Function to stop all services
stop_services() {
    print_info "Stopping all services..."
    docker-compose down -v
    print_success "All services stopped!"
}

# Function to show logs
show_logs() {
    if [ -z "$1" ]; then
        print_info "Showing logs for all services..."
        docker-compose logs -f
    else
        print_info "Showing logs for $1..."
        docker-compose logs -f "$1"
    fi
}

# Function to show service status
show_status() {
    print_info "Service status:"
    docker-compose ps
}

# Function to execute command in a service
exec_service() {
    if [ -z "$1" ]; then
        print_error "Please specify a service name"
        exit 1
    fi
    
    service=$1
    shift
    
    if [ -z "$1" ]; then
        # Default to bash if no command specified
        print_info "Executing bash in $service..."
        docker-compose exec "$service" /bin/bash
    else
        print_info "Executing command in $service..."
        docker-compose exec "$service" "$@"
    fi
}

# Function to run database migrations
run_migrations() {
    print_info "Running database migrations..."
    docker-compose exec corgi-api python -m flask db upgrade
    print_success "Migrations completed!"
}

# Function to show help
show_help() {
    cat << EOF
Corgi Recommender Service - Docker Development Control Script

Usage: $0 <command> [options]

Commands:
    standalone    Start Corgi API with dependencies (PostgreSQL, Redis)
    demo          Start full stack including ELK client frontend
    stop          Stop all services and clean up
    logs [service] Show logs (optionally for specific service)
    status        Show status of all services
    exec <service> [command]  Execute command in service container
    migrate       Run database migrations
    help          Show this help message

Examples:
    $0 standalone              # Start API in standalone mode
    $0 demo                    # Start full demo stack
    $0 logs corgi-api          # Show API logs
    $0 exec corgi-api bash     # Open bash shell in API container
    $0 exec postgres psql -U corgi -d corgi_db  # Connect to database
    $0 stop                    # Stop everything

Service Names:
    - postgres
    - redis
    - corgi-api
    - elk-client (demo mode only)

EOF
}

# Main script logic
case "$1" in
    standalone)
        start_standalone
        ;;
    demo)
        start_demo
        ;;
    stop)
        stop_services
        ;;
    logs)
        show_logs "$2"
        ;;
    status)
        show_status
        ;;
    exec)
        shift
        exec_service "$@"
        ;;
    migrate)
        run_migrations
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Invalid command: $1"
        show_help
        exit 1
        ;;
esac 