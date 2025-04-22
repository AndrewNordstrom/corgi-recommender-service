#!/bin/bash

# Make sure the Corgi server is running
CORGI_PID=$(ps aux | grep -i "python.*special_proxy_fixed.py" | grep -v grep | awk '{print $2}')
if [ -z "$CORGI_PID" ]; then
  echo "Starting Corgi backend on port 5004..."
  cd /Users/andrewnordstrom/corgi-recommender-service
  python3 special_proxy_fixed.py --port 5004 &
  sleep 2
fi

# Go to Elk directory and start it
echo "Starting Elk frontend..."
cd /Users/andrewnordstrom/elk-clean-repo
mkdir -p elk-data

# Check if Docker is running
if docker info > /dev/null 2>&1; then
  echo "Starting with Docker..."
  docker-compose down
  docker-compose up -d
  echo ""
  echo "Elk frontend is running on Docker!"
  echo "Access it at: http://localhost:3013"
  echo ""
  echo "To view logs: docker-compose logs -f elk-frontend"
  echo "To stop: docker-compose down"
else
  echo "Docker not available, starting in dev mode..."
  cd elk
  PORT=3013 NUXT_PUBLIC_DEFAULT_SERVER="localhost:5004" NUXT_PUBLIC_DISABLE_SERVER_SIDE_AUTH=true npm run dev
fi