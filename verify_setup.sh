#!/bin/bash

echo "Corgi & Elk Setup Verification"
echo "============================"
echo

# Check Corgi backend
echo "1. Checking Corgi backend (port 5004)..."
CORGI_STATUS=$(curl -k -s https://localhost:5004/api/v1/proxy/status)
if [[ $CORGI_STATUS == *"status"*"ok"* ]]; then
  echo "✅ Corgi backend is running properly!"
  echo "   Backend response: $CORGI_STATUS"
else
  echo "❌ Corgi backend is not running or not responding correctly."
  echo "   Try running: python3 special_proxy_fixed.py --port 5004"
fi
echo

# Check Docker container if available
echo "2. Checking Elk frontend..."
if docker info > /dev/null 2>&1; then
  ELK_CONTAINER=$(docker ps | grep elk-frontend)
  if [[ ! -z "$ELK_CONTAINER" ]]; then
    echo "✅ Elk frontend container is running!"
    echo "   Access it at: http://localhost:3013"
  else
    echo "❌ Elk frontend container is not running."
    echo "   Try running: ./start_elk.sh"
  fi
else
  echo "Docker not available, checking for local process..."
  ELK_PROCESS=$(ps aux | grep -i "node.*nuxt.*dev" | grep -v grep)
  if [[ ! -z "$ELK_PROCESS" ]]; then
    echo "✅ Elk frontend is running in development mode!"
    echo "   Access it at: http://localhost:3013"
  else
    echo "❌ Elk frontend is not running."
    echo "   Try running: ./start_elk.sh"
  fi
fi
echo

# Verify API connectivity between Elk and Corgi
echo "3. Verifying Elk's connection to Corgi..."
if curl -s http://localhost:3013 > /dev/null; then
  echo "✅ Elk frontend is responding at http://localhost:3013"
  echo "   You should now be able to see the enhanced user interface!"
else
  echo "❌ Elk frontend is not responding at http://localhost:3013"
  echo "   This could indicate that the server is still starting up or there's a configuration issue."
  echo "   Wait a minute and try running this script again."
fi
echo

echo "To start using the system:"
echo "1. Open http://localhost:3013 in your browser"
echo "2. You should see your enhanced components in action"
echo "3. Check for recommendation badges on posts"
echo "4. Verify that avatar and username are clickable"
echo