#!/bin/bash

# Start Corgi Recommender Service
# This script starts the Corgi backend without any dependencies on Elk or other frontends

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PORT=5004
USE_HTTPS=true
HOST="0.0.0.0"
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --port|-p)
      PORT="$2"
      shift
      shift
      ;;
    --host|-h)
      HOST="$2"
      shift
      shift
      ;;
    --no-https)
      USE_HTTPS=false
      shift
      ;;
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    --help)
      echo "Usage: ./start_corgi.sh [options]"
      echo "Options:"
      echo "  --port, -p PORT      Specify port to run on (default: 5004)"
      echo "  --host, -h HOST      Specify host to bind to (default: 0.0.0.0)"
      echo "  --no-https           Disable HTTPS (not recommended for production)"
      echo "  --verbose, -v        Enable verbose output"
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

# Check if certs exist if using HTTPS
if [ "$USE_HTTPS" = true ]; then
  CERT_PATH="$PWD/certs/cert.pem"
  KEY_PATH="$PWD/certs/key.pem"
  
  if [ ! -f "$CERT_PATH" ] || [ ! -f "$KEY_PATH" ]; then
    echo -e "${YELLOW}Warning: SSL certificates not found at $CERT_PATH and $KEY_PATH${NC}"
    echo -e "${YELLOW}Creating self-signed certificates in the certs directory...${NC}"
    
    # Create certs directory if it doesn't exist
    mkdir -p "$PWD/certs"
    
    # Generate self-signed certificates
    openssl req -x509 -newkey rsa:4096 -keyout "$KEY_PATH" -out "$CERT_PATH" -days 365 -nodes -subj "/CN=localhost" 2> /dev/null
    
    if [ $? -ne 0 ]; then
      echo -e "${YELLOW}Failed to create self-signed certificates. Falling back to HTTP.${NC}"
      USE_HTTPS=false
    else
      echo -e "${GREEN}Self-signed certificates created successfully.${NC}"
    fi
  fi
fi

# Build the command
CMD="python3 special_proxy_fixed.py --port $PORT --host $HOST"

if [ "$USE_HTTPS" = false ]; then
  CMD="$CMD --no-https"
fi

# Check for existing process
EXISTING_PID=$(ps aux | grep -i "python.*special_proxy_fixed.py.*--port $PORT" | grep -v grep | awk '{print $2}')
if [ -n "$EXISTING_PID" ]; then
  echo -e "${YELLOW}Warning: Corgi seems to be already running on port $PORT (PID: $EXISTING_PID).${NC}"
  echo -e "Would you like to:"
  echo -e "  1) Stop the existing process and start a new one"
  echo -e "  2) Continue anyway (may cause port conflicts)"
  echo -e "  3) Exit"
  read -p "Enter choice [1-3]: " choice
  
  case $choice in
    1)
      echo -e "${YELLOW}Stopping existing Corgi process (PID: $EXISTING_PID)...${NC}"
      kill $EXISTING_PID
      sleep 2
      ;;
    2)
      echo -e "${YELLOW}Continuing anyway. Be aware of potential port conflicts.${NC}"
      ;;
    3)
      echo -e "${BLUE}Exiting.${NC}"
      exit 0
      ;;
    *)
      echo -e "${YELLOW}Invalid choice. Exiting.${NC}"
      exit 1
      ;;
  esac
fi

# Display start message
echo -e "${GREEN}===========================================================${NC}"
echo -e "${GREEN}Starting Corgi Recommender Service${NC}"
echo -e "${GREEN}===========================================================${NC}"
echo
echo -e "${BLUE}Configuration:${NC}"
echo -e "  Host:       ${YELLOW}$HOST${NC}"
echo -e "  Port:       ${YELLOW}$PORT${NC}"
echo -e "  Protocol:   ${YELLOW}$([ "$USE_HTTPS" = true ] && echo "HTTPS" || echo "HTTP")${NC}"
echo

# Start Corgi
if [ "$VERBOSE" = true ]; then
  echo -e "${BLUE}Starting with command: $CMD${NC}"
  echo
  eval $CMD
else
  echo -e "${BLUE}Starting Corgi in the background... (use --verbose for detailed output)${NC}"
  eval "$CMD > /tmp/corgi_server.log 2>&1 &"
  PID=$!
  echo $PID > corgi_server.pid
  echo -e "${GREEN}Corgi started with PID $PID${NC}"
  echo -e "${BLUE}Logs are being written to /tmp/corgi_server.log${NC}"
  echo
  echo -e "${BLUE}API endpoints available at:${NC}"
  echo -e "  $([ "$USE_HTTPS" = true ] && echo "https" || echo "http")://$([[ "$HOST" == "0.0.0.0" ]] && echo "localhost" || echo "$HOST"):$PORT/api/v1/timelines/home"
  echo -e "  $([ "$USE_HTTPS" = true ] && echo "https" || echo "http")://$([[ "$HOST" == "0.0.0.0" ]] && echo "localhost" || echo "$HOST"):$PORT/api/v1/proxy/status"
  echo
  echo -e "${BLUE}To stop Corgi, run:${NC}"
  echo -e "  ./scripts/stop_corgi.sh"
  echo
  echo -e "${GREEN}===========================================================${NC}"
fi