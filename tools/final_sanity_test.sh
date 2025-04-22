#!/bin/bash

# Corgi Recommender Final Sanity Test
# This script performs a final sanity check on the Corgi Recommender system
# to ensure that the middleware proxy and documentation are fully operational.

# Colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# API settings
API_PORT=5001
API_HOST="localhost"
API_BASE="http://${API_HOST}:${API_PORT}"
MAX_RETRIES=30
RETRY_INTERVAL=1

# Log directories
LOG_DIR="../logs"
PROXY_LOG="$LOG_DIR/proxy.log"
INTERACTION_LOG="$LOG_DIR/proxy_interactions.log"

# Test statuses
HEALTH_STATUS=0
TIMELINE_STATUS=0
FAVORITE_STATUS=0
LOGS_STATUS=0

# Print header
echo -e "${BOLD}======================================${NC}"
echo -e "${BOLD}   Corgi Recommender Sanity Test     ${NC}"
echo -e "${BOLD}======================================${NC}"
echo ""

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to print success/failure
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# Function to check if a process is running on the specified port
check_port() {
    if command -v lsof >/dev/null 2>&1; then
        lsof -i:$1 >/dev/null 2>&1
        return $?
    elif command -v netstat >/dev/null 2>&1; then
        netstat -tuln | grep -q ":$1 "
        return $?
    else
        # Fallback to a direct connection attempt
        nc -z localhost $1 >/dev/null 2>&1
        return $?
    fi
}

# Function to start the server if it's not already running
start_server() {
    echo -e "${YELLOW}Checking if server is already running on port $API_PORT...${NC}"
    
    if check_port $API_PORT; then
        echo -e "${CYAN}Server is already running on port $API_PORT${NC}"
    else
        echo -e "${YELLOW}Starting Corgi Recommender API server on port $API_PORT...${NC}"
        
        # Export environment variables for the server
        export HOST="0.0.0.0"
        export PORT=$API_PORT
        export FLASK_ENV="development"
        
        # Start the server in the background
        (cd .. && python -m flask --app app run --host=$HOST --port=$PORT > "$LOG_DIR/server_startup.log" 2>&1) &
        
        # Store the server PID
        SERVER_PID=$!
        
        echo -e "${CYAN}Server started with PID: $SERVER_PID${NC}"
        
        # Write PID to file for later cleanup
        echo $SERVER_PID > "$LOG_DIR/server.pid"
        
        # Give the server a moment to start
        sleep 2
    fi
}

# Function to wait for the server to become available
wait_for_server() {
    echo -e "${YELLOW}Waiting for server to become available...${NC}"
    
    for i in $(seq 1 $MAX_RETRIES); do
        if curl -s "$API_BASE/health" > /dev/null; then
            echo -e "${GREEN}Server is up and running!${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}Waiting for server to start (attempt $i/$MAX_RETRIES)...${NC}"
        sleep $RETRY_INTERVAL
    done
    
    echo -e "${RED}Server failed to start within the expected time!${NC}"
    return 1
}

# Function to run the health check
check_health() {
    echo -e "\n${BOLD}1. Health Check${NC}"
    
    response=$(curl -s "$API_BASE/health")
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        echo -e "${CYAN}Health check response: $response${NC}"
        HEALTH_STATUS=0
    else
        echo -e "${RED}Health check failed!${NC}"
        HEALTH_STATUS=1
    fi
    
    print_status $HEALTH_STATUS "Health check"
}

# Function to test the timeline endpoint
test_timeline() {
    echo -e "\n${BOLD}2. Timeline Test${NC}"
    
    response=$(curl -s -H "Authorization: Bearer test_sanity_token" \
                    -H "X-Mastodon-Instance: mastodon.social" \
                    "$API_BASE/api/v1/timelines/home")
    
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        echo -e "${CYAN}Timeline response received (${#response} bytes)${NC}"
        TIMELINE_STATUS=0
    else
        echo -e "${RED}Timeline request failed!${NC}"
        TIMELINE_STATUS=1
    fi
    
    print_status $TIMELINE_STATUS "Timeline test"
}

# Function to test the favorite endpoint
test_favorite() {
    echo -e "\n${BOLD}3. Interaction Test (Favourite)${NC}"
    
    echo -e "${YELLOW}Sending a POST request to /api/v1/statuses/123456/favourite${NC}"
    
    response=$(curl -s -X POST \
                   -H "Authorization: Bearer test_sanity_token" \
                   -H "X-Mastodon-Instance: mastodon.social" \
                   -H "Content-Type: application/json" \
                   "$API_BASE/api/v1/statuses/123456/favourite")
    
    if [ $? -eq 0 ]; then
        echo -e "${CYAN}Favourite response received: $response${NC}"
        FAVORITE_STATUS=0
    else
        echo -e "${RED}Favourite request failed!${NC}"
        FAVORITE_STATUS=1
    fi
    
    print_status $FAVORITE_STATUS "Interaction test"
    
    # Give the server time to process and log the interaction
    sleep 2
}

# Function to check the logs
check_logs() {
    echo -e "\n${BOLD}4. Log Check${NC}"
    
    LOGS_STATUS=0
    
    # Check proxy log
    if [ -f "$PROXY_LOG" ]; then
        echo -e "${CYAN}Proxy log found. Last few lines:${NC}"
        tail -n 5 "$PROXY_LOG"
    else
        echo -e "${RED}Proxy log not found at $PROXY_LOG${NC}"
        LOGS_STATUS=1
    fi
    
    echo ""
    
    # Check interaction log
    if [ -f "$INTERACTION_LOG" ]; then
        echo -e "${CYAN}Interaction log found. Last few lines:${NC}"
        tail -n 5 "$INTERACTION_LOG"
    else
        echo -e "${RED}Interaction log not found at $INTERACTION_LOG${NC}"
        LOGS_STATUS=1
    fi
    
    print_status $LOGS_STATUS "Log check"
}

# Function to kill the server if we started it
cleanup() {
    if [ -f "$LOG_DIR/server.pid" ]; then
        PID=$(cat "$LOG_DIR/server.pid")
        if ps -p $PID > /dev/null; then
            echo -e "\n${YELLOW}Stopping server with PID $PID...${NC}"
            kill $PID
            sleep 1
            if ps -p $PID > /dev/null; then
                echo -e "${RED}Server didn't stop gracefully, forcing...${NC}"
                kill -9 $PID
            fi
            echo -e "${GREEN}Server stopped.${NC}"
        fi
        rm "$LOG_DIR/server.pid"
    fi
}

# Trap for clean exit
trap cleanup EXIT

# Main execution flow
start_server
wait_for_server
check_health
test_timeline
test_favorite
check_logs

# Final summary
echo -e "\n${BOLD}======================================${NC}"
echo -e "${BOLD}           Test Summary             ${NC}"
echo -e "${BOLD}======================================${NC}"
print_status $HEALTH_STATUS "Health check"
print_status $TIMELINE_STATUS "Timeline test"
print_status $FAVORITE_STATUS "Interaction test"
print_status $LOGS_STATUS "Log check"

# Calculate overall status
OVERALL_STATUS=$(( HEALTH_STATUS + TIMELINE_STATUS + FAVORITE_STATUS + LOGS_STATUS ))
if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "\n${GREEN}${BOLD}All tests passed! The Corgi Recommender system is operational.${NC}"
    exit 0
else
    echo -e "\n${RED}${BOLD}Some tests failed. Please check the logs for details.${NC}"
    exit 1
fi