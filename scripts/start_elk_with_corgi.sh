#!/bin/bash

# Start Elk with Corgi integration
# This script starts Elk and optionally ensures Corgi is running

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
ELK_PORT=3013
CORGI_PORT=5004
START_CORGI=false
ELK_PATH="/Users/andrewnordstrom/elk-clean-repo/elk"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --elk-port)
      ELK_PORT="$2"
      shift
      shift
      ;;
    --corgi-port)
      CORGI_PORT="$2"
      shift
      shift
      ;;
    --with-corgi)
      START_CORGI=true
      shift
      ;;
    --elk-path)
      ELK_PATH="$2"
      shift
      shift
      ;;
    --help)
      echo "Usage: ./start_elk_with_corgi.sh [options]"
      echo "Options:"
      echo "  --elk-port PORT      Specify port for Elk (default: 3013)"
      echo "  --corgi-port PORT    Specify port for Corgi (default: 5004)"
      echo "  --with-corgi         Start Corgi if it's not already running"
      echo "  --elk-path PATH      Specify path to the Elk directory (default: ~/elk-clean-repo/elk)"
      echo "  --help               Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $key"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Display banner
echo -e "${GREEN}===========================================================${NC}"
echo -e "${GREEN}Starting Elk with Corgi Integration${NC}"
echo -e "${GREEN}===========================================================${NC}"
echo

# Check if Elk path exists
if [ ! -d "$ELK_PATH" ]; then
  echo -e "${RED}Error: Elk directory not found at $ELK_PATH${NC}"
  echo -e "${YELLOW}Please specify the correct path using --elk-path option.${NC}"
  exit 1
fi

# Check if Corgi is running
CORGI_RUNNING=false
CORGI_PID=$(ps aux | grep -i "python.*special_proxy_fixed.py.*--port $CORGI_PORT" | grep -v grep | awk '{print $2}')

if [ -n "$CORGI_PID" ]; then
  CORGI_RUNNING=true
  echo -e "${GREEN}✓ Corgi is already running on port $CORGI_PORT (PID: $CORGI_PID)${NC}"
else
  echo -e "${YELLOW}! Corgi is not running on port $CORGI_PORT${NC}"
  
  if [ "$START_CORGI" = true ]; then
    echo -e "${BLUE}Starting Corgi...${NC}"
    
    # Start Corgi using the start_corgi.sh script
    CORGI_SCRIPT_PATH="$(dirname "$0")/start_corgi.sh"
    
    if [ -f "$CORGI_SCRIPT_PATH" ]; then
      # Use the script with port specified
      bash "$CORGI_SCRIPT_PATH" --port $CORGI_PORT
      
      # Check if it started successfully
      sleep 2
      CORGI_PID=$(ps aux | grep -i "python.*special_proxy_fixed.py.*--port $CORGI_PORT" | grep -v grep | awk '{print $2}')
      
      if [ -n "$CORGI_PID" ]; then
        CORGI_RUNNING=true
        echo -e "${GREEN}✓ Corgi started successfully on port $CORGI_PORT${NC}"
      else
        echo -e "${RED}Failed to start Corgi.${NC}"
      fi
    else
      echo -e "${RED}Error: start_corgi.sh script not found at $CORGI_SCRIPT_PATH${NC}"
      echo -e "${YELLOW}Continuing without Corgi. Elk will use its default backend.${NC}"
    fi
  else
    echo -e "${YELLOW}Not starting Corgi (use --with-corgi to start it automatically).${NC}"
    echo -e "${YELLOW}Elk will use its default backend.${NC}"
  fi
fi

echo
echo -e "${BLUE}Starting Elk on port $ELK_PORT...${NC}"

# Create a temporary script to run npm command in the Elk directory
TMP_SCRIPT=$(mktemp)
cat > $TMP_SCRIPT << EOF
#!/bin/bash
cd "$ELK_PATH"
export PORT=$ELK_PORT
EOF

# Add Corgi backend configuration if Corgi is running
if [ "$CORGI_RUNNING" = true ]; then
  cat >> $TMP_SCRIPT << EOF
export NUXT_PUBLIC_DEFAULT_SERVER="localhost:$CORGI_PORT"
export NUXT_PUBLIC_DISABLE_SERVER_SIDE_AUTH=true
export NUXT_PUBLIC_PREFER_WSS=false
EOF
  echo -e "${GREEN}✓ Configured Elk to use Corgi backend at localhost:$CORGI_PORT${NC}"
else
  echo -e "${YELLOW}! Elk will use its default backend settings${NC}"
fi

# Add the npm command
cat >> $TMP_SCRIPT << EOF
echo "Starting Elk development server..."
npm run dev
EOF

chmod +x $TMP_SCRIPT

echo -e "${BLUE}Starting Elk in foreground mode...${NC}"
echo -e "${GREEN}===========================================================${NC}"
echo -e "${GREEN}Elk will be available at: http://localhost:$ELK_PORT${NC}"
echo -e "${GREEN}===========================================================${NC}"
echo
echo -e "${YELLOW}Note: Press Ctrl+C to stop Elk when you're finished.${NC}"
echo

# Execute the script
$TMP_SCRIPT

# Clean up
rm $TMP_SCRIPT

# If we get here, Elk has stopped
echo
echo -e "${GREEN}Elk has stopped.${NC}"

# If we started Corgi, ask if we should stop it too
if [ "$START_CORGI" = true ] && [ "$CORGI_RUNNING" = true ]; then
  echo -e "${YELLOW}Do you want to stop Corgi as well? [y/N]${NC}"
  read -r response
  
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    CORGI_STOP_SCRIPT_PATH="$(dirname "$0")/stop_corgi.sh"
    
    if [ -f "$CORGI_STOP_SCRIPT_PATH" ]; then
      bash "$CORGI_STOP_SCRIPT_PATH"
    else
      echo -e "${RED}Error: stop_corgi.sh script not found at $CORGI_STOP_SCRIPT_PATH${NC}"
      echo -e "${YELLOW}Please stop Corgi manually.${NC}"
    fi
  else
    echo -e "${BLUE}Leaving Corgi running.${NC}"
  fi
fi

echo -e "${GREEN}Done.${NC}"