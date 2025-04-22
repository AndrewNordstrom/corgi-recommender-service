#!/bin/bash

echo "Starting Elk frontend in development mode..."
echo "This will connect to the Corgi backend at localhost:5004"
echo

# Make sure Corgi is running
CORGI_PID=$(ps aux | grep -i "python.*special_proxy_fixed.py" | grep -v grep | awk '{print $2}')
if [ -z "$CORGI_PID" ]; then
  echo "Starting Corgi backend on port 5004..."
  cd /Users/andrewnordstrom/corgi-recommender-service
  python3 special_proxy_fixed.py --port 5004 &
  sleep 2
fi

# Create a temporary script that will run the npm command
TMP_SCRIPT=$(mktemp)
cat > $TMP_SCRIPT << 'EOF'
#!/bin/bash
cd /Users/andrewnordstrom/elk-clean-repo/elk
export PORT=3013
export NUXT_PUBLIC_DEFAULT_SERVER="localhost:5004" 
export NUXT_PUBLIC_DISABLE_SERVER_SIDE_AUTH=true

# Note that we've fixed the following components to use proper class format:
# 1. StatusAccountHeader.vue
# 2. RecommendationBadge.vue 
# 3. StatusCard.vue

echo "Starting Elk development server with your customized components..."
npm run dev
EOF

chmod +x $TMP_SCRIPT

echo "Starting Elk development server..."
echo "You can access the app at: http://localhost:3013"
echo
echo "Note: We've updated your Vue components to use proper class formats"
echo "instead of attribute-based utility classes, which were causing errors."
echo
echo "Press Ctrl+C to stop the server when you're done"
echo

# Run the script
$TMP_SCRIPT

# Clean up
rm $TMP_SCRIPT