#!/bin/bash
# Debug script for troubleshooting recommendations not appearing in feed
# This helps diagnose when console says recs are generating but they don't show

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}🔍 Recommendations Debug Tool${NC}"
echo -e "${CYAN}This will help diagnose why recommendations aren't showing in the feed${NC}"
echo ""

# Check if we need credentials
echo -e "${YELLOW}Do you need to log in to see the feed? (y/n)${NC}"
read -p "Choice: " need_login

extra_args=""
if [ "$need_login" = "y" ] || [ "$need_login" = "Y" ]; then
    echo -e "${YELLOW}You can either:${NC}"
    echo "1) Provide credentials now (they'll only be used for this test)"
    echo "2) Run in headed mode and log in manually"
    read -p "Choice (1/2): " login_choice
    
    if [ "$login_choice" = "1" ]; then
        read -p "Username/Email: " username
        read -s -p "Password: " password
        echo ""
        extra_args="--username \"$username\" --password \"$password\""
    else
        extra_args="--headed"
        echo -e "${CYAN}Browser window will open - please log in manually${NC}"
    fi
fi

echo ""
echo -e "${CYAN}Running diagnostic tests...${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

# Run the test with verbose output
# Using correct ports: ELK on 3004, API on 9999
if [ -n "$extra_args" ]; then
    eval "python3 scripts/development/browser_agent.py --frontend-url http://localhost:3004 --api-url http://localhost:9999 --verbose $extra_args"
else
    python3 scripts/development/browser_agent.py --frontend-url http://localhost:3004 --api-url http://localhost:9999 --verbose
fi

# Check the results
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}❌ Issue detected with recommendations display!${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    
    echo ""
    echo -e "${YELLOW}📋 Quick Debugging Checklist:${NC}"
    echo ""
    echo -e "${BLUE}1. Check API Response:${NC}"
    echo "   curl http://localhost:5002/api/v1/recommendations"
    echo ""
    echo -e "${BLUE}2. Check Browser Console:${NC}"
    echo "   - Look for JavaScript errors"
    echo "   - Check network tab for failed requests"
    echo ""
    echo -e "${BLUE}3. Inspect DOM Elements:${NC}"
    echo "   - Right-click on timeline → Inspect"
    echo "   - Look for elements with:"
    echo "     • data-corgi-recommendation=\"true\""
    echo "     • class=\"corgi-recommendation\""
    echo "     • data-source=\"corgi\""
    echo ""
    echo -e "${BLUE}4. Check Frontend Code:${NC}"
    echo "   - Is the API response being parsed correctly?"
    echo "   - Are recommendations being rendered with identifiable attributes?"
    echo "   - Is there conditional rendering hiding them?"
    echo ""
    echo -e "${BLUE}5. Review Screenshots:${NC}"
    echo "   ls -la logs/screenshots/"
    echo "   open logs/screenshots/  # macOS"
    echo ""
    echo -e "${YELLOW}💡 Common Causes:${NC}"
    echo "   • Frontend not adding Corgi-specific attributes to recommended posts"
    echo "   • Recommendations mixed with regular posts without distinction"
    echo "   • API returning empty recommendation array"
    echo "   • Frontend filtering out recommendations by mistake"
    echo "   • CSS hiding recommendation indicators"
else
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Recommendations are displaying correctly!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
fi

echo ""
echo -e "${CYAN}📸 Screenshots saved in: logs/screenshots/${NC}"
echo -e "${CYAN}📝 Detailed logs in: logs/browser_agent.log${NC}"
echo -e "${CYAN}📊 Test results in: logs/latest_test_results.json${NC}" 