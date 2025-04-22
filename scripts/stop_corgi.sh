#!/bin/bash

# Stop Corgi Recommender Service script

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check for PID file
if [ -f corgi_server.pid ]; then
  PID=$(cat corgi_server.pid)
  echo -e "${BLUE}Found Corgi server PID: $PID${NC}"
  
  # Check if process exists
  if ps -p $PID > /dev/null; then
    echo -e "${YELLOW}Stopping Corgi server (PID: $PID)...${NC}"
    kill $PID
    
    # Wait for process to stop
    for i in {1..5}; do
      if ! ps -p $PID > /dev/null; then
        break
      fi
      echo -e "${BLUE}Waiting for process to terminate...${NC}"
      sleep 1
    done
    
    # Check if process is still running after timeout
    if ps -p $PID > /dev/null; then
      echo -e "${YELLOW}Process didn't terminate gracefully. Force killing...${NC}"
      kill -9 $PID
      sleep 1
    fi
    
    # Check once more
    if ! ps -p $PID > /dev/null; then
      echo -e "${GREEN}Corgi server stopped successfully.${NC}"
      rm corgi_server.pid
    else
      echo -e "${RED}Failed to stop Corgi server. Please check manually.${NC}"
      exit 1
    fi
  else
    echo -e "${YELLOW}Process with PID $PID is not running.${NC}"
    rm corgi_server.pid
    echo -e "${GREEN}Removed stale PID file.${NC}"
  fi
else
  # No PID file found, try to find by process name
  echo -e "${YELLOW}No PID file found. Trying to find Corgi processes...${NC}"
  
  # Find processes matching special_proxy_fixed.py
  PIDS=$(ps aux | grep -i "python.*special_proxy_fixed.py" | grep -v grep | awk '{print $2}')
  
  if [ -z "$PIDS" ]; then
    echo -e "${YELLOW}No running Corgi processes found.${NC}"
    exit 0
  else
    echo -e "${BLUE}Found these Corgi processes:${NC}"
    ps -o pid,ppid,cmd -p $PIDS
    
    echo -e "${YELLOW}Do you want to stop these processes? [y/N]${NC}"
    read -r response
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
      for pid in $PIDS; do
        echo -e "${BLUE}Stopping process $pid...${NC}"
        kill $pid
      done
      
      # Check if processes are still running
      sleep 2
      REMAINING=$(ps -p $PIDS 2>/dev/null | wc -l)
      
      if [ "$REMAINING" -gt 1 ]; then
        echo -e "${YELLOW}Some processes did not stop. Force killing remaining processes...${NC}"
        for pid in $PIDS; do
          if ps -p $pid > /dev/null; then
            kill -9 $pid
          fi
        done
      fi
      
      echo -e "${GREEN}All Corgi processes stopped.${NC}"
    else
      echo -e "${BLUE}No processes were stopped.${NC}"
    fi
  fi
fi

echo -e "${GREEN}Done.${NC}"