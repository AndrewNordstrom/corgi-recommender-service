#!/bin/bash
# log_entry.sh - Script to add standardized entries to DEV_LOG.md
# Usage: ./scripts/log_entry.sh "Change Description" "Details..." [-c category] [-n "next steps"]
# Examples:
#   ./scripts/log_entry.sh "Fixed bug" "Details here"
#   ./scripts/log_entry.sh "Performance Fix" "Summary: 6x speedup" "Details..." -c performance -n "Monitor metrics"

set -e

# Function to display usage
usage() {
    echo "Usage: $0 \"Title\" [\"Detail 1\"] [\"Detail 2\"] ... [-c category] [-n \"next steps\"]"
    echo ""
    echo "Options:"
    echo "  -c CATEGORY    Add category tag (e.g., testing, performance, bugfix, feature, refactor, docs)"
    echo "  -n NEXT_STEPS  Add next steps section"
    echo "  -h             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 \"Fixed bug\" \"Details here\""
    echo "  $0 \"Performance Fix\" \"Summary: 6x speedup\" \"Details...\" -c performance -n \"Monitor metrics\""
    exit 1
}

# Set variables
DEV_LOG_PATH="$(pwd)/DEV_LOG.md"
# Force America/Denver timezone for consistent Mountain time entries
export TZ="America/Denver"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M %Z")

# Initialize variables
TITLE=""
DETAILS=()
CATEGORY=""
NEXT_STEPS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--category)
            CATEGORY="$2"
            shift 2
            ;;
        -n|--next-steps)
            NEXT_STEPS="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        -*)
            echo "Unknown option: $1"
            usage
            ;;
        *)
            if [[ -z "$TITLE" ]]; then
                TITLE="$1"
            else
                DETAILS+=("$1")
            fi
            shift
            ;;
    esac
done

# Check if title is provided
if [[ -z "$TITLE" ]]; then
    echo "Error: Title is required"
    usage
fi

# Find the last entry ID
LAST_ID=$(grep -E "^### Entry #[0-9]+" "$DEV_LOG_PATH" | sed -E 's/^### Entry #([0-9]+).*/\1/' | sort -n | tail -n 1 || echo 0)
NEXT_ID=$((LAST_ID + 1))

# Parse details to extract summary, components, files
SUMMARY=""
COMPONENTS=""
FILES=""
FORMATTED_DETAILS=()

for detail in "${DETAILS[@]}"; do
    if [[ "$detail" == "Summary:"* ]] && [[ -z "$SUMMARY" ]]; then
        SUMMARY="${detail#Summary: }"
    elif [[ "$detail" == "Components:"* ]]; then
        COMPONENTS="$detail"
    elif [[ "$detail" == "Files:"* ]]; then
        FILES="$detail"
    else
        # Handle sub-bullets (details starting with "  -")
        if [[ "$detail" == "  -"* ]]; then
            FORMATTED_DETAILS+=("  $detail")
        else
            FORMATTED_DETAILS+=("$detail")
        fi
    fi
done

# Start building the entry content
if [[ -n "$CATEGORY" ]]; then
    ENTRY="### Entry #${NEXT_ID} ${TIMESTAMP} [${CATEGORY}] ${TITLE}"
else
    ENTRY="### Entry #${NEXT_ID} ${TIMESTAMP} ${TITLE}"
fi

# Add summary if provided
if [[ -n "$SUMMARY" ]]; then
    ENTRY+=$'\n\n'"**Summary:** ${SUMMARY}"
fi

# Add details if any
if [[ ${#FORMATTED_DETAILS[@]} -gt 0 ]]; then
    ENTRY+=$'\n\n'"**Details:**"
    for detail in "${FORMATTED_DETAILS[@]}"; do
        ENTRY+=$'\n'"- ${detail}"
    done
fi

# Add Affected section only if we have components or files
if [[ -n "$COMPONENTS" ]] || [[ -n "$FILES" ]]; then
    ENTRY+=$'\n\n'"**Affected:**"
    
    if [[ -n "$COMPONENTS" ]]; then
        ENTRY+=$'\n'"- ${COMPONENTS}"
    fi
    
    if [[ -n "$FILES" ]]; then
        ENTRY+=$'\n'"- ${FILES}"
    fi
fi

# Add next steps if provided
if [[ -n "$NEXT_STEPS" ]]; then
    ENTRY+=$'\n\n'"**Next Steps:**"$'\n'"- ${NEXT_STEPS}"
fi

# Append the entry to DEV_LOG.md
echo -e "\n${ENTRY}" >> "$DEV_LOG_PATH"

echo "Entry #${NEXT_ID} has been added to DEV_LOG.md"
echo "Timestamp: ${TIMESTAMP}"
if [[ -n "$CATEGORY" ]]; then
    echo "Category: ${CATEGORY}"
fi
echo "Title: ${TITLE}"