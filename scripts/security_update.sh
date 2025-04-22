#!/bin/bash
# Script to apply security updates to Corgi Recommender Service

set -e  # Exit on any error

echo "Starting security updates..."

# Create a backup of current dependencies
echo "Creating backups of current dependency files..."
cp requirements.txt requirements.txt.bak
cp frontend/package.json frontend/package.json.bak

# Update backend dependencies
echo "Updating backend dependencies..."
pip install --upgrade pip
pip install --upgrade gunicorn>=22.0.1 psycopg2-binary>=2.9.9 urllib3>=2.0.7

# Update frontend dependencies
echo "Updating frontend dependencies..."
cd frontend
npm update next next-auth eslint-config-next
cd ..

# Run tests to verify everything still works
echo "Running backend tests..."
pytest

# Check if tests pass
if [ $? -eq 0 ]; then
    echo "Backend tests passed successfully!"
else
    echo "Backend tests failed. Rolling back to backup..."
    mv requirements.txt.bak requirements.txt
    pip install -r requirements.txt
    exit 1
fi

# Try to run frontend tests if they exist
if [ -f "frontend/package.json" ]; then
    echo "Running frontend tests..."
    cd frontend
    if npm test; then
        echo "Frontend tests passed successfully!"
    else
        echo "Frontend tests failed. Rolling back to backup..."
        mv frontend/package.json.bak frontend/package.json
        npm install
        exit 1
    fi
    cd ..
fi

# Summary of changes
echo "Security updates applied successfully!"
echo "Updated dependencies:"
echo "- gunicorn to >=22.0.1"
echo "- next.js to ^14.4.2"
echo "- next-auth to ^4.24.10"
echo "- eslint-config-next to ^14.4.2"

echo "Backup files (.bak) have been created and can be removed if everything works correctly."

# Make the script executable
chmod +x scripts/security_update.sh