#!/usr/bin/env python3
"""
log_entry.py - Script to add standardized entries to DEV_LOG.md

USAGE EXAMPLES FOR LLMs:

1. Simple entry with title only:
   python3 log_entry.py "Feature Complete" --category feature

2. Entry with summary and single detail:
   python3 log_entry.py "Bug Fixed" --category bugfix --summary "Quick description" --detail "Fixed the main issue"

3. Multiple details using --detail flag (RECOMMENDED FOR LLMs):
   python3 log_entry.py "System Complete" --category feature \
     --summary "Brief overview" \
     --detail "First accomplishment" \
     --detail "Second accomplishment" \
     --components "Core Engine, API" \
     --files "file1.py, file2.py" \
     --next-steps "Next thing to do"

4. Traditional way (harder for LLMs due to shell parsing):
   python3 log_entry.py "Title" "Detail 1" "Detail 2" -c category

LLM TIPS:
- Use --detail flag multiple times instead of passing multiple positional arguments
- Use --summary for the summary line
- Use --components and --files for the affected section
- Always quote arguments that contain spaces or special characters
- Run from the project root directory
"""

import argparse
import datetime
import os
import re
import sys
import pytz

def find_dev_log_path():
    """Find the DEV_LOG.md file path."""
    # First, try current working directory
    current_path = os.path.join(os.getcwd(), "DEV_LOG.md")
    if os.path.exists(current_path):
        return current_path
    
    # If not found, try the script's directory (in case script is in subdirectory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, "DEV_LOG.md")
    if os.path.exists(script_path):
        return script_path
    
    # Try parent directory of script
    parent_path = os.path.join(os.path.dirname(script_dir), "DEV_LOG.md")
    if os.path.exists(parent_path):
        return parent_path
    
    # Not found anywhere
    return None

def find_last_entry_id(dev_log_path):
    """Find the highest entry ID in the log file."""
    try:
        with open(dev_log_path, 'r', encoding='utf-8') as log_file:
            content = log_file.read()
            matches = re.findall(r'^### Entry #(\d+)', content, re.MULTILINE)
            if matches:
                return max(map(int, matches))
            return 0
    except Exception as e:
        print(f"❌ Error reading DEV_LOG.md: {e}")
        return 0

def parse_details_new_format(details_list, summary=None, components=None, files=None):
    """Parse details using the new flag-based format."""
    formatted_details = []
    
    if details_list:
        for detail in details_list:
            # Handle sub-bullets (details starting with "  -")
            if detail.startswith("  -"):
                # This is a sub-bullet, indent it further
                formatted_details.append(f"  {detail}")
            else:
                # Regular detail
                formatted_details.append(detail)
    
    return summary, components, files, formatted_details

def parse_details_legacy(details):
    """Parse details to extract summary, components, files, and format sub-bullets (legacy format)."""
    summary = None
    components = None
    files = None
    formatted_details = []
    
    for detail in details:
        if detail.startswith("Summary:") and summary is None:
            summary = detail[8:].strip()  # Remove "Summary:" prefix
        elif detail.startswith("Components:"):
            components = detail[11:].strip()  # Remove "Components:" prefix
        elif detail.startswith("Files:"):
            files = detail[6:].strip()  # Remove "Files:" prefix
        else:
            # Handle sub-bullets (details starting with "  -")
            if detail.startswith("  -"):
                # This is a sub-bullet, indent it further
                formatted_details.append(f"  {detail}")
            else:
                # Regular detail
                formatted_details.append(detail)
    
    return summary, components, files, formatted_details

def create_entry(title, details, category=None, next_steps=None, summary=None, components=None, files=None, detail_flags=None):
    """Create a formatted entry string."""
    # Find DEV_LOG.md path
    dev_log_path = find_dev_log_path()
    if not dev_log_path:
        raise FileNotFoundError("Could not find DEV_LOG.md in current directory, script directory, or parent directory")
    
    # Set to Mountain Time (America/Denver) regardless of system timezone
    mountain_tz = pytz.timezone('America/Denver')
    now = datetime.datetime.now(mountain_tz)
    # Format with timezone abbreviation (MST or MDT depending on daylight saving)
    timestamp = now.strftime("%Y-%m-%d %H:%M %Z")
    
    # Find the last entry ID and increment
    last_id = find_last_entry_id(dev_log_path)
    next_id = last_id + 1
    
    # Use new format if flags were used, otherwise legacy format
    if detail_flags is not None:
        parsed_summary, parsed_components, parsed_files, formatted_details = parse_details_new_format(
            detail_flags, summary, components, files
        )
    else:
        parsed_summary, parsed_components, parsed_files, formatted_details = parse_details_legacy(details)
    
    # Start building the entry
    entry_lines = []
    
    # Format the entry title with optional category
    if category:
        entry_lines.append(f"\n### Entry #{next_id} {timestamp} [{category}] {title}\n")
    else:
        entry_lines.append(f"\n### Entry #{next_id} {timestamp} {title}\n")
    
    # Add summary if provided
    if parsed_summary:
        entry_lines.append(f"**Summary:** {parsed_summary}\n")
    
    # Add details if any
    if formatted_details:
        entry_lines.append("**Details:**")
        for detail in formatted_details:
            entry_lines.append(f"- {detail}")
    
    # Add affected section only if we have components or files
    if parsed_components or parsed_files:
        entry_lines.append("\n**Affected:**")
        if parsed_components:
            entry_lines.append(f"- Components: {parsed_components}")
        if parsed_files:
            entry_lines.append(f"- Files: {parsed_files}")
    
    # Add next steps if provided
    if next_steps:
        entry_lines.append(f"\n**Next Steps:**")
        entry_lines.append(f"- {next_steps}")
    
    # Join all lines with newlines
    entry = "\n".join(entry_lines) + "\n"
    
    return entry, dev_log_path, next_id, timestamp

def append_to_log(entry, dev_log_path):
    """Append the entry to the DEV_LOG.md file."""
    try:
        # Read existing content to verify it's a valid file
        with open(dev_log_path, 'r', encoding='utf-8') as log_file:
            existing_content = log_file.read()
        
        # Append the new entry
        with open(dev_log_path, 'a', encoding='utf-8') as log_file:
            log_file.write(entry)
        
        # Verify the entry was actually written
        with open(dev_log_path, 'r', encoding='utf-8') as log_file:
            new_content = log_file.read()
        
        if len(new_content) <= len(existing_content):
            raise Exception("Entry does not appear to have been written to file")
        
        return True
    except Exception as e:
        print(f"❌ Error writing to DEV_LOG.md: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Add an entry to DEV_LOG.md", 
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
USAGE EXAMPLES FOR LLMs:

1. Simple entry:
   python3 log_entry.py "Feature Complete" --category feature

2. Entry with summary and details (RECOMMENDED):
   python3 log_entry.py "System Complete" --category feature \\
     --summary "Brief overview" \\
     --detail "First accomplishment" \\
     --detail "Second accomplishment" \\
     --components "Core Engine, API" \\
     --files "file1.py, file2.py"

3. Legacy format (harder for LLMs):
   python3 log_entry.py "Title" "Detail 1" "Detail 2" -c category
        """
    )
    
    # Required arguments
    parser.add_argument("title", help="Title of the change")
    
    # Legacy format (positional details)
    parser.add_argument("details", nargs="*", help="Details of the change (legacy format)")
    
    # New LLM-friendly flags
    parser.add_argument("--detail", action="append", dest="detail_flags", 
                       help="Add a detail line (can be used multiple times)")
    parser.add_argument("--summary", help="Summary line for the entry")
    parser.add_argument("--components", help="Components affected (comma-separated)")
    parser.add_argument("--files", help="Files affected (comma-separated)")
    
    # Common flags
    parser.add_argument("-c", "--category", help="Category tag (e.g., testing, performance, bugfix, feature, refactor, docs)")
    parser.add_argument("-n", "--next-steps", help="Optional next steps or follow-up actions")
    
    args = parser.parse_args()
    
    # Validate that we have some content
    if not args.details and not args.detail_flags and not args.summary:
        print("⚠️  Warning: Creating entry with title only. Consider adding --summary or --detail for more information.")
    
    try:
        # Create and append the entry
        entry, dev_log_path, next_id, timestamp = create_entry(
            args.title, 
            args.details or [],
            args.category,
            args.next_steps,
            args.summary,
            args.components,
            args.files,
            args.detail_flags
        )
        
        print(f"📝 Creating entry in: {dev_log_path}")
        
        if append_to_log(entry, dev_log_path):
            print(f"✅ Entry #{next_id} has been successfully added to DEV_LOG.md")
            print(f"📅 Timestamp: {timestamp}")
            if args.category:
                print(f"🏷️  Category: {args.category}")
            print(f"📝 Title: {args.title}")
            if args.summary:
                print(f"📋 Summary: {args.summary}")
            if args.detail_flags:
                print(f"📄 Details: {len(args.detail_flags)} items added")
        else:
            print("❌ Failed to add entry to DEV_LOG.md")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()