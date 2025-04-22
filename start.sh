#!/bin/bash
set -e

# Enhanced startup script for Corgi Recommender Service
# Compatible with both local development and cloud platforms (Render, Fly.io, etc.)

echo "🚀 Corgi Recommender Service - Startup Script"
echo "=============================================="

# Function to wait for PostgreSQL to be ready
wait_for_postgres() {
    host="${POSTGRES_HOST:-localhost}"
    port="${DB_PORT:-5432}"
    user="${POSTGRES_USER:-postgres}"
    db="${POSTGRES_DB:-corgi_recommender}"
    max_retries=${MAX_DB_RETRIES:-30}
    retry_count=0
    
    echo "📊 Waiting for PostgreSQL at $host:$port to be ready..."
    
    # Use PostgreSQL client if available
    if command -v pg_isready &> /dev/null; then
        while ! pg_isready -h "$host" -p "$port" -U "$user" > /dev/null 2>&1; do
            retry_count=$((retry_count+1))
            if [ $retry_count -ge $max_retries ]; then
                echo "❌ ERROR: PostgreSQL still not available after $max_retries attempts. Exiting."
                exit 1
            fi
            echo "⏳ PostgreSQL is unavailable - sleeping 2 seconds (attempt $retry_count/$max_retries)"
            sleep 2
        done
    # Otherwise use netcat or an equivalent tool
    elif command -v nc &> /dev/null; then
        while ! nc -z "$host" "$port"; do
            retry_count=$((retry_count+1))
            if [ $retry_count -ge $max_retries ]; then
                echo "❌ ERROR: PostgreSQL still not available after $max_retries attempts. Exiting."
                exit 1
            fi
            echo "⏳ PostgreSQL is unavailable - sleeping 2 seconds (attempt $retry_count/$max_retries)"
            sleep 2
        done
    else
        # Simple sleep as fallback
        echo "⚠️ No tools available to check PostgreSQL, sleeping 10 seconds"
        sleep 10
    fi
    
    # Verify database connectivity and existence
    echo "🔍 Verifying database connectivity and existence..."
    if command -v psql &> /dev/null; then
        if ! psql -h "$host" -p "$port" -U "$user" -d "$db" -c "SELECT 1" &> /dev/null; then
            echo "⚠️ Database '$db' might not exist, attempting to create it..."
            psql -h "$host" -p "$port" -U "$user" -c "CREATE DATABASE $db;" || true
        fi
    fi
    
    echo "✅ PostgreSQL is up and ready!"
}

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "📄 Loading environment from .env file"
    export $(grep -v '^#' .env | xargs)
fi

# Set default environment variables if not already set
export PORT=${PORT:-5000}
export HOST=${HOST:-0.0.0.0}
export FLASK_ENV=${FLASK_ENV:-development}
export DEBUG=${DEBUG:-False}
export LOG_LEVEL=${LOG_LEVEL:-INFO}
export WORKERS=${WORKERS:-2}
export THREADS=${THREADS:-4}
export WORKER_CLASS=${WORKER_CLASS:-gthread}
export REQUEST_TIMEOUT=${REQUEST_TIMEOUT:-120}

# Auto-detect if we're running on Render.com
if [ -n "$RENDER" ]; then
    echo "🔍 Detected Render.com environment"
    export FLASK_ENV=production
fi

# Auto-detect if we're running on Fly.io
if [ -n "$FLY_APP_NAME" ]; then
    echo "🔍 Detected Fly.io environment"
    export FLASK_ENV=production
fi

echo "🚀 Starting Corgi Recommender Service on ${HOST}:${PORT}"
echo "📊 Environment: FLASK_ENV=${FLASK_ENV}, DEBUG=${DEBUG}, LOG_LEVEL=${LOG_LEVEL}"

# Wait for PostgreSQL to be ready
wait_for_postgres

# Initialize the database schema
echo "🔧 Initializing database schema..."
python -c "from db.connection import init_db; init_db()"

# Determine how to run the application based on environment
if [ "$FLASK_ENV" = "development" ]; then
    echo "🛠️ Starting development server..."
    # Use Flask's built-in server for development
    python -m flask --app app run --host=${HOST} --port=${PORT} --debug
else
    echo "🚀 Starting production server with Gunicorn..."
    # Use gunicorn for production with extended settings
    gunicorn \
        --bind ${HOST}:${PORT} \
        --workers ${WORKERS} \
        --threads ${THREADS} \
        --worker-class ${WORKER_CLASS} \
        --timeout ${REQUEST_TIMEOUT} \
        --log-level ${LOG_LEVEL} \
        --access-logfile - \
        --error-logfile - \
        --forwarded-allow-ips="*" \
        --access-logformat '%(h)s - %(u)s [%(t)s] "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" request_id=%(H)s' \
        "app:create_app()"
fi