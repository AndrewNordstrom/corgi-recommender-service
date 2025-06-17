"""
Profiler & Optimizer Agent

Autonomous performance analysis agent that proactively identifies performance bottlenecks
and optimization opportunities through automated benchmarking and LLM-powered analysis.

This agent:
- Runs nightly/weekly performance benchmarks
- Analyzes .pstats profiling files using LLM interpretation
- Identifies performance regressions and hotspots
- Suggests specific optimization strategies
- Reports findings to Manager Agent with Slack notifications
"""

import asyncio
import cProfile
import pstats
import io
import json
import os
import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging

from agents.base_agent import BaseAgent, AgentResult
from agents.claude_interface import ClaudeInterface
from agents.slack_notifier import SlackNotifier
from db.connection import get_db_connection, get_cursor

logger = logging.getLogger(__name__)

class ProfilerOptimizerAgent(BaseAgent):
    """
    Autonomous performance analysis and optimization agent.
    
    Proactively monitors system performance through automated benchmarking,
    analyzes profiling data using AI interpretation, and identifies optimization
    opportunities before they become critical issues.
    """
    
    def __init__(self):
        super().__init__(
            agent_id="profiler_optimizer",
            name="Profiler & Optimizer Agent",
            description="Autonomous performance analysis and optimization recommendations"
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
        
        # Performance tracking configuration
        self.benchmark_schedule = {
            'nightly': True,
            'weekly_deep': True,
            'on_demand': True
        }
        
        # Profiling configuration
        self.profiling_config = {
            'output_dir': 'logs/profiling',
            'benchmark_endpoints': [
                '/api/v1/recommendations',
                '/api/v1/posts',
                '/api/v1/timeline',
                '/health'
            ],
            'load_test_scenarios': [
                {'name': 'light_load', 'concurrent_users': 10, 'duration': 60},
                {'name': 'moderate_load', 'concurrent_users': 50, 'duration': 120},
                {'name': 'heavy_load', 'concurrent_users': 100, 'duration': 180}
            ]
        }
        
        # Performance thresholds for alerting
        self.performance_thresholds = {
            'response_time_ms': 500,
            'memory_usage_mb': 1000,
            'cpu_usage_percent': 80,
            'regression_threshold_percent': 20
        }
        
        # Ensure profiling directory exists
        os.makedirs(self.profiling_config['output_dir'], exist_ok=True)
        
    async def execute(self) -> AgentResult:
        """Execute profiler and optimizer analysis."""
        try:
            logger.info("🔍 Starting Profiler & Optimizer Agent execution")
            
            # Determine what type of analysis to run
            analysis_type = self._determine_analysis_type()
            
            results = []
            
            if analysis_type in ['nightly', 'weekly_deep']:
                # Run automated benchmarks
                benchmark_results = await self._run_automated_benchmarks()
                results.append(benchmark_results)
                
                # Analyze existing profiling data
                profiling_analysis = await self._analyze_profiling_data()
                results.append(profiling_analysis)
                
                # Performance regression detection
                regression_analysis = await self._detect_performance_regressions()
                results.append(regression_analysis)
                
            if analysis_type == 'weekly_deep':
                # Deep performance analysis
                deep_analysis = await self._run_deep_performance_analysis()
                results.append(deep_analysis)
                
            # Compile comprehensive report
            report = await self._compile_performance_report(results, analysis_type)
            
            # Send notifications if issues found
            await self._send_notifications(report)
            
            return AgentResult(
                success=True,
                message=f"Performance analysis completed: {analysis_type}",
                data={
                    'analysis_type': analysis_type,
                    'report': report,
                    'issues_found': len(report.get('critical_issues', [])),
                    'recommendations': len(report.get('recommendations', []))
                }
            )
            
        except Exception as e:
            logger.error(f"Profiler & Optimizer Agent execution failed: {e}")
            
            # Send error notification
            if self.slack:
                await self.slack.send_message(
                    f"🚨 Profiler & Optimizer Agent Error: {str(e)}",
                    channel="#corgi-alerts"
                )
            
            return AgentResult(
                success=False,
                message=f"Performance analysis failed: {str(e)}",
                data={'error': str(e)}
            )
    
    def _determine_analysis_type(self) -> str:
        """Determine what type of analysis to run based on schedule and triggers."""
        current_time = datetime.now()
        
        # Check if it's time for weekly deep analysis (Sundays at 2 AM)
        if (current_time.weekday() == 6 and 
            current_time.hour == 2 and 
            self.benchmark_schedule['weekly_deep']):
            return 'weekly_deep'
        
        # Check if it's time for nightly analysis (2 AM daily)
        if (current_time.hour == 2 and 
            self.benchmark_schedule['nightly']):
            return 'nightly'
        
        # Default to on-demand analysis
        return 'on_demand'
    
    async def _run_automated_benchmarks(self) -> Dict[str, Any]:
        """Run automated performance benchmarks."""
        logger.info("🏃 Running automated performance benchmarks")
        
        benchmark_results = {
            'timestamp': datetime.now().isoformat(),
            'endpoint_performance': {},
            'load_test_results': {},
            'system_metrics': {}
        }
        
        try:
            # Test individual endpoints
            for endpoint in self.profiling_config['benchmark_endpoints']:
                endpoint_result = await self._benchmark_endpoint(endpoint)
                benchmark_results['endpoint_performance'][endpoint] = endpoint_result
            
            # Run load tests
            for scenario in self.profiling_config['load_test_scenarios']:
                load_result = await self._run_load_test_scenario(scenario)
                benchmark_results['load_test_results'][scenario['name']] = load_result
            
            # Collect system metrics
            benchmark_results['system_metrics'] = await self._collect_system_metrics()
            
            # Save results
            self._save_benchmark_results(benchmark_results)
            
            return benchmark_results
            
        except Exception as e:
            logger.error(f"Benchmark execution failed: {e}")
            return {'error': str(e)}
    
    async def _benchmark_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """Benchmark a specific API endpoint."""
        try:
            # Create profiler
            profiler = cProfile.Profile()
            
            # Profile the endpoint
            profiler.enable()
            
            # Make test requests (using curl for simplicity)
            start_time = time.time()
            
            # Run multiple requests to get average performance
            response_times = []
            for _ in range(10):
                request_start = time.time()
                result = subprocess.run([
                    'curl', '-s', '-w', '%{time_total}',
                    f'http://localhost:5002{endpoint}',
                    '-H', 'X-API-Key: admin-key'
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    try:
                        response_time = float(result.stderr.strip()) * 1000  # Convert to ms
                        response_times.append(response_time)
                    except ValueError:
                        pass
                
                # Small delay between requests
                await asyncio.sleep(0.1)
            
            profiler.disable()
            
            # Save profiling data
            profile_file = f"{self.profiling_config['output_dir']}/profile_{endpoint.replace('/', '_')}_{int(time.time())}.pstats"
            profiler.dump_stats(profile_file)
            
            # Calculate statistics
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                min_response_time = min(response_times)
            else:
                avg_response_time = max_response_time = min_response_time = 0
            
            return {
                'endpoint': endpoint,
                'avg_response_time_ms': avg_response_time,
                'max_response_time_ms': max_response_time,
                'min_response_time_ms': min_response_time,
                'successful_requests': len(response_times),
                'profile_file': profile_file,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to benchmark endpoint {endpoint}: {e}")
            return {'endpoint': endpoint, 'error': str(e)}
    
    async def _run_load_test_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run a load test scenario."""
        logger.info(f"🔥 Running load test: {scenario['name']}")
        
        try:
            # Use Apache Bench (ab) for load testing
            cmd = [
                'ab',
                '-n', str(scenario['concurrent_users'] * 10),  # Total requests
                '-c', str(scenario['concurrent_users']),        # Concurrent requests
                '-H', 'X-API-Key: admin-key',
                'http://localhost:5002/api/v1/recommendations'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=scenario['duration'] + 60)
            
            if result.returncode == 0:
                # Parse ab output
                output = result.stdout
                
                # Extract key metrics (basic parsing)
                metrics = {
                    'scenario': scenario['name'],
                    'concurrent_users': scenario['concurrent_users'],
                    'duration': scenario['duration'],
                    'timestamp': datetime.now().isoformat()
                }
                
                # Parse response time and throughput from ab output
                for line in output.split('\n'):
                    if 'Time per request:' in line and 'mean' in line:
                        try:
                            metrics['avg_response_time_ms'] = float(line.split()[3])
                        except (IndexError, ValueError):
                            pass
                    elif 'Requests per second:' in line:
                        try:
                            metrics['requests_per_second'] = float(line.split()[3])
                        except (IndexError, ValueError):
                            pass
                    elif 'Failed requests:' in line:
                        try:
                            metrics['failed_requests'] = int(line.split()[2])
                        except (IndexError, ValueError):
                            pass
                
                return metrics
            else:
                return {
                    'scenario': scenario['name'],
                    'error': f"Load test failed: {result.stderr}",
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Load test scenario {scenario['name']} failed: {e}")
            return {
                'scenario': scenario['name'],
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system performance metrics."""
        try:
            import psutil
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'memory_total_mb': memory.total / (1024 * 1024),
                'memory_used_mb': memory.used / (1024 * 1024),
                'memory_percent': memory.percent,
                'disk_total_gb': disk.total / (1024 * 1024 * 1024),
                'disk_used_gb': disk.used / (1024 * 1024 * 1024),
                'disk_percent': (disk.used / disk.total) * 100,
                'timestamp': datetime.now().isoformat()
            }
            
        except ImportError:
            logger.warning("psutil not available, skipping system metrics")
            return {'error': 'psutil not available'}
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {'error': str(e)}
    
    async def _analyze_profiling_data(self) -> Dict[str, Any]:
        """Analyze existing profiling data using LLM interpretation."""
        logger.info("🧠 Analyzing profiling data with LLM interpretation")
        
        try:
            # Find recent .pstats files
            profiling_dir = Path(self.profiling_config['output_dir'])
            pstats_files = list(profiling_dir.glob('*.pstats'))
            
            # Sort by modification time, get most recent
            recent_files = sorted(pstats_files, key=lambda f: f.stat().st_mtime, reverse=True)[:5]
            
            if not recent_files:
                return {'message': 'No profiling data found to analyze'}
            
            analysis_results = []
            
            for pstats_file in recent_files:
                # Extract profiling statistics
                stats_summary = self._extract_pstats_summary(pstats_file)
                
                # Use LLM to analyze the profiling data
                llm_analysis = await self._llm_analyze_profiling_data(stats_summary, pstats_file.name)
                
                analysis_results.append({
                    'file': pstats_file.name,
                    'stats_summary': stats_summary,
                    'llm_analysis': llm_analysis
                })
            
            return {
                'analyzed_files': len(analysis_results),
                'analyses': analysis_results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Profiling data analysis failed: {e}")
            return {'error': str(e)}
    
    def _extract_pstats_summary(self, pstats_file: Path) -> Dict[str, Any]:
        """Extract key statistics from a .pstats file."""
        try:
            # Load profiling data
            stats = pstats.Stats(str(pstats_file))
            
            # Capture stats output
            output = io.StringIO()
            stats.print_stats(20)  # Top 20 functions
            stats_output = output.getvalue()
            
            # Get top functions by cumulative time
            stats.sort_stats('cumulative')
            top_functions = []
            
            # Extract function data (simplified)
            for func, (cc, nc, tt, ct, callers) in list(stats.stats.items())[:10]:
                top_functions.append({
                    'function': f"{func[0]}:{func[1]}({func[2]})",
                    'call_count': cc,
                    'total_time': tt,
                    'cumulative_time': ct,
                    'per_call_time': tt/cc if cc > 0 else 0
                })
            
            return {
                'total_calls': stats.total_calls,
                'total_time': stats.total_tt,
                'top_functions': top_functions,
                'raw_output_preview': stats_output[:1000]  # First 1000 chars
            }
            
        except Exception as e:
            logger.error(f"Failed to extract pstats summary from {pstats_file}: {e}")
            return {'error': str(e)}
    
    async def _llm_analyze_profiling_data(self, stats_summary: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Use LLM to analyze profiling data and identify optimization opportunities."""
        try:
            prompt = f"""
Analyze this Python profiling data from {filename} and identify performance optimization opportunities:

PROFILING SUMMARY:
- Total calls: {stats_summary.get('total_calls', 'N/A')}
- Total time: {stats_summary.get('total_time', 'N/A')} seconds
- Top functions by time:

{json.dumps(stats_summary.get('top_functions', []), indent=2)}

RAW PROFILING OUTPUT (preview):
{stats_summary.get('raw_output_preview', 'No preview available')}

Please provide:
1. **Performance Hotspots**: Identify the top 3 performance bottlenecks
2. **Optimization Recommendations**: Specific, actionable suggestions for each hotspot
3. **Severity Assessment**: Rate each issue as Critical/High/Medium/Low
4. **Implementation Priority**: Order recommendations by impact vs effort
5. **Code Areas**: Specific files/functions that need attention

Format your response as JSON with the following structure:
{{
    "hotspots": [
        {{
            "function": "function_name",
            "issue": "description of performance issue",
            "severity": "Critical/High/Medium/Low",
            "time_impact": "percentage or time spent"
        }}
    ],
    "recommendations": [
        {{
            "title": "optimization title",
            "description": "detailed recommendation",
            "priority": "High/Medium/Low",
            "effort": "High/Medium/Low",
            "expected_improvement": "description of expected improvement",
            "code_areas": ["file1.py", "file2.py"]
        }}
    ],
    "overall_assessment": "summary of performance state"
}}
"""
            
            response = await self.claude.generate_response(prompt)
            
            # Try to parse JSON response
            try:
                analysis = json.loads(response)
                return analysis
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw response
                return {
                    'raw_analysis': response,
                    'parse_error': 'Failed to parse JSON response'
                }
                
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return {'error': str(e)}
    
    async def _detect_performance_regressions(self) -> Dict[str, Any]:
        """Detect performance regressions by comparing recent benchmarks."""
        logger.info("📈 Detecting performance regressions")
        
        try:
            # Load recent benchmark results
            benchmark_files = list(Path(self.profiling_config['output_dir']).glob('benchmarks_*.json'))
            
            if len(benchmark_files) < 2:
                return {'message': 'Not enough benchmark data for regression analysis'}
            
            # Sort by modification time
            recent_files = sorted(benchmark_files, key=lambda f: f.stat().st_mtime, reverse=True)[:5]
            
            # Load and compare benchmarks
            current_benchmark = self._load_benchmark_file(recent_files[0])
            previous_benchmarks = [self._load_benchmark_file(f) for f in recent_files[1:]]
            
            regressions = []
            
            # Compare endpoint performance
            if 'endpoint_performance' in current_benchmark:
                for endpoint, current_perf in current_benchmark['endpoint_performance'].items():
                    if 'avg_response_time_ms' in current_perf:
                        current_time = current_perf['avg_response_time_ms']
                        
                        # Compare with previous benchmarks
                        for prev_benchmark in previous_benchmarks:
                            if (endpoint in prev_benchmark.get('endpoint_performance', {}) and
                                'avg_response_time_ms' in prev_benchmark['endpoint_performance'][endpoint]):
                                
                                prev_time = prev_benchmark['endpoint_performance'][endpoint]['avg_response_time_ms']
                                
                                if prev_time > 0:  # Avoid division by zero
                                    regression_percent = ((current_time - prev_time) / prev_time) * 100
                                    
                                    if regression_percent > self.performance_thresholds['regression_threshold_percent']:
                                        regressions.append({
                                            'type': 'endpoint_regression',
                                            'endpoint': endpoint,
                                            'current_time_ms': current_time,
                                            'previous_time_ms': prev_time,
                                            'regression_percent': regression_percent,
                                            'severity': 'Critical' if regression_percent > 50 else 'High' if regression_percent > 30 else 'Medium'
                                        })
                                break  # Only compare with most recent previous benchmark
            
            return {
                'regressions_found': len(regressions),
                'regressions': regressions,
                'benchmarks_compared': len(recent_files),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Regression detection failed: {e}")
            return {'error': str(e)}
    
    def _load_benchmark_file(self, file_path: Path) -> Dict[str, Any]:
        """Load benchmark data from JSON file."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load benchmark file {file_path}: {e}")
            return {}
    
    async def _run_deep_performance_analysis(self) -> Dict[str, Any]:
        """Run comprehensive deep performance analysis (weekly)."""
        logger.info("🔬 Running deep performance analysis")
        
        try:
            analysis_results = {
                'database_performance': await self._analyze_database_performance(),
                'memory_analysis': await self._analyze_memory_usage(),
                'algorithm_performance': await self._analyze_algorithm_performance(),
                'system_bottlenecks': await self._identify_system_bottlenecks()
            }
            
            return {
                'analysis_type': 'deep_analysis',
                'results': analysis_results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Deep performance analysis failed: {e}")
            return {'error': str(e)}
    
    async def _analyze_database_performance(self) -> Dict[str, Any]:
        """Analyze database query performance."""
        try:
            with get_db_connection() as conn:
                with get_cursor(conn) as cursor:
                    # Get slow query information (if available)
                    cursor.execute("PRAGMA compile_options")  # SQLite version check
                    
                    # Basic database statistics
                    cursor.execute("SELECT COUNT(*) FROM interactions")
                    interaction_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM crawled_posts")
                    post_count = cursor.fetchone()[0]
                    
                    return {
                        'interaction_count': interaction_count,
                        'post_count': post_count,
                        'analysis': 'Basic database metrics collected'
                    }
                    
        except Exception as e:
            logger.error(f"Database performance analysis failed: {e}")
            return {'error': str(e)}
    
    async def _analyze_memory_usage(self) -> Dict[str, Any]:
        """Analyze memory usage patterns."""
        try:
            import psutil
            process = psutil.Process()
            
            return {
                'memory_info': process.memory_info()._asdict(),
                'memory_percent': process.memory_percent(),
                'open_files': len(process.open_files()),
                'num_threads': process.num_threads()
            }
            
        except ImportError:
            return {'error': 'psutil not available for memory analysis'}
        except Exception as e:
            logger.error(f"Memory analysis failed: {e}")
            return {'error': str(e)}
    
    async def _analyze_algorithm_performance(self) -> Dict[str, Any]:
        """Analyze recommendation algorithm performance."""
        try:
            # Profile the ranking algorithm
            profiler = cProfile.Profile()
            profiler.enable()
            
            # Import and test ranking algorithm
            from core.ranking_algorithm import generate_rankings_for_user
            
            # Test with a sample user
            start_time = time.time()
            rankings = generate_rankings_for_user("test_user_performance")
            end_time = time.time()
            
            profiler.disable()
            
            # Save algorithm profiling data
            algo_profile_file = f"{self.profiling_config['output_dir']}/algorithm_profile_{int(time.time())}.pstats"
            profiler.dump_stats(algo_profile_file)
            
            return {
                'execution_time_ms': (end_time - start_time) * 1000,
                'recommendations_generated': len(rankings),
                'profile_file': algo_profile_file,
                'analysis': 'Algorithm performance profiled successfully'
            }
            
        except Exception as e:
            logger.error(f"Algorithm performance analysis failed: {e}")
            return {'error': str(e)}
    
    async def _identify_system_bottlenecks(self) -> Dict[str, Any]:
        """Identify system-level bottlenecks."""
        try:
            import psutil
            
            # CPU usage by process
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Sort by CPU usage
            top_cpu_processes = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:10]
            
            # Sort by memory usage
            top_memory_processes = sorted(processes, key=lambda x: x['memory_percent'] or 0, reverse=True)[:10]
            
            return {
                'top_cpu_processes': top_cpu_processes,
                'top_memory_processes': top_memory_processes,
                'total_processes': len(processes)
            }
            
        except ImportError:
            return {'error': 'psutil not available for system analysis'}
        except Exception as e:
            logger.error(f"System bottleneck analysis failed: {e}")
            return {'error': str(e)}
    
    async def _compile_performance_report(self, results: List[Dict[str, Any]], analysis_type: str) -> Dict[str, Any]:
        """Compile comprehensive performance report."""
        try:
            # Extract critical issues
            critical_issues = []
            recommendations = []
            
            for result in results:
                if isinstance(result, dict):
                    # Extract regressions
                    if 'regressions' in result:
                        for regression in result['regressions']:
                            if regression.get('severity') in ['Critical', 'High']:
                                critical_issues.append(regression)
                    
                    # Extract LLM recommendations
                    if 'analyses' in result:
                        for analysis in result['analyses']:
                            if 'llm_analysis' in analysis and 'recommendations' in analysis['llm_analysis']:
                                recommendations.extend(analysis['llm_analysis']['recommendations'])
            
            # Create summary
            report = {
                'analysis_type': analysis_type,
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_analyses': len(results),
                    'critical_issues': len(critical_issues),
                    'recommendations': len(recommendations),
                    'status': 'Critical' if critical_issues else 'Good' if recommendations else 'Healthy'
                },
                'critical_issues': critical_issues,
                'recommendations': recommendations,
                'detailed_results': results
            }
            
            # Save report
            report_file = f"{self.profiling_config['output_dir']}/performance_report_{analysis_type}_{int(time.time())}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            report['report_file'] = report_file
            
            return report
            
        except Exception as e:
            logger.error(f"Report compilation failed: {e}")
            return {'error': str(e)}
    
    def _save_benchmark_results(self, results: Dict[str, Any]):
        """Save benchmark results to file."""
        try:
            timestamp = int(time.time())
            filename = f"{self.profiling_config['output_dir']}/benchmarks_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Benchmark results saved to {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save benchmark results: {e}")
    
    async def _send_notifications(self, report: Dict[str, Any]):
        """Send Slack notifications based on report findings."""
        try:
            summary = report.get('summary', {})
            status = summary.get('status', 'Unknown')
            critical_issues = len(report.get('critical_issues', []))
            recommendations = len(report.get('recommendations', []))
            
            # Determine message based on findings
            if status == 'Critical':
                emoji = "🚨"
                message = f"{emoji} **CRITICAL Performance Issues Detected**\n"
                message += f"• {critical_issues} critical performance issues found\n"
                message += f"• {recommendations} optimization recommendations available\n"
                message += f"• Analysis type: {report.get('analysis_type', 'unknown')}\n"
                
                # Add top issues
                for issue in report.get('critical_issues', [])[:3]:
                    if issue.get('type') == 'endpoint_regression':
                        message += f"• ⚠️ {issue['endpoint']}: {issue['regression_percent']:.1f}% slower\n"
                
                channel = "#corgi-alerts"
                
            elif recommendations:
                emoji = "💡"
                message = f"{emoji} **Performance Optimization Opportunities**\n"
                message += f"• {recommendations} optimization recommendations found\n"
                message += f"• Analysis type: {report.get('analysis_type', 'unknown')}\n"
                message += f"• Overall status: {status}\n"
                
                channel = "#corgi-performance"
                
            else:
                emoji = "✅"
                message = f"{emoji} **Performance Analysis Complete**\n"
                message += f"• Status: {status}\n"
                message += f"• Analysis type: {report.get('analysis_type', 'unknown')}\n"
                message += f"• No critical issues detected\n"
                
                channel = "#corgi-performance"
            
            # Add report file link if available
            if 'report_file' in report:
                message += f"• 📊 Full report: `{report['report_file']}`"
            
            if self.slack:
                await self.slack.send_message(message, channel=channel)
            
        except Exception as e:
            logger.error(f"Failed to send notifications: {e}")
    
    async def health_check(self) -> bool:
        """Check if the agent is healthy and can perform its functions."""
        try:
            # Check if profiling directory exists and is writable
            profiling_dir = Path(self.profiling_config['output_dir'])
            if not profiling_dir.exists():
                profiling_dir.mkdir(parents=True)
            
            # Test file creation
            test_file = profiling_dir / 'health_check.tmp'
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
            logger.error(f"Profiler & Optimizer Agent health check failed: {e}")
            return False