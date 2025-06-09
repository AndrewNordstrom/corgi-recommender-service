import os
import re

# Count tests by category
categories = {}
test_files = []

for f in os.listdir('tests/'):
    if f.startswith('test_') and f.endswith('.py'):
        with open(f'tests/{f}', 'r') as file:
            content = file.read()
            test_count = len(re.findall(r'def test_', content))
            
            # Categorize
            if 'performance' in f:
                category = 'performance'
            elif any(x in f for x in ['auth', 'oauth', 'token']):
                category = 'auth'
            elif any(x in f for x in ['cache', 'caching']):
                category = 'cache'
            elif 'proxy' in f:
                category = 'proxy'
            elif 'phase' in f:
                category = 'phase_testing'
            elif any(x in f for x in ['integration', 'e2e']):
                category = 'integration'
            elif any(x in f for x in ['api', 'endpoints']):
                category = 'api'
            else:
                category = 'other'
            
            if category not in categories:
                categories[category] = []
            categories[category].append((f, test_count))
            test_files.append((f, test_count, category))

print('=== TEST ANALYSIS REPORT ===')
print()
print('Total test files:', len(test_files))
print('Total tests:', sum(count for _, count, _ in test_files))
print()

for category, files in categories.items():
    total_tests = sum(count for _, count in files)
    print(f'{category.upper()}: {len(files)} files, {total_tests} tests')
    for file, count in sorted(files, key=lambda x: x[1], reverse=True)[:5]:
        print(f'  - {file}: {count} tests')
    print()

# Identify potential pruning targets
print('=== PRUNING TARGETS ===')
print()

# Files with too many tests (over-testing)
print('OVER-TESTING (>20 tests per file):')
for file, count, category in sorted(test_files, key=lambda x: x[1], reverse=True):
    if count > 20:
        print(f'  - {file}: {count} tests ({category})')
print()

# Phase testing files (likely temporary)
print('PHASE TESTING FILES (likely removable):')
for file, count, category in test_files:
    if category == 'phase_testing':
        print(f'  - {file}: {count} tests')
print()

# Small test files (potential consolidation targets)
print('SMALL FILES (<5 tests, consolidation candidates):')
for file, count, category in sorted(test_files, key=lambda x: x[1]):
    if count < 5 and count > 0:
        print(f'  - {file}: {count} tests ({category})')
print() 