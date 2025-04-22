#!/usr/bin/env python3
"""
Documentation Validation Script for Corgi Recommender Service

This script verifies that all required documentation files exist and are properly
formatted, and checks that the mkdocs.yml configuration is valid.
"""

import os
import sys
import yaml
import subprocess
import argparse
from pathlib import Path
from termcolor import colored

# Define paths relative to the project root
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_ROOT = PROJECT_ROOT / "docs"
MKDOCS_CONFIG = PROJECT_ROOT / "mkdocs.yml"

# Required documentation files
REQUIRED_DOCS = [
    "index.md",
    "endpoints/interactions.md",
    "proxy.md",
    "agent_guide.md",
]

def check_file_exists(file_path, is_required=True):
    """Check if a file exists and print the result."""
    path = DOCS_ROOT / file_path
    exists = path.exists()
    
    if exists:
        print(colored(f"✅ Found: {file_path}", "green"))
    elif is_required:
        print(colored(f"❌ Missing: {file_path}", "red"))
    else:
        print(colored(f"⚠️ Optional file not found: {file_path}", "yellow"))
    
    return exists

def validate_mkdocs_config():
    """Validate the mkdocs.yml configuration file."""
    if not MKDOCS_CONFIG.exists():
        print(colored("❌ mkdocs.yml not found", "red"))
        return False
    
    try:
        with open(MKDOCS_CONFIG, 'r') as file:
            config = yaml.safe_load(file)
        
        # Check for required keys
        required_keys = ['site_name', 'nav']
        missing_keys = [key for key in required_keys if key not in config]
        
        if missing_keys:
            print(colored(f"❌ mkdocs.yml is missing required keys: {', '.join(missing_keys)}", "red"))
            return False
        
        # Check that nav is properly structured
        if not isinstance(config.get('nav', []), list):
            print(colored("❌ mkdocs.yml 'nav' section is not a valid list", "red"))
            return False
        
        print(colored("✅ mkdocs.yml is valid", "green"))
        return True
    
    except yaml.YAMLError as e:
        print(colored(f"❌ Error parsing mkdocs.yml: {e}", "red"))
        return False
    except Exception as e:
        print(colored(f"❌ Error validating mkdocs.yml: {e}", "red"))
        return False

def check_mkdocs_command():
    """Check if mkdocs is installed and available."""
    try:
        subprocess.run(["mkdocs", "--version"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def main():
    """Main function to validate documentation."""
    parser = argparse.ArgumentParser(description="Validate Corgi Recommender Service documentation")
    parser.add_argument("--check-only", action="store_true", help="Only check files, don't suggest actions")
    args = parser.parse_args()
    
    print(colored("\n=== Corgi Recommender Documentation Validation ===", "cyan", attrs=["bold"]))
    
    # Check if docs directory exists
    if not DOCS_ROOT.exists():
        print(colored(f"❌ Documentation directory not found at {DOCS_ROOT}", "red"))
        return False
    
    print(colored("\nChecking required documentation files:", "cyan"))
    all_docs_exist = True
    for doc in REQUIRED_DOCS:
        if not check_file_exists(doc):
            all_docs_exist = False
    
    print(colored("\nChecking optional documentation files:", "cyan"))
    # Add any additional optional docs to check here
    check_file_exists("getting-started.md", is_required=False)
    check_file_exists("architecture.md", is_required=False)
    
    print(colored("\nValidating mkdocs configuration:", "cyan"))
    mkdocs_valid = validate_mkdocs_config()
    
    # Overall status
    print(colored("\n=== Validation Summary ===", "cyan", attrs=["bold"]))
    overall_status = all_docs_exist and mkdocs_valid
    
    if overall_status:
        print(colored("✅ All required documentation is available and valid", "green"))
        
        if not args.check_only:
            # Check if mkdocs is installed
            if check_mkdocs_command():
                print(colored("\nSuggestion: Run the following to serve the documentation locally:", "cyan"))
                print(colored("    cd " + str(PROJECT_ROOT) + " && mkdocs serve", "yellow"))
            else:
                print(colored("\nSuggestion: Install mkdocs to serve the documentation locally:", "cyan"))
                print(colored("    pip install mkdocs mkdocs-material", "yellow"))
                print(colored("    cd " + str(PROJECT_ROOT) + " && mkdocs serve", "yellow"))
    else:
        print(colored("❌ Some documentation files or configurations are missing or invalid", "red"))
        
        if not all_docs_exist:
            print(colored("\nMissing documentation files need to be created:", "cyan"))
            for doc in REQUIRED_DOCS:
                path = DOCS_ROOT / doc
                if not path.exists():
                    print(colored(f"    - Create {path}", "yellow"))
        
        if not mkdocs_valid and not args.check_only:
            print(colored("\nFix the mkdocs.yml configuration file to enable documentation serving", "cyan"))
    
    return overall_status

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)