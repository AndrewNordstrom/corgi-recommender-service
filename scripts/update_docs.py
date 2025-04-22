#!/usr/bin/env python3
"""
Documentation Maintenance Tool for Corgi Recommender Service.

This tool scans the codebase for missing documentation and incomplete MkDocs references,
making it easier to keep documentation synchronized with code changes.

It performs the following checks:
1. Finds routes with no corresponding markdown documentation
2. Identifies functions missing Google-style docstrings
3. Warns if mkdocs.yml navigation is missing links to existing documentation files
4. Optionally regenerates API reference documentation using mkdocstrings

Example usage:
    python scripts/update_docs.py --check-routes --check-docstrings
    python scripts/update_docs.py --check-mkdocs --generate-api-docs
"""

import os
import re
import sys
import argparse
import glob
import yaml
import logging
from collections import defaultdict
from typing import List, Dict, Set, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger('update_docs')

# Define paths
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROUTES_DIR = os.path.join(ROOT_DIR, 'routes')
DOCS_DIR = os.path.join(ROOT_DIR, 'docs')
MKDOCS_YML = os.path.join(ROOT_DIR, 'mkdocs.yml')


def find_routes() -> List[Dict]:
    """
    Find all Flask route definitions in the codebase.
    
    Returns:
        List[Dict]: List of route information dictionaries with keys:
            - file: Source file path
            - route: Route path
            - methods: HTTP methods
            - function: Function name
            - line: Line number
    """
    routes = []
    route_pattern = re.compile(r'@\w+_bp\.route\([\'"]([^\'"]+)[\'"](?:,\s*methods=(\[[^\]]+\]))?\)')
    function_pattern = re.compile(r'def\s+(\w+)\s*\(')
    
    for root, _, files in os.walk(ROUTES_DIR):
        for filename in files:
            if filename.endswith('.py'):
                file_path = os.path.join(root, filename)
                with open(file_path, 'r') as f:
                    content = f.readlines()
                
                for i, line in enumerate(content):
                    route_match = route_pattern.search(line)
                    if route_match:
                        route = route_match.group(1)
                        methods = route_match.group(2) or "['GET']"
                        
                        # Find the function name (should be in the next few lines)
                        function_name = None
                        for j in range(i, min(i + 5, len(content))):
                            fn_match = function_pattern.search(content[j])
                            if fn_match:
                                function_name = fn_match.group(1)
                                break
                        
                        if function_name:
                            routes.append({
                                'file': os.path.relpath(file_path, ROOT_DIR),
                                'route': route,
                                'methods': methods,
                                'function': function_name,
                                'line': i + 1
                            })
    
    return routes


def find_documented_routes() -> Set[str]:
    """
    Find routes that are already documented in markdown files.
    
    Returns:
        Set[str]: Set of documented route paths
    """
    documented_routes = set()
    route_pattern = re.compile(r'`(?:GET|POST|PUT|DELETE|PATCH)\s+([^`]+)`')
    
    # Look in endpoints directory specifically
    endpoints_dir = os.path.join(DOCS_DIR, 'endpoints')
    if os.path.exists(endpoints_dir):
        for md_file in glob.glob(os.path.join(endpoints_dir, '**/*.md'), recursive=True):
            with open(md_file, 'r') as f:
                content = f.read()
            
            for match in route_pattern.finditer(content):
                route = match.group(1)
                if route.startswith('/api/v1/'):
                    # Normalize by removing API prefix
                    route = route.replace('/api/v1/', '/')
                documented_routes.add(route)
    
    return documented_routes


def find_undocumented_routes(routes: List[Dict], documented_routes: Set[str]) -> List[Dict]:
    """
    Find routes that lack documentation.
    
    Args:
        routes: List of route information dictionaries
        documented_routes: Set of documented route paths
    
    Returns:
        List[Dict]: List of undocumented route information
    """
    undocumented = []
    
    for route in routes:
        route_path = route['route']
        # Skip internal/utility routes
        if route_path.startswith('/health') or route_path.startswith('/debug'):
            continue
            
        if route_path not in documented_routes:
            undocumented.append(route)
    
    return undocumented


def find_missing_docstrings() -> List[Dict]:
    """
    Find functions missing Google-style docstrings.
    
    Returns:
        List[Dict]: List of functions with missing/incomplete docstrings
    """
    missing_docstrings = []
    function_pattern = re.compile(r'def\s+(\w+)\s*\(([^)]*)\)')
    
    for root, _, files in os.walk(ROOT_DIR):
        # Skip certain directories
        if 'venv' in root or '.git' in root or 'site' in root:
            continue
            
        for filename in files:
            if filename.endswith('.py'):
                file_path = os.path.join(root, filename)
                with open(file_path, 'r') as f:
                    content = f.readlines()
                
                for i, line in enumerate(content):
                    fn_match = function_pattern.search(line)
                    if fn_match and not line.strip().startswith('#'):
                        function_name = fn_match.group(1)
                        # Skip magic methods, private helpers, and Flask app setup
                        if (function_name.startswith('__') or 
                            function_name.startswith('_') or
                            function_name == 'create_app'):
                            continue
                        
                        # Check for docstring
                        has_docstring = False
                        has_args_section = False
                        has_returns_section = False
                        
                        # Look at next 10 lines for docstring
                        for j in range(i + 1, min(i + 10, len(content))):
                            if '"""' in content[j] or "'''" in content[j]:
                                has_docstring = True
                                # Check for Google-style sections
                                for k in range(j, min(j + 20, len(content))):
                                    if 'Args:' in content[k]:
                                        has_args_section = True
                                    if 'Returns:' in content[k]:
                                        has_returns_section = True
                                    # End of docstring
                                    if ('"""' in content[k] or "'''" in content[k]) and k > j:
                                        break
                                break
                        
                        if not has_docstring or not (has_args_section and has_returns_section):
                            # Extract arguments
                            args = fn_match.group(2).strip()
                            if args and args != 'self':  # Only consider functions with args
                                missing_docstrings.append({
                                    'file': os.path.relpath(file_path, ROOT_DIR),
                                    'function': function_name,
                                    'missing': 'docstring' if not has_docstring else 'sections',
                                    'line': i + 1
                                })
    
    return missing_docstrings


def check_mkdocs_nav() -> Tuple[List[str], List[str]]:
    """
    Check for inconsistencies between mkdocs.yml navigation and actual markdown files.
    
    Returns:
        Tuple[List[str], List[str]]: 
            - List of markdown files not referenced in mkdocs.yml
            - List of broken references in mkdocs.yml
    """
    # Load mkdocs.yml
    try:
        with open(MKDOCS_YML, 'r') as f:
            mkdocs_config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to parse mkdocs.yml: {e}")
        return [], []
    
    # Extract all referenced markdown files
    referenced_files = set()
    
    def extract_references(nav_item):
        if isinstance(nav_item, dict):
            for _, value in nav_item.items():
                if isinstance(value, str) and value.endswith('.md'):
                    referenced_files.add(value)
                elif isinstance(value, list):
                    for item in value:
                        extract_references(item)
        elif isinstance(nav_item, list):
            for item in nav_item:
                extract_references(item)
    
    if 'nav' in mkdocs_config:
        extract_references(mkdocs_config['nav'])
    
    # Find all markdown files in docs directory
    actual_files = set()
    for root, _, files in os.walk(DOCS_DIR):
        for filename in files:
            if filename.endswith('.md'):
                rel_path = os.path.relpath(os.path.join(root, filename), DOCS_DIR)
                actual_files.add(rel_path)
    
    # Convert referenced paths to be relative to docs directory
    referenced_normalized = set()
    for ref in referenced_files:
        referenced_normalized.add(ref)
    
    # Find files not referenced in mkdocs.yml
    unreferenced = [file for file in actual_files if file not in referenced_normalized]
    
    # Find broken references in mkdocs.yml
    broken_refs = [ref for ref in referenced_normalized if not os.path.exists(os.path.join(DOCS_DIR, ref))]
    
    return unreferenced, broken_refs


def generate_api_docs():
    """
    Generate API reference documentation using mkdocstrings if available.
    
    This is a placeholder for future functionality. The actual implementation would:
    1. Check if mkdocstrings is configured in mkdocs.yml
    2. Generate/update API reference pages based on docstrings
    """
    logger.info("API documentation generation not yet implemented")
    logger.info("This would generate API reference documentation using mkdocstrings")
    logger.info("To add this functionality, you would need to:")
    logger.info("1. Install mkdocstrings with: pip install mkdocstrings-python")
    logger.info("2. Add mkdocstrings plugin to mkdocs.yml")
    logger.info("3. Implement document generation logic in this function")


def main():
    """Run the documentation maintenance tool."""
    parser = argparse.ArgumentParser(description='Documentation maintenance tool')
    parser.add_argument('--check-routes', action='store_true', help='Check for undocumented routes')
    parser.add_argument('--check-docstrings', action='store_true', help='Check for missing docstrings')
    parser.add_argument('--check-mkdocs', action='store_true', help='Check mkdocs.yml navigation')
    parser.add_argument('--generate-api-docs', action='store_true', help='Generate API reference documentation')
    parser.add_argument('--all', action='store_true', help='Run all checks')
    
    args = parser.parse_args()
    
    # If no specific arguments provided, use --all as default
    if not (args.check_routes or args.check_docstrings or 
            args.check_mkdocs or args.generate_api_docs):
        args.all = True
    
    if args.check_routes or args.all:
        logger.info("Checking for undocumented routes...")
        routes = find_routes()
        documented = find_documented_routes()
        undocumented = find_undocumented_routes(routes, documented)
        
        if undocumented:
            logger.warning(f"Found {len(undocumented)} undocumented routes:")
            for route in undocumented:
                logger.warning(f"  {route['file']}:{route['line']} - {route['function']} ({route['route']})")
        else:
            logger.info("All routes are documented!")
    
    if args.check_docstrings or args.all:
        logger.info("Checking for missing Google-style docstrings...")
        missing = find_missing_docstrings()
        
        if missing:
            logger.warning(f"Found {len(missing)} functions with missing/incomplete docstrings:")
            for func in missing:
                missing_type = "is missing docstring" if func['missing'] == 'docstring' else "has incomplete docstring (missing Args/Returns sections)"
                logger.warning(f"  {func['file']}:{func['line']} - {func['function']} {missing_type}")
        else:
            logger.info("All functions have proper Google-style docstrings!")
    
    if args.check_mkdocs or args.all:
        logger.info("Checking mkdocs.yml navigation...")
        unreferenced, broken = check_mkdocs_nav()
        
        if unreferenced:
            logger.warning(f"Found {len(unreferenced)} markdown files not referenced in mkdocs.yml:")
            for file in unreferenced:
                logger.warning(f"  {file}")
        else:
            logger.info("All markdown files are referenced in mkdocs.yml!")
        
        if broken:
            logger.warning(f"Found {len(broken)} broken references in mkdocs.yml:")
            for ref in broken:
                logger.warning(f"  {ref}")
        else:
            logger.info("No broken references in mkdocs.yml!")
    
    if args.generate_api_docs or args.all:
        logger.info("Generating API reference documentation...")
        generate_api_docs()


if __name__ == "__main__":
    main()