#!/bin/bash

# End-to-end startup script for Corgi + Elk integration
# This script will:
# 1. Start the Corgi backend if it's not already running
# 2. Start the Elk frontend pointing to Corgi
# 3. Provide instructions for testing the integration

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default configuration
CORGI_PORT=5004
ELK_PORT=3013
ELK_PATH="/Users/andrewnordstrom/elk-clean-repo/elk"
BROWSER_INJECTION=true

echo -e "${GREEN}===========================================================${NC}"
echo -e "${GREEN}      CORGI + ELK END-TO-END STARTUP${NC}"
echo -e "${GREEN}===========================================================${NC}"
echo

# 1. Check if Corgi is already running
echo -e "${BLUE}Step 1: Checking if Corgi is already running...${NC}"
CORGI_PID=$(ps aux | grep -i "python.*special_proxy_fixed.py.*--port $CORGI_PORT" | grep -v grep | awk '{print $2}')

if [ -n "$CORGI_PID" ]; then
  echo -e "${GREEN}✓ Corgi is already running on port $CORGI_PORT (PID: $CORGI_PID)${NC}"
else
  echo -e "${YELLOW}! Corgi is not running. Starting it now...${NC}"
  
  # Start Corgi using our modular script
  echo -e "${BLUE}Starting Corgi on port $CORGI_PORT...${NC}"
  cd "$(dirname "$0")"
  ./scripts/start_corgi.sh --port $CORGI_PORT
  
  # Verify Corgi started successfully
  sleep 2
  CORGI_PID=$(ps aux | grep -i "python.*special_proxy_fixed.py.*--port $CORGI_PORT" | grep -v grep | awk '{print $2}')
  
  if [ -n "$CORGI_PID" ]; then
    echo -e "${GREEN}✓ Corgi started successfully on port $CORGI_PORT (PID: $CORGI_PID)${NC}"
  else
    echo -e "${RED}✗ Failed to start Corgi. Please check the logs at /tmp/corgi_server.log${NC}"
    exit 1
  fi
fi

# 2. Verify Corgi API is responding
echo
echo -e "${BLUE}Step 2: Verifying Corgi API is responding...${NC}"
CORGI_STATUS=$(curl -k -s "https://localhost:$CORGI_PORT/api/v1/proxy/status")

if [[ $CORGI_STATUS == *"status"*"ok"* ]]; then
  echo -e "${GREEN}✓ Corgi API is responding properly!${NC}"
  echo -e "   API response: $CORGI_STATUS"
else
  echo -e "${RED}✗ Corgi API is not responding correctly.${NC}"
  echo -e "${YELLOW}Attempting to restart Corgi...${NC}"
  
  # Kill existing process and start again
  kill $CORGI_PID
  sleep 2
  ./scripts/start_corgi.sh --port $CORGI_PORT
  
  # Check again
  sleep 2
  CORGI_STATUS=$(curl -k -s "https://localhost:$CORGI_PORT/api/v1/proxy/status")
  
  if [[ $CORGI_STATUS == *"status"*"ok"* ]]; then
    echo -e "${GREEN}✓ Corgi API is now responding after restart!${NC}"
  else
    echo -e "${RED}✗ Corgi API is still not responding. Please check the logs.${NC}"
    exit 1
  fi
fi

# 3. Create a temporary script to start Elk with proper environment variables
echo
echo -e "${BLUE}Step 3: Preparing to start Elk frontend...${NC}"

# Check if Elk directory exists
if [ ! -d "$ELK_PATH" ]; then
  echo -e "${RED}✗ Elk directory not found at $ELK_PATH${NC}"
  echo -e "${YELLOW}Please update the ELK_PATH variable in this script.${NC}"
  exit 1
fi

# Create a temporary script for starting Elk
TMP_SCRIPT=$(mktemp)
cat > $TMP_SCRIPT << EOF
#!/bin/bash
cd "$ELK_PATH"
export PORT=$ELK_PORT
export NUXT_PUBLIC_DEFAULT_SERVER="localhost:$CORGI_PORT"
export NUXT_PUBLIC_DISABLE_SERVER_SIDE_AUTH=true
export NUXT_PUBLIC_PREFER_WSS=false

echo "Starting Elk development server on port $ELK_PORT..."
npm run dev
EOF

chmod +x $TMP_SCRIPT

# 4. Prepare browser injection script if enabled
if [ "$BROWSER_INJECTION" = true ]; then
  echo -e "${BLUE}Step 4: Preparing browser injection script...${NC}"
  
  INJECTION_DIR="$(dirname "$0")/integrations/browser_injection"
  INJECTION_FILE="$INJECTION_DIR/simple_elk_integration.js"
  
  if [ -f "$INJECTION_FILE" ]; then
    echo -e "${GREEN}✓ Browser injection script found at:${NC}"
    echo -e "   $INJECTION_FILE"
  else
    echo -e "${RED}✗ Browser injection script not found.${NC}"
    echo -e "${YELLOW}The integration might not show recommendation badges or clickable profiles.${NC}"
  fi
fi

# 5. Start Elk and provide instructions
echo
echo -e "${GREEN}===========================================================${NC}"
echo -e "${GREEN}     STARTUP COMPLETE - FOLLOW THESE STEPS${NC}"
echo -e "${GREEN}===========================================================${NC}"
echo
echo -e "${BLUE}1. Elk will start in a moment at: ${GREEN}http://localhost:$ELK_PORT${NC}"
echo
echo -e "${BLUE}2. When Elk loads, configure it as follows:${NC}"
echo -e "   - Server: ${GREEN}localhost:$CORGI_PORT${NC} (no http:// or https://)"
echo -e "   - Sign in with your Mastodon credentials"
echo
echo -e "${BLUE}3. To enable enhanced UI features like recommendation badges:${NC}"
echo -e "   - Open browser developer tools (F12 or Cmd+Option+I)"
echo -e "   - Go to the Console tab"
echo -e "   - Copy and paste the contents of the script at:${NC}"
echo -e "     ${GREEN}$INJECTION_FILE${NC}"
echo
echo -e "${BLUE}4. You should now see:${NC}"
echo -e "   - Recommendation badges on recommended posts"
echo -e "   - Clickable profile pictures and usernames"
echo -e "   - Enhanced timeline with Corgi recommendations"
echo
echo -e "${YELLOW}Starting Elk now...${NC}"
echo -e "${YELLOW}(Press Ctrl+C to stop Elk when you're done)${NC}"
echo

# Start Elk
$TMP_SCRIPT

# Clean up
rm $TMP_SCRIPT

# If we get here, Elk has been stopped
echo
echo -e "${GREEN}===========================================================${NC}"
echo -e "${GREEN}     ELK FRONTEND STOPPED${NC}"
echo -e "${GREEN}===========================================================${NC}"
echo
echo -e "${BLUE}Corgi is still running in the background.${NC}"
echo -e "${BLUE}To stop Corgi, run:${NC}"
echo -e "   ${GREEN}./scripts/stop_corgi.sh${NC}"
echo