#!/bin/bash
# Setup script for Corgi Recommender Service database
set -e

echo "🐶 Corgi Recommender Service - Database Setup"
echo "=============================================="

# Parse command line options
RESET=false
CREATE_DB=true
DRY_RUN=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --reset) RESET=true ;;
        --no-create) CREATE_DB=false ;;
        --dry-run) DRY_RUN=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Check if PostgreSQL is running (skip in dry-run mode)
if [ "$DRY_RUN" = false ]; then
    echo "Checking PostgreSQL status..."
    if pg_isready &>/dev/null; then
        echo "✅ PostgreSQL is running"
    else
        echo "❌ PostgreSQL is not running. Please start PostgreSQL first."
        echo "To see the SQL without connecting to PostgreSQL, use --dry-run"
        exit 1
    fi
else
    echo "🔍 Dry run mode - skipping PostgreSQL check"
fi

# Run database setup
CMD="python3 -m db.setup"

if [ "$CREATE_DB" = true ]; then
    CMD="$CMD --create-db"
fi

if [ "$RESET" = true ]; then
    if [ "$DRY_RUN" = false ]; then
        echo "⚠️  WARNING: You are about to RESET the database. All data will be lost!"
        read -p "Are you sure you want to continue? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Operation canceled."
            exit 0
        fi
    fi
    
    CMD="$CMD --reset"
fi

if [ "$DRY_RUN" = true ]; then
    echo "🔍 Dry run mode: Will show SQL without executing it"
    CMD="$CMD --dry-run"
fi

echo "Running: $CMD"
$CMD

echo
echo "🎉 Setup complete! You can now run the Corgi Recommender Service."