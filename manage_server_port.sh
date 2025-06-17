#!/bin/sh
# Corgi Recommender Service Port Manager
# A comprehensive tool for managing development services and preventing port conflicts
# POSIX-compliant for maximum compatibility

# Color codes (POSIX-compliant)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_NAME=$(basename "$0")
ENV_FILE=".env"
MAX_PORT_SCAN=10  # Maximum number of ports to scan when finding free port

# Default service configurations
DEFAULT_SERVICES="
api:CORGI_API_HOST_PORT:5002:python3 app.py
proxy:CORGI_PROXY_PORT:5003:python3 special_proxy.py
frontend:FRONTEND_PORT:3000:cd frontend && npm run dev
elk:ELK_PORT:5314:docker-compose up elk
flower:CELERY_FLOWER_PORT:5555:celery flower
redis:REDIS_PORT:6379:redis-server
postgres:DB_PORT:5432:postgres
"

# Utility functions
print_error() {
    printf "${RED}[ERROR]${NC} %s\n" "$1" >&2
}

print_warning() {
    printf "${YELLOW}[WARN]${NC} %s\n" "$1"
}

print_info() {
    printf "${BLUE}[INFO]${NC} %s\n" "$1"
}

print_success() {
    printf "${GREEN}[SUCCESS]${NC} %s\n" "$1"
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Load environment variables from .env file
load_env() {
    if [ -f "$ENV_FILE" ]; then
        # Read .env file line by line
        while IFS= read -r line || [ -n "$line" ]; do
            # Skip comments and empty lines
            case "$line" in
                \#*|"") continue ;;
            esac
            # Export valid environment variables
            if printf '%s' "$line" | grep -q '^[A-Za-z_][A-Za-z0-9_]*='; then
                # Extract key and value
                key=$(printf '%s' "$line" | cut -d= -f1)
                value=$(printf '%s' "$line" | cut -d= -f2-)
                # Remove quotes from value if present
                value=$(printf '%s' "$value" | sed 's/^["'\'']\(.*\)["'\'']$/\1/')
                # Export the cleaned variable
                eval "export $key=\"$value\""
            fi
        done < "$ENV_FILE"
        return 0
    else
        print_warning "No .env file found. Using default configurations."
        return 1
    fi
}

# Get service configuration
get_service_config() {
    service_name=$1
    
    # Load environment variables
    load_env
    
    # Parse service configurations
    printf '%s\n' "$DEFAULT_SERVICES" | while IFS=: read -r name var default_port command; do
        [ -z "$name" ] && continue
        if [ "$name" = "$service_name" ]; then
            # Get port from environment or use default
            port_value=$(eval "printf '%s' \"\${$var:-$default_port}\"")
            printf '%s:%s:%s' "$name" "$port_value" "$command"
            return 0
        fi
    done
    
    return 1
}

# Get all services
get_all_services() {
    load_env
    
    printf '%s\n' "$DEFAULT_SERVICES" | while IFS=: read -r name var default_port command; do
        [ -z "$name" ] && continue
        port_value=$(eval "printf '%s' \"\${$var:-$default_port}\"")
        printf '%s:%s:%s\n' "$name" "$port_value" "$command"
    done
}

# Check if port is in use
is_port_in_use() {
    port=$1
    
    # Try multiple methods to check port availability
    if command_exists lsof; then
        lsof -i :"$port" >/dev/null 2>&1
    elif command_exists netstat; then
        netstat -an 2>/dev/null | grep -q "[.:]$port .*LISTEN"
    elif command_exists ss; then
        ss -tlnp 2>/dev/null | grep -q ":$port "
    else
        # Fallback: try to connect to the port
        (printf '' | nc -w 1 localhost "$port") >/dev/null 2>&1
    fi
}

# Get process info for port
get_port_process() {
    port=$1
    
    if command_exists lsof; then
        lsof -i :"$port" -P -n 2>/dev/null | grep LISTEN | head -1
    elif command_exists netstat; then
        netstat -tlnp 2>/dev/null | grep ":$port " | head -1
    elif command_exists ss; then
        ss -tlnp 2>/dev/null | grep ":$port " | head -1
    else
        printf "Unable to determine process"
    fi
}

# Get PID for port
get_port_pid() {
    port=$1
    
    if command_exists lsof; then
        lsof -t -i :"$port" 2>/dev/null | head -1
    else
        # Try to extract PID from netstat/ss output
        process_info=$(get_port_process "$port")
        printf '%s' "$process_info" | awk '{for(i=1;i<=NF;i++) if($i ~ /^[0-9]+$/) {print $i; exit}}'
    fi
}

# Find next available port
find_next_free_port() {
    base_port=$1
    max_attempts=${2:-$MAX_PORT_SCAN}
    
    port=$base_port
    attempts=0
    
    while [ $attempts -lt $max_attempts ]; do
        if ! is_port_in_use "$port"; then
            printf '%d' "$port"
            return 0
        fi
        port=$((port + 1))
        attempts=$((attempts + 1))
    done
    
    return 1
}

# Display status table
display_status() {
    printf "\n${BOLD}Service Port Status${NC}\n"
    printf "%-15s %-15s %-10s %-10s %s\n" "SERVICE" "PORT" "STATUS" "PID" "COMMAND"
    printf "%-15s %-15s %-10s %-10s %s\n" "-------" "----" "------" "---" "-------"
    
    get_all_services | while IFS=: read -r name port command; do
        [ -z "$name" ] && continue
        
        if is_port_in_use "$port"; then
            status="${RED}IN-USE${NC}"
            pid=$(get_port_pid "$port")
            process_info=$(get_port_process "$port" | cut -c1-40)
        else
            status="${GREEN}FREE${NC}"
            pid="-"
            process_info="-"
        fi
        
        printf "%-15s %-15s %-20b %-10s %s\n" "$name" "$port" "$status" "$pid" "$process_info"
    done
    printf "\n"
}

# Start service
start_service() {
    service_name=$1
    
    config=$(get_service_config "$service_name")
    if [ -z "$config" ]; then
        print_error "Unknown service: $service_name"
        print_info "Available services: api, proxy, frontend, elk, flower, redis, postgres"
        return 1
    fi
    
    # Parse configuration
    name=$(printf '%s' "$config" | cut -d: -f1)
    port=$(printf '%s' "$config" | cut -d: -f2)
    command=$(printf '%s' "$config" | cut -d: -f3-)
    
    print_info "Checking port $port for service $name..."
    
    if is_port_in_use "$port"; then
        pid=$(get_port_pid "$port")
        process_info=$(get_port_process "$port")
        
        print_warning "Port $port is already in use!"
        printf "PID: %s\n" "$pid"
        printf "Process: %s\n" "$process_info"
        printf "\nWhat would you like to do?\n"
        printf "  ${BOLD}(K)${NC}ill the existing process\n"
        printf "  ${BOLD}(F)${NC}ind next available port\n"
        printf "  ${BOLD}(A)${NC}bort\n"
        printf "Choice [K/F/A]: "
        
        read -r choice
        
        case $(printf '%s' "$choice" | tr '[:upper:]' '[:lower:]') in
            k)
                print_info "Killing process $pid..."
                if kill -9 "$pid" 2>/dev/null; then
                    print_success "Process killed successfully"
                    sleep 1
                else
                    print_error "Failed to kill process. You may need sudo privileges."
                    return 1
                fi
                ;;
            f)
                print_info "Searching for next available port..."
                new_port=$(find_next_free_port $((port + 1)))
                if [ -n "$new_port" ]; then
                    print_success "Found free port: $new_port"
                    printf "Start $name on port $new_port? [Y/n]: "
                    read -r confirm
                    if [ "$confirm" != "n" ] && [ "$confirm" != "N" ]; then
                        port=$new_port
                    else
                        return 0
                    fi
                else
                    print_error "No free ports found in range"
                    return 1
                fi
                ;;
            *)
                print_info "Aborted"
                return 0
                ;;
        esac
    fi
    
    # Update command with the final port value, ensuring it's always passed
    case "$name" in
        api)
            command="CORGI_PORT=$port python3 app.py"
            ;;
        proxy)
            command="CORGI_PROXY_PORT=$port python3 special_proxy.py"
            ;;
        frontend)
            # npm run dev uses the PORT env var by default
            command="cd frontend && PORT=$port npm run dev"
            ;;
    esac

    # Start the service
    print_info "Starting $name on port $port..."
    print_info "Command: $command"
    
    # Create logs directory if it doesn't exist
    LOG_DIR="logs"
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/${name}.log"

    # Execute command in background and redirect output to log file
    if eval "$command" >"$LOG_FILE" 2>&1 & then
        new_pid=$!
        sleep 2  # Give service time to start
        
        # Check if service started successfully
        if kill -0 "$new_pid" 2>/dev/null; then
            print_success "$name started successfully (PID: $new_pid)"
            printf "Service log: %s\n" "$LOG_FILE"
        else
            print_error "Service failed to start. Check log for details: $LOG_FILE"
            return 1
        fi
    else
        print_error "Failed to execute command"
        return 1
    fi
}

# Stop service (graceful)
stop_service() {
    service_name=$1
    
    config=$(get_service_config "$service_name")
    if [ -z "$config" ]; then
        print_error "Unknown service: $service_name"
        return 1
    fi
    
    port=$(printf '%s' "$config" | cut -d: -f2)
    
    if ! is_port_in_use "$port"; then
        print_warning "Service $service_name is not running"
        return 0
    fi
    
    pid=$(get_port_pid "$port")
    if [ -z "$pid" ]; then
        print_error "Could not find process ID"
        return 1
    fi
    
    print_info "Stopping $service_name (PID: $pid) gracefully..."
    
    # Send SIGTERM for graceful shutdown
    if kill -TERM "$pid" 2>/dev/null; then
        # Wait up to 5 seconds for process to terminate
        count=0
        while [ $count -lt 5 ] && kill -0 "$pid" 2>/dev/null; do
            sleep 1
            count=$((count + 1))
            printf "."
        done
        printf "\n"
        
        if kill -0 "$pid" 2>/dev/null; then
            print_warning "Process didn't stop gracefully, sending SIGKILL..."
            kill -KILL "$pid" 2>/dev/null
        fi
        
        print_success "Service $service_name stopped"
    else
        print_error "Failed to stop service. You may need sudo privileges."
        return 1
    fi
}

# Kill service (force)
kill_service() {
    service_name=$1
    
    config=$(get_service_config "$service_name")
    if [ -z "$config" ]; then
        print_error "Unknown service: $service_name"
        return 1
    fi
    
    port=$(printf '%s' "$config" | cut -d: -f2)
    
    if ! is_port_in_use "$port"; then
        print_warning "Service $service_name is not running"
        return 0
    fi
    
    pid=$(get_port_pid "$port")
    if [ -z "$pid" ]; then
        print_error "Could not find process ID"
        return 1
    fi
    
    print_info "Force killing $service_name (PID: $pid)..."
    
    if kill -KILL "$pid" 2>/dev/null; then
        print_success "Service $service_name killed"
    else
        print_error "Failed to kill service. You may need sudo privileges."
        return 1
    fi
}

# Display help
show_help() {
    printf "${BOLD}Corgi Service Port Manager${NC}\n"
    printf "A comprehensive tool for managing development services and resolving port conflicts\n\n"
    
    printf "${BOLD}USAGE:${NC}\n"
    printf "    %s <command> [options]\n\n" "$SCRIPT_NAME"
    
    printf "${BOLD}COMMANDS:${NC}\n"
    printf "    ${CYAN}status${NC}              Display status of all configured services\n"
    printf "    ${CYAN}start <service>${NC}     Start a service (interactive if port conflict)\n"
    printf "    ${CYAN}stop <service>${NC}      Gracefully stop a service (SIGTERM then SIGKILL)\n"
    printf "    ${CYAN}kill <service>${NC}      Force kill a service (immediate SIGKILL)\n"
    printf "    ${CYAN}help${NC}                Display this help message\n\n"
    
    printf "${BOLD}SERVICES:${NC}\n"
    printf "    ${GREEN}api${NC}       - Corgi API server (default: 5002)\n"
    printf "    ${GREEN}proxy${NC}     - Special proxy server (default: 5003)\n"
    printf "    ${GREEN}frontend${NC}  - Next.js frontend (default: 3000)\n"
    printf "    ${GREEN}elk${NC}       - ELK stack (default: 5314)\n"
    printf "    ${GREEN}flower${NC}    - Celery Flower dashboard (default: 5555)\n"
    printf "    ${GREEN}redis${NC}     - Redis cache server (default: 6379)\n"
    printf "    ${GREEN}postgres${NC}  - PostgreSQL database (default: 5432)\n\n"
    
    printf "${BOLD}EXAMPLES:${NC}\n"
    printf "    # Check status of all services\n"
    printf "    %s status\n\n" "$SCRIPT_NAME"
    
    printf "    # Start the API service\n"
    printf "    %s start api\n\n" "$SCRIPT_NAME"
    
    printf "    # Gracefully stop the frontend\n"
    printf "    %s stop frontend\n\n" "$SCRIPT_NAME"
    
    printf "    # Force kill the proxy\n"
    printf "    %s kill proxy\n\n" "$SCRIPT_NAME"
    
    printf "${BOLD}ENVIRONMENT:${NC}\n"
    printf "    The script reads service ports from the .env file\n"
    printf "    If .env is missing, default ports are used\n\n"
    
    printf "${BOLD}PORT CONFLICT RESOLUTION:${NC}\n"
    printf "    When starting a service with a busy port, you can:\n"
    printf "    - Kill the existing process\n"
    printf "    - Find the next available port\n"
    printf "    - Abort the operation\n\n"
}

# Main function
main() {
    case "${1:-help}" in
        status)
            display_status
            ;;
        start)
            if [ -z "$2" ]; then
                print_error "Service name required"
                printf "Usage: %s start <service>\n" "$SCRIPT_NAME"
                exit 1
            fi
            start_service "$2"
            ;;
        stop)
            if [ -z "$2" ]; then
                print_error "Service name required"
                printf "Usage: %s stop <service>\n" "$SCRIPT_NAME"
                exit 1
            fi
            stop_service "$2"
            ;;
        kill)
            if [ -z "$2" ]; then
                print_error "Service name required"
                printf "Usage: %s kill <service>\n" "$SCRIPT_NAME"
                exit 1
            fi
            kill_service "$2"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            printf "Use '%s help' for usage information\n" "$SCRIPT_NAME"
            exit 1
            ;;
    esac
}

# Check for required commands
check_dependencies() {
    missing_deps=""
    
    # Check for at least one port checking tool
    if ! command_exists lsof && ! command_exists netstat && ! command_exists ss; then
        missing_deps="$missing_deps lsof|netstat|ss"
    fi
    
    if [ -n "$missing_deps" ]; then
        print_error "Missing required dependencies: $missing_deps"
        print_info "Please install at least one of: lsof, netstat, or ss"
        exit 1
    fi
}

# Entry point
check_dependencies
main "$@" 