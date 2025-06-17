"""
Tester Agent

Automated test generation and maintenance agent that ensures comprehensive test coverage
and maintains the "100% Green Test Suite" by accelerating test creation and maintenance.

This agent:
- Analyzes new/modified code to generate appropriate tests
- Creates boilerplate unit and integration tests
- Learns from existing test patterns for consistency
- Generates regression tests for bug fixes
- Reports test coverage and quality metrics to Manager Agent
"""

import ast
import inspect
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
import logging

from agents.base_agent import BaseAgent, AgentResult
from agents.claude_interface import ClaudeInterface
from agents.slack_notifier import SlackNotifier

logger = logging.getLogger(__name__)

class TesterAgent(BaseAgent):
    """
    Automated test generation and maintenance agent.
    
    Analyzes code changes and automatically generates comprehensive test suites
    to maintain high test coverage and prevent regressions.
    """
    
    def __init__(self):
        super().__init__(
            agent_id="tester",
            name="Tester Agent",
            description="Automated test generation and test suite maintenance"
        )
        
        self.claude = ClaudeInterface()
        
        # Initialize Slack notifier if webhook URL is available
        slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        if slack_webhook:
            # Disable SSL verification for macOS certificate issues
            self.slack = SlackNotifier(webhook_url=slack_webhook, verify_ssl=False)
        else:
            self.slack = None
            logger.warning("SLACK_WEBHOOK_URL not configured, Slack notifications disabled")
        
        # Test generation configuration
        self.test_config = {
            'test_dir': 'tests',
            'output_dir': 'logs/test_generation',
            'coverage_threshold': 80.0,
            'supported_extensions': ['.py'],
            'test_patterns': {
                'unit_test': 'test_{function_name}',
                'integration_test': 'test_{module_name}_integration',
                'regression_test': 'test_regression_{issue_id}'
            }
        }
        
        # Code analysis patterns
        self.analysis_patterns = {
            'api_endpoints': r'@\w+\.route\([\'"]([^\'"]+)[\'"]',
            'functions': r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
            'classes': r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[\(:]',
            'imports': r'(?:from\s+[\w.]+\s+)?import\s+([\w.,\s]+)',
            'database_queries': r'(?:cursor\.execute|conn\.execute)\s*\([\'"]([^\'"]+)[\'"]'
        }
        
        # Test template patterns learned from existing tests
        self.test_templates = {}
        
        # Ensure output directory exists
        os.makedirs(self.test_config['output_dir'], exist_ok=True)
        
        # Learn from existing test patterns on initialization
        self._learn_test_patterns()
        
    async def execute(self) -> AgentResult:
        """Execute tester agent analysis and test generation."""
        try:
            logger.info("🧪 Starting Tester Agent execution")
            
            # Analyze recent code changes
            code_changes = await self._analyze_recent_code_changes()
            
            # Generate tests for new/modified code
            test_generation_results = await self._generate_tests_for_changes(code_changes)
            
            # Run test coverage analysis
            coverage_analysis = await self._analyze_test_coverage()
            
            # Identify missing test scenarios
            missing_tests = await self._identify_missing_tests()
            
            # Check test suite health
            test_health = await self._check_test_suite_health()
            
            # Compile comprehensive report
            report = await self._compile_test_report({
                'code_changes': code_changes,
                'test_generation': test_generation_results,
                'coverage_analysis': coverage_analysis,
                'missing_tests': missing_tests,
                'test_health': test_health
            })
            
            # Send notifications
            await self._send_notifications(report)
            
            return AgentResult(
                success=True,
                message="Test analysis and generation completed",
                data={
                    'report': report,
                    'tests_generated': len(test_generation_results.get('generated_tests', [])),
                    'coverage_percentage': coverage_analysis.get('coverage_percentage', 0),
                    'missing_test_count': len(missing_tests.get('missing_scenarios', []))
                }
            )
            
        except Exception as e:
            logger.error(f"Tester Agent execution failed: {e}")
            
            # Send error notification
            if self.slack:
                await self.slack.send_message(
                    f"🚨 Tester Agent Error: {str(e)}",
                    channel="#corgi-alerts"
                )
            
            return AgentResult(
                success=False,
                message=f"Test analysis failed: {str(e)}",
                data={'error': str(e)}
            )
    
    def _learn_test_patterns(self):
        """Learn test patterns from existing test suite."""
        try:
            test_dir = Path(self.test_config['test_dir'])
            if not test_dir.exists():
                logger.warning(f"Test directory {test_dir} not found")
                return
            
            # Analyze existing test files
            test_files = list(test_dir.rglob('test_*.py'))
            
            patterns = {
                'imports': set(),
                'fixtures': set(),
                'assertion_patterns': set(),
                'mock_patterns': set(),
                'setup_patterns': set()
            }
            
            for test_file in test_files[:20]:  # Limit analysis to avoid performance issues
                try:
                    with open(test_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract common patterns
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                patterns['imports'].add(alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                patterns['imports'].add(f"from {node.module} import ...")
                        elif isinstance(node, ast.FunctionDef):
                            if node.name.startswith('test_'):
                                # Analyze test function structure
                                if any(decorator.id == 'pytest.fixture' for decorator in node.decorator_list 
                                      if isinstance(decorator, ast.Name)):
                                    patterns['fixtures'].add(node.name)
                    
                    # Extract assertion patterns using regex
                    assertions = re.findall(r'assert\s+([^#\n]+)', content)
                    patterns['assertion_patterns'].update(assertions[:10])  # Limit to avoid memory issues
                    
                    # Extract mock patterns
                    mock_patterns = re.findall(r'@patch\([\'"]([^\'"]+)[\'"]', content)
                    patterns['mock_patterns'].update(mock_patterns)
                    
                except Exception as e:
                    logger.warning(f"Failed to analyze test file {test_file}: {e}")
                    continue
            
            self.test_templates = patterns
            logger.info(f"Learned patterns from {len(test_files)} test files")
            
        except Exception as e:
            logger.error(f"Failed to learn test patterns: {e}")
    
    async def _analyze_recent_code_changes(self) -> Dict[str, Any]:
        """Analyze recent code changes to identify what needs testing."""
        try:
            # Get recent git changes (last 24 hours)
            result = subprocess.run([
                'git', 'log', '--since=24 hours ago', '--name-only', '--pretty=format:'
            ], capture_output=True, text=True, cwd='.')
            
            if result.returncode != 0:
                return {'error': 'Failed to get git changes'}
            
            # Parse changed files
            changed_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            python_files = [f for f in changed_files if f.endswith('.py') and not f.startswith('tests/')]
            
            # Analyze each changed file
            file_analyses = []
            
            for file_path in python_files[:10]:  # Limit to avoid performance issues
                if os.path.exists(file_path):
                    analysis = await self._analyze_python_file(file_path)
                    if analysis:
                        file_analyses.append(analysis)
            
            return {
                'total_changed_files': len(changed_files),
                'python_files_changed': len(python_files),
                'analyzed_files': file_analyses,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Code change analysis failed: {e}")
            return {'error': str(e)}
    
    async def _analyze_python_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Analyze a Python file to understand its structure and testing needs."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            analysis = {
                'file_path': file_path,
                'functions': [],
                'classes': [],
                'api_endpoints': [],
                'imports': [],
                'complexity_indicators': {
                    'total_lines': len(content.split('\n')),
                    'function_count': 0,
                    'class_count': 0,
                    'complexity_score': 0
                }
            }
            
            # Walk the AST
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        'name': node.name,
                        'line_number': node.lineno,
                        'args': [arg.arg for arg in node.args.args],
                        'is_async': isinstance(node, ast.AsyncFunctionDef),
                        'has_decorators': len(node.decorator_list) > 0,
                        'docstring': ast.get_docstring(node)
                    }
                    analysis['functions'].append(func_info)
                    analysis['complexity_indicators']['function_count'] += 1
                    
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        'name': node.name,
                        'line_number': node.lineno,
                        'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                        'bases': [base.id for base in node.bases if isinstance(base, ast.Name)],
                        'docstring': ast.get_docstring(node)
                    }
                    analysis['classes'].append(class_info)
                    analysis['complexity_indicators']['class_count'] += 1
                    
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis['imports'].append(alias.name)
                        
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        analysis['imports'].append(f"from {node.module}")
            
            # Look for Flask/FastAPI routes
            route_patterns = re.findall(self.analysis_patterns['api_endpoints'], content)
            analysis['api_endpoints'] = route_patterns
            
            # Calculate complexity score
            analysis['complexity_indicators']['complexity_score'] = (
                analysis['complexity_indicators']['function_count'] * 2 +
                analysis['complexity_indicators']['class_count'] * 5 +
                len(analysis['api_endpoints']) * 3
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze file {file_path}: {e}")
            return None
    
    async def _generate_tests_for_changes(self, code_changes: Dict[str, Any]) -> Dict[str, Any]:
        """Generate tests for analyzed code changes."""
        try:
            generated_tests = []
            
            if 'analyzed_files' not in code_changes:
                return {'generated_tests': [], 'message': 'No analyzed files to process'}
            
            for file_analysis in code_changes['analyzed_files']:
                # Generate tests for each component
                file_tests = await self._generate_tests_for_file(file_analysis)
                generated_tests.extend(file_tests)
            
            # Save generated tests
            for test_info in generated_tests:
                await self._save_generated_test(test_info)
            
            return {
                'generated_tests': generated_tests,
                'total_tests_created': len(generated_tests),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            return {'error': str(e)}
    
    async def _generate_tests_for_file(self, file_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate tests for a specific file analysis."""
        tests = []
        
        try:
            file_path = file_analysis['file_path']
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Generate tests for functions
            for func in file_analysis['functions']:
                if not func['name'].startswith('_'):  # Skip private functions
                    test_code = await self._generate_function_test(func, file_analysis)
                    if test_code:
                        tests.append({
                            'type': 'unit_test',
                            'target': f"{file_path}::{func['name']}",
                            'test_name': f"test_{func['name']}",
                            'test_code': test_code,
                            'file_path': f"tests/test_{module_name}.py"
                        })
            
            # Generate tests for classes
            for cls in file_analysis['classes']:
                test_code = await self._generate_class_test(cls, file_analysis)
                if test_code:
                    tests.append({
                        'type': 'class_test',
                        'target': f"{file_path}::{cls['name']}",
                        'test_name': f"test_{cls['name'].lower()}",
                        'test_code': test_code,
                        'file_path': f"tests/test_{module_name}.py"
                    })
            
            # Generate tests for API endpoints
            for endpoint in file_analysis['api_endpoints']:
                test_code = await self._generate_api_test(endpoint, file_analysis)
                if test_code:
                    tests.append({
                        'type': 'api_test',
                        'target': f"{file_path}::{endpoint}",
                        'test_name': f"test_api_{endpoint.replace('/', '_').replace('<', '').replace('>', '')}",
                        'test_code': test_code,
                        'file_path': f"tests/test_{module_name}_api.py"
                    })
            
            return tests
            
        except Exception as e:
            logger.error(f"Failed to generate tests for file {file_analysis.get('file_path', 'unknown')}: {e}")
            return []
    
    async def _generate_function_test(self, func_info: Dict[str, Any], file_analysis: Dict[str, Any]) -> Optional[str]:
        """Generate a unit test for a function using LLM."""
        try:
            # Build context about the function
            context = {
                'function_name': func_info['name'],
                'arguments': func_info['args'],
                'is_async': func_info['is_async'],
                'file_path': file_analysis['file_path'],
                'imports': file_analysis['imports'][:10],  # Limit imports
                'existing_patterns': self.test_templates
            }
            
            prompt = f"""
Generate a simple unit test for the function '{func_info['name']}' in file '{file_analysis['file_path']}'.

Requirements:
- Function name: test_{func_info['name']}
- Use pytest format
- Include a docstring
- Keep it simple and syntactically correct
- Use basic assertions

Return only the Python code, no markdown or explanations:

def test_{func_info['name']}():
    \"\"\"Test the {func_info['name']} function.\"\"\"
    # TODO: Add test implementation
    assert True
"""
            
            response = self.claude.send_message(prompt)
            
            # Extract text from Claude's response
            if isinstance(response, dict) and 'content' in response:
                response_text = ""
                for item in response['content']:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        response_text += item.get('text', '')
                response = response_text
            
            # Clean up the response to ensure it's valid Python
            test_code = self._clean_generated_code(response)
            
            return test_code
            
        except Exception as e:
            logger.error(f"Failed to generate function test for {func_info['name']}: {e}")
            return None
    
    async def _generate_class_test(self, class_info: Dict[str, Any], file_analysis: Dict[str, Any]) -> Optional[str]:
        """Generate a test class for a Python class using LLM."""
        try:
            prompt = f"""
Generate a simple test class for the class '{class_info['name']}' in file '{file_analysis['file_path']}'.

Requirements:
- Class name: Test{class_info['name']}
- Use pytest format
- Include basic test methods
- Keep it simple and syntactically correct

Return only the Python code, no markdown or explanations:

class Test{class_info['name']}:
    \"\"\"Test class for {class_info['name']}.\"\"\"
    
    def test_init(self):
        \"\"\"Test class initialization.\"\"\"
        # TODO: Add test implementation
        assert True
"""
            
            response = self.claude.send_message(prompt)
            
            # Extract text from Claude's response
            if isinstance(response, dict) and 'content' in response:
                response_text = ""
                for item in response['content']:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        response_text += item.get('text', '')
                response = response_text
            
            test_code = self._clean_generated_code(response)
            
            return test_code
            
        except Exception as e:
            logger.error(f"Failed to generate class test for {class_info['name']}: {e}")
            return None
    
    async def _generate_api_test(self, endpoint: str, file_analysis: Dict[str, Any]) -> Optional[str]:
        """Generate an API integration test for an endpoint using LLM."""
        try:
            prompt = f"""
Generate a simple API test for the endpoint '{endpoint}' in file '{file_analysis['file_path']}'.

Requirements:
- Function name: test_api_{endpoint.replace('/', '_').replace('-', '_')}
- Use pytest format
- Test basic GET request
- Keep it simple and syntactically correct

Return only the Python code, no markdown or explanations:

def test_api_{endpoint.replace('/', '_').replace('-', '_')}():
    \"\"\"Test the {endpoint} endpoint.\"\"\"
    # TODO: Add API test implementation
    assert True
"""
            
            response = self.claude.send_message(prompt)
            
            # Extract text from Claude's response
            if isinstance(response, dict) and 'content' in response:
                response_text = ""
                for item in response['content']:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        response_text += item.get('text', '')
                response = response_text
            
            test_code = self._clean_generated_code(response)
            
            return test_code
            
        except Exception as e:
            logger.error(f"Failed to generate API test for {endpoint}: {e}")
            return None
    
    def _clean_generated_code(self, code: str) -> str:
        """Clean and validate generated test code."""
        try:
            # Remove markdown code blocks if present
            if '```python' in code:
                code = code.split('```python')[1].split('```')[0]
            elif '```' in code:
                code = code.split('```')[1].split('```')[0]
            
            # Remove leading/trailing whitespace
            code = code.strip()
            
            # Ensure proper indentation
            lines = code.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # Skip empty lines at start
                if not cleaned_lines and not line.strip():
                    continue
                cleaned_lines.append(line)
            
            # Validate syntax
            try:
                ast.parse('\n'.join(cleaned_lines))
            except SyntaxError as e:
                logger.warning(f"Generated code has syntax error: {e}")
                # Try to fix common issues
                cleaned_lines = self._fix_common_syntax_issues(cleaned_lines)
                
                # Validate again after fixes
                try:
                    ast.parse('\n'.join(cleaned_lines))
                except SyntaxError as e2:
                    logger.error(f"Could not fix syntax error: {e2}")
                    # Return a basic test template as fallback
                    return self._get_fallback_test_template()
            
            return '\n'.join(cleaned_lines)
            
        except Exception as e:
            logger.error(f"Failed to clean generated code: {e}")
            return code  # Return original if cleaning fails
    
    def _fix_common_syntax_issues(self, lines: List[str]) -> List[str]:
        """Fix common syntax issues in generated code."""
        fixed_lines = []
        open_brackets = {'(': 0, '[': 0, '{': 0}
        
        for i, line in enumerate(lines):
            # Skip empty lines
            if not line.strip():
                fixed_lines.append(line)
                continue
            
            # Fix common import issues
            if 'import' in line and not line.strip().startswith(('#', '"', "'")):
                if not line.strip().startswith('import') and not line.strip().startswith('from'):
                    continue  # Skip malformed import lines
            
            # Ensure proper function definitions
            if line.strip().startswith('def ') and not line.rstrip().endswith(':'):
                line = line.rstrip() + ':'
            
            # Track bracket balance
            for char in line:
                if char == '(':
                    open_brackets['('] += 1
                elif char == ')':
                    open_brackets['('] = max(0, open_brackets['('] - 1)
                elif char == '[':
                    open_brackets['['] += 1
                elif char == ']':
                    open_brackets['['] = max(0, open_brackets['['] - 1)
                elif char == '{':
                    open_brackets['{'] += 1
                elif char == '}':
                    open_brackets['{'] = max(0, open_brackets['{'] - 1)
            
            fixed_lines.append(line)
        
        # Close any unclosed brackets at the end
        closing_chars = []
        if open_brackets['('] > 0:
            closing_chars.extend([')'] * open_brackets['('])
        if open_brackets['['] > 0:
            closing_chars.extend([']'] * open_brackets['['])
        if open_brackets['{'] > 0:
            closing_chars.extend(['}'] * open_brackets['{'])
        
        if closing_chars:
            # Add closing brackets on a new line with proper indentation
            if fixed_lines and fixed_lines[-1].strip():
                indent = len(fixed_lines[-1]) - len(fixed_lines[-1].lstrip())
                fixed_lines.append(' ' * indent + ''.join(closing_chars))
        
        # Remove incomplete lines that would cause syntax errors
        final_lines = []
        for line in fixed_lines:
            stripped = line.strip()
            # Skip lines that are clearly incomplete
            if (stripped.endswith(('def ', 'class ', 'if ', 'for ', 'while ', 'try:', 'except ', 'with ')) or
                stripped in ['def', 'class', 'if', 'for', 'while', 'try', 'except', 'with']):
                # Add a pass statement to make it valid
                final_lines.append(line)
                indent = len(line) - len(line.lstrip()) + 4
                final_lines.append(' ' * indent + 'pass')
            else:
                final_lines.append(line)
        
        return final_lines
    
    def _get_fallback_test_template(self) -> str:
        """Return a basic test template when code generation fails."""
        return '''def test_placeholder():
    """Generated test placeholder - manual implementation needed."""
    # TODO: Implement actual test logic
    assert True  # Placeholder assertion
'''
    
    async def _save_generated_test(self, test_info: Dict[str, Any]):
        """Save a generated test to the appropriate file."""
        try:
            test_file_path = Path(test_info['file_path'])
            
            # Ensure test directory exists
            test_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if test file already exists
            if test_file_path.exists():
                # Append to existing file
                with open(test_file_path, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                
                # Check if test already exists
                if test_info['test_name'] in existing_content:
                    logger.info(f"Test {test_info['test_name']} already exists in {test_file_path}")
                    return
                
                # Append new test
                with open(test_file_path, 'a', encoding='utf-8') as f:
                    f.write(f'\n\n{test_info["test_code"]}')
            else:
                # Create new test file
                template = self._get_test_file_template()
                with open(test_file_path, 'w', encoding='utf-8') as f:
                    f.write(template + '\n\n' + test_info['test_code'])
            
            logger.info(f"Generated test saved to {test_file_path}")
            
            # Also save to output directory for review
            output_file = Path(self.test_config['output_dir']) / f"generated_{test_info['test_name']}_{int(datetime.now().timestamp())}.py"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(test_info['test_code'])
            
        except Exception as e:
            logger.error(f"Failed to save generated test {test_info['test_name']}: {e}")
    
    def _get_test_file_template(self) -> str:
        """Get template for new test files based on learned patterns."""
        common_imports = [
            "import pytest",
            "from unittest.mock import Mock, patch, MagicMock",
            "import json",
            "from datetime import datetime"
        ]
        
        # Add imports from learned patterns
        if 'imports' in self.test_templates:
            for imp in list(self.test_templates['imports'])[:5]:
                if imp not in common_imports and 'import' in imp:
                    common_imports.append(imp)
        
        template = '"""Generated test file by Tester Agent"""\n\n'
        template += '\n'.join(common_imports)
        template += '\n'
        
        return template
    
    async def _analyze_test_coverage(self) -> Dict[str, Any]:
        """Analyze current test coverage."""
        try:
            # Run coverage analysis
            result = subprocess.run([
                'python', '-m', 'pytest', '--cov=.', '--cov-report=json',
                '--cov-report=term-missing', '--quiet'
            ], capture_output=True, text=True, cwd='.')
            
            coverage_data = {}
            
            # Try to read coverage.json if it exists
            if os.path.exists('coverage.json'):
                with open('coverage.json', 'r') as f:
                    coverage_data = json.load(f)
            
            # Parse coverage output
            coverage_percentage = 0.0
            if result.stdout:
                # Extract coverage percentage from output
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'TOTAL' in line and '%' in line:
                        try:
                            coverage_percentage = float(line.split()[-1].replace('%', ''))
                        except (ValueError, IndexError):
                            pass
            
            return {
                'coverage_percentage': coverage_percentage,
                'coverage_data': coverage_data,
                'meets_threshold': coverage_percentage >= self.test_config['coverage_threshold'],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Coverage analysis failed: {e}")
            return {'error': str(e), 'coverage_percentage': 0.0}
    
    async def _identify_missing_tests(self) -> Dict[str, Any]:
        """Identify code areas that lack sufficient test coverage."""
        try:
            missing_scenarios = []
            
            # Analyze all Python files for untested code
            for root, dirs, files in os.walk('.'):
                # Skip test directories and virtual environments
                if any(skip in root for skip in ['tests', 'venv', '.git', '__pycache__']):
                    continue
                
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        
                        # Check if corresponding test file exists
                        test_file_name = f"test_{file}"
                        test_file_path = os.path.join('tests', test_file_name)
                        
                        if not os.path.exists(test_file_path):
                            # Analyze the file to understand what's missing
                            analysis = await self._analyze_python_file(file_path)
                            if analysis and (analysis['functions'] or analysis['classes'] or analysis['api_endpoints']):
                                missing_scenarios.append({
                                    'file_path': file_path,
                                    'missing_test_file': test_file_path,
                                    'untested_functions': len(analysis['functions']),
                                    'untested_classes': len(analysis['classes']),
                                    'untested_endpoints': len(analysis['api_endpoints']),
                                    'complexity_score': analysis['complexity_indicators']['complexity_score']
                                })
            
            # Sort by complexity score (prioritize complex code)
            missing_scenarios.sort(key=lambda x: x['complexity_score'], reverse=True)
            
            return {
                'missing_scenarios': missing_scenarios[:20],  # Limit to top 20
                'total_untested_files': len(missing_scenarios),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Missing test identification failed: {e}")
            return {'error': str(e)}
    
    async def _check_test_suite_health(self) -> Dict[str, Any]:
        """Check overall test suite health and performance."""
        try:
            # Run test suite
            result = subprocess.run([
                'python', '-m', 'pytest', '--tb=short', '-v'
            ], capture_output=True, text=True, cwd='.')
            
            # Parse test results
            output_lines = result.stdout.split('\n')
            
            test_stats = {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'skipped_tests': 0,
                'execution_time': 0.0
            }
            
            for line in output_lines:
                if '::' in line and ('PASSED' in line or 'FAILED' in line or 'SKIPPED' in line):
                    test_stats['total_tests'] += 1
                    if 'PASSED' in line:
                        test_stats['passed_tests'] += 1
                    elif 'FAILED' in line:
                        test_stats['failed_tests'] += 1
                    elif 'SKIPPED' in line:
                        test_stats['skipped_tests'] += 1
                
                # Extract execution time
                if 'seconds' in line and '=====' in line:
                    try:
                        time_match = re.search(r'(\d+\.?\d*)\s+seconds?', line)
                        if time_match:
                            test_stats['execution_time'] = float(time_match.group(1))
                    except (ValueError, AttributeError):
                        pass
            
            # Calculate health metrics
            health_score = 0.0
            if test_stats['total_tests'] > 0:
                health_score = (test_stats['passed_tests'] / test_stats['total_tests']) * 100
            
            return {
                'test_stats': test_stats,
                'health_score': health_score,
                'is_green': test_stats['failed_tests'] == 0,
                'execution_time': test_stats['execution_time'],
                'test_output': result.stdout[-1000:],  # Last 1000 chars
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Test suite health check failed: {e}")
            return {'error': str(e)}
    
    async def _compile_test_report(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compile comprehensive test analysis report."""
        try:
            # Extract key metrics
            coverage_percentage = analysis_results.get('coverage_analysis', {}).get('coverage_percentage', 0)
            tests_generated = len(analysis_results.get('test_generation', {}).get('generated_tests', []))
            missing_test_count = len(analysis_results.get('missing_tests', {}).get('missing_scenarios', []))
            test_health = analysis_results.get('test_health', {})
            
            # Determine overall status
            status = 'Healthy'
            if not test_health.get('is_green', True):
                status = 'Critical'
            elif coverage_percentage < self.test_config['coverage_threshold']:
                status = 'Needs Improvement'
            elif missing_test_count > 10:
                status = 'Needs Attention'
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'status': status,
                    'coverage_percentage': coverage_percentage,
                    'tests_generated': tests_generated,
                    'missing_test_scenarios': missing_test_count,
                    'test_suite_health': test_health.get('health_score', 0),
                    'is_green_suite': test_health.get('is_green', False)
                },
                'detailed_results': analysis_results,
                'recommendations': self._generate_test_recommendations(analysis_results)
            }
            
            # Save report
            report_file = f"{self.test_config['output_dir']}/test_report_{int(datetime.now().timestamp())}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            report['report_file'] = report_file
            
            return report
            
        except Exception as e:
            logger.error(f"Test report compilation failed: {e}")
            return {'error': str(e)}
    
    def _generate_test_recommendations(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable test recommendations."""
        recommendations = []
        
        # Coverage recommendations
        coverage_percentage = analysis_results.get('coverage_analysis', {}).get('coverage_percentage', 0)
        if coverage_percentage < self.test_config['coverage_threshold']:
            recommendations.append({
                'priority': 'High',
                'category': 'Coverage',
                'title': 'Improve Test Coverage',
                'description': f'Current coverage is {coverage_percentage:.1f}%, target is {self.test_config["coverage_threshold"]}%',
                'action': 'Focus on testing the most complex untested code first'
            })
        
        # Missing test recommendations
        missing_tests = analysis_results.get('missing_tests', {}).get('missing_scenarios', [])
        if missing_tests:
            top_missing = missing_tests[0]  # Highest complexity
            recommendations.append({
                'priority': 'Medium',
                'category': 'Missing Tests',
                'title': 'Add Tests for High-Complexity Code',
                'description': f'File {top_missing["file_path"]} has complexity score {top_missing["complexity_score"]} but no tests',
                'action': f'Create test file {top_missing["missing_test_file"]}'
            })
        
        # Test health recommendations
        test_health = analysis_results.get('test_health', {})
        if not test_health.get('is_green', True):
            recommendations.append({
                'priority': 'Critical',
                'category': 'Test Failures',
                'title': 'Fix Failing Tests',
                'description': f'{test_health.get("test_stats", {}).get("failed_tests", 0)} tests are currently failing',
                'action': 'Review and fix failing tests to maintain green test suite'
            })
        
        return recommendations
    
    async def _send_notifications(self, report: Dict[str, Any]):
        """Send Slack notifications based on test analysis results."""
        try:
            summary = report.get('summary', {})
            status = summary.get('status', 'Unknown')
            coverage = summary.get('coverage_percentage', 0)
            tests_generated = summary.get('tests_generated', 0)
            is_green = summary.get('is_green_suite', False)
            
            # Determine message based on status
            if status == 'Critical':
                emoji = "🚨"
                message = f"{emoji} **CRITICAL Test Suite Issues**\n"
                message += f"• Test suite is not green (failing tests detected)\n"
                message += f"• Coverage: {coverage:.1f}%\n"
                channel = "#corgi-alerts"
                
            elif status == 'Needs Improvement':
                emoji = "⚠️"
                message = f"{emoji} **Test Suite Needs Improvement**\n"
                message += f"• Coverage: {coverage:.1f}% (target: {self.test_config['coverage_threshold']}%)\n"
                message += f"• Tests generated: {tests_generated}\n"
                channel = "#corgi-testing"
                
            elif tests_generated > 0:
                emoji = "🧪"
                message = f"{emoji} **New Tests Generated**\n"
                message += f"• {tests_generated} new tests created\n"
                message += f"• Coverage: {coverage:.1f}%\n"
                message += f"• Suite status: {'Green ✅' if is_green else 'Has Issues ⚠️'}\n"
                channel = "#corgi-testing"
                
            else:
                emoji = "✅"
                message = f"{emoji} **Test Suite Health Check Complete**\n"
                message += f"• Status: {status}\n"
                message += f"• Coverage: {coverage:.1f}%\n"
                message += f"• Suite is green: {'Yes' if is_green else 'No'}\n"
                channel = "#corgi-testing"
            
            # Add recommendations
            recommendations = report.get('recommendations', [])
            if recommendations:
                message += f"\n**Top Recommendations:**\n"
                for rec in recommendations[:3]:
                    message += f"• {rec['title']}: {rec['description']}\n"
            
            # Add report file link
            if 'report_file' in report:
                message += f"\n📊 Full report: `{report['report_file']}`"
            
            if self.slack:
                await self.slack.send_message(message, channel=channel)
            
        except Exception as e:
            logger.error(f"Failed to send test notifications: {e}")
    
    async def health_check(self) -> bool:
        """Check if the agent is healthy and can perform its functions."""
        try:
            # Check if test directory exists
            test_dir = Path(self.test_config['test_dir'])
            if not test_dir.exists():
                logger.warning(f"Test directory {test_dir} does not exist")
                return False
            
            # Check if output directory is writable
            output_dir = Path(self.test_config['output_dir'])
            output_dir.mkdir(exist_ok=True)
            
            test_file = output_dir / 'health_check.tmp'
            test_file.write_text('test')
            test_file.unlink()
            
            # Check if Claude interface is available
            if not self.claude:
                return False
            
            # Check if Slack notifier is available
            if not self.slack:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Tester Agent health check failed: {e}")
            return False