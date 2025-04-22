#!/bin/bash
# Run validator and save results to a snapshot file

# Set directory to script's location
cd "$(dirname "$0")/.." || exit 1

# Create logs directory if it doesn't exist
mkdir -p logs

# Get today's date in YYYYMMDD format
DATE=$(date +%Y%m%d)

# Run nightly check
echo "Running nightly checks..."
make nightly-check

# Run validator and save results
echo "Running validator and saving results to snapshot..."
./corgi_validator.py --api-base=http://localhost:5001 --api-prefix=/api/v1 --verbose --output "logs/validator_snapshot_${DATE}.json"

# Print results
echo "Validator snapshot saved to logs/validator_snapshot_${DATE}.json"
echo "Results summary:"
jq '.summary' "logs/validator_snapshot_${DATE}.json" || echo "Unable to parse results file"