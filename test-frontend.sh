#!/bin/bash
# Quick frontend testing script
# This runs the intelligent browser agent to check if your changes work

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🤖 Intelligent Frontend Tester${NC}"
echo -e "${CYAN}This will automatically check if your frontend changes work!${NC}"
echo ""

# Check if services are running
check_service() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${GREEN}✓ $service is running on port $port${NC}"
        return 0
    else
        echo -e "${RED}✗ $service is not running on port $port${NC}"
        return 1
    fi
}

# Check services
api_running=false
frontend_running=false

if check_service 5002 "Corgi API"; then
    api_running=true
fi

if check_service 3000 "ELK Frontend"; then
    frontend_running=true
fi

# Offer to start services if not running
if [ "$api_running" = false ] || [ "$frontend_running" = false ]; then
    echo ""
    echo -e "${YELLOW}Some services are not running. Would you like to:${NC}"
    echo "1) Start missing services with 'make dev'"
    echo "2) Continue anyway"
    echo "3) Exit"
    read -p "Choice (1/2/3): " choice
    
    case $choice in
        1)
            echo -e "${YELLOW}Starting services...${NC}"
            make dev &
            echo -e "${CYAN}Waiting for services to start...${NC}"
            sleep 10
            ;;
        2)
            echo -e "${YELLOW}Continuing without all services...${NC}"
            ;;
        3)
            echo -e "${RED}Exiting.${NC}"
            exit 0
            ;;
    esac
fi

# Run the browser agent
echo ""
echo -e "${CYAN}Running browser tests...${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

# Parse command line arguments
if [ "$1" = "--headed" ] || [ "$1" = "-h" ]; then
    echo -e "${YELLOW}Running with visible browser...${NC}"
    python3 scripts/development/browser_agent.py --headed
elif [ "$1" = "--continuous" ] || [ "$1" = "-c" ]; then
    echo -e "${YELLOW}Running continuous testing (Ctrl+C to stop)...${NC}"
    python3 scripts/development/browser_agent.py --continuous
else
    python3 scripts/development/browser_agent.py
fi

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ All tests passed! Your changes work correctly!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
else
    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}❌ Tests failed! Check the output above for details.${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting tips:${NC}"
    echo "• Check if the API is properly connected"
    echo "• Look for console errors in the screenshots"
    echo "• Try running with --headed to see what's happening"
    echo "• Check logs/browser_agent.log for more details"
fi 