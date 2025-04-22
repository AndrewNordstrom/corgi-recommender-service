#!/usr/bin/env python3
"""
Script to find JavaScript-style booleans in Python code
"""

import re

def find_js_booleans(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    for line_num, line in enumerate(lines, 1):
        # Skip comments and strings with JSON examples
        if line.strip().startswith('#') or 'example' in line.lower():
            continue
        
        # Check for 'true' or 'false' as standalone tokens
        if re.search(r'(?<![a-zA-Z0-9_])(true|false)(?![a-zA-Z0-9_])', line):
            print(f"Line {line_num}: {line.strip()}")

if __name__ == "__main__":
    find_js_booleans('/Users/andrewnordstrom/corgi-recommender-service/special_proxy.py')