#!/usr/bin/env python3
"""
Automated Health Monitor for Corgi Recommender Service

This script continuously monitors the health of both backend and frontend services,
automatically detecting 503 errors, API failures, and frontend issues without
requiring manual browser interaction.
"""

import asyncio
import aiohttp
import json
import time
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass
import argparse

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

@dataclass
class HealthCheckResult:
    service: str
    endpoint: str
    status: str
    response_time: float
    status_code: Optional[int] = None
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class HealthMonitor:
    def __init__(self, 
                 backend_url: str = None,
                 frontend_url: str = None,
                 check_interval: int = 10,
                 verbose: bool = False):
        # Auto-detect ports from environment variables if URLs not provided
        if backend_url is None:
            backend_port = os.getenv("CORGI_PORT", "9999")
            backend_url = f"http://localhost:{backend_port}"
        if frontend_url is None:
            frontend_port = os.getenv("FRONTEND_PORT", "3000")
            frontend_url = f"http://localhost:{frontend_port}"
        self.backend_url = backend_url
        self.frontend_url = frontend_url
        self.check_interval = check_interval
        self.verbose = verbose
        
        # Setup logging
        log_level = logging.INFO if verbose else logging.WARNING
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('logs/health_monitor.log', mode='a')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Track consecutive failures
        self.failure_counts = {}
        self.last_success = {}
        
        # Define endpoints to check
        self.endpoints = {
            'backend': [
                '/health',
                '/api/v1/health',
                '/api/v1/recommendations',
                '/api/v1/posts',
            ],
            'frontend': [
                '/',
                '/api/health',  # Next.js API route
            ]
        }

    async def check_endpoint(self, session: aiohttp.ClientSession, 
                           base_url: str, endpoint: str, service: str) -> HealthCheckResult:
        """Check a single endpoint and return result"""
        url = f"{base_url}{endpoint}"
        start_time = time.time()
        
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                response_time = time.time() - start_time
                
                # Check if response is successful
                if response.status == 200:
                    status = "✅ HEALTHY"
                    error = None
                elif response.status == 503:
                    status = "🔴 SERVICE UNAVAILABLE (503)"
                    error = f"Service unavailable: {await response.text()}"
                elif response.status >= 400:
                    status = f"⚠️  HTTP {response.status}"
                    error = f"HTTP {response.status}: {await response.text()}"
                else:
                    status = f"❓ HTTP {response.status}"
                    error = None
                
                return HealthCheckResult(
                    service=service,
                    endpoint=endpoint,
                    status=status,
                    response_time=response_time,
                    status_code=response.status,
                    error=error
                )
                
        except asyncio.TimeoutError:
            return HealthCheckResult(
                service=service,
                endpoint=endpoint,
                status="⏱️  TIMEOUT",
                response_time=time.time() - start_time,
                error="Request timed out after 5 seconds"
            )
        except aiohttp.ClientConnectorError:
            return HealthCheckResult(
                service=service,
                endpoint=endpoint,
                status="🔌 CONNECTION FAILED",
                response_time=time.time() - start_time,
                error="Could not connect to service"
            )
        except Exception as e:
            return HealthCheckResult(
                service=service,
                endpoint=endpoint,
                status="💥 ERROR",
                response_time=time.time() - start_time,
                error=str(e)
            )

    async def check_all_endpoints(self) -> List[HealthCheckResult]:
        """Check all configured endpoints"""
        results = []
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            # Backend endpoints
            for endpoint in self.endpoints['backend']:
                tasks.append(
                    self.check_endpoint(session, self.backend_url, endpoint, 'backend')
                )
            
            # Frontend endpoints
            for endpoint in self.endpoints['frontend']:
                tasks.append(
                    self.check_endpoint(session, self.frontend_url, endpoint, 'frontend')
                )
            
            results = await asyncio.gather(*tasks)
        
        return results

    def update_failure_tracking(self, results: List[HealthCheckResult]):
        """Track consecutive failures and recovery"""
        for result in results:
            key = f"{result.service}:{result.endpoint}"
            
            if result.status_code != 200:
                # Increment failure count
                self.failure_counts[key] = self.failure_counts.get(key, 0) + 1
                
                # Alert on consecutive failures
                if self.failure_counts[key] == 3:
                    self.logger.error(f"🚨 ALERT: {key} has failed 3 times consecutively!")
                elif self.failure_counts[key] == 1:
                    self.logger.warning(f"⚠️  First failure detected for {key}")
            else:
                # Reset failure count on success
                if key in self.failure_counts and self.failure_counts[key] > 0:
                    prev_failures = self.failure_counts[key]
                    self.failure_counts[key] = 0
                    self.last_success[key] = datetime.now()
                    self.logger.info(f"✅ {key} recovered after {prev_failures} failures")

    def format_results(self, results: List[HealthCheckResult]) -> str:
        """Format results for display"""
        lines = []
        lines.append("=" * 80)
        lines.append(f"Health Check Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        
        # Group by service
        backend_results = [r for r in results if r.service == 'backend']
        frontend_results = [r for r in results if r.service == 'frontend']
        
        for service_name, service_results in [('BACKEND', backend_results), ('FRONTEND', frontend_results)]:
            lines.append(f"\n{service_name}:")
            lines.append("-" * 40)
            
            for result in service_results:
                response_time_ms = result.response_time * 1000
                lines.append(f"  {result.endpoint:<20} {result.status:<25} ({response_time_ms:.1f}ms)")
                
                if result.error and self.verbose:
                    lines.append(f"    Error: {result.error}")
        
        # Add failure summary
        active_failures = {k: v for k, v in self.failure_counts.items() if v > 0}
        if active_failures:
            lines.append("\n🔴 ACTIVE FAILURES:")
            lines.append("-" * 40)
            for endpoint, count in active_failures.items():
                lines.append(f"  {endpoint}: {count} consecutive failures")
        
        return "\n".join(lines)

    async def run_continuous_monitoring(self):
        """Run continuous health monitoring"""
        self.logger.info(f"Starting health monitoring (interval: {self.check_interval}s)")
        self.logger.info(f"Backend URL: {self.backend_url}")
        self.logger.info(f"Frontend URL: {self.frontend_url}")
        
        try:
            while True:
                results = await self.check_all_endpoints()
                self.update_failure_tracking(results)
                
                # Always show results if there are issues
                has_issues = any(r.status_code != 200 for r in results if r.status_code is not None)
                
                if has_issues or self.verbose:
                    output = self.format_results(results)
                    print(output)
                    
                    # Save to file for debugging using an atomic write pattern
                    temp_file_path = 'logs/latest_health_check.json.tmp'
                    final_file_path = 'logs/latest_health_check.json'
                    try:
                        with open(temp_file_path, 'w') as f:
                            json.dump({
                                'summary': {
                                    'total_checks': len(results),
                                    'failed_checks': len([r for r in results if r.status_code != 200 and r.status_code is not None]),
                                    'timestamp': datetime.now().isoformat()
                                },
                                'checks': [{
                                    'service': r.service,
                                    'endpoint': r.endpoint,
                                    'status': r.status,
                                    'response_time': r.response_time,
                                    'status_code': r.status_code,
                                    'error': r.error,
                                    'timestamp': r.timestamp.isoformat()
                                } for r in results]
                            }, f, indent=2)
                        os.rename(temp_file_path, final_file_path)
                    except Exception as e:
                        self.logger.error(f"Failed to write health check file: {e}")
                
                await asyncio.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Health monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Health monitoring error: {e}")

def main():
    # Auto-detect ports from environment variables
    backend_port = os.getenv("CORGI_PORT", "9999")
    frontend_port = os.getenv("FRONTEND_PORT", "3000")
    default_backend_url = f"http://localhost:{backend_port}"
    default_frontend_url = f"http://localhost:{frontend_port}"
    
    parser = argparse.ArgumentParser(description="Automated Health Monitor for Corgi Recommender Service")
    parser.add_argument("--backend-url", default=default_backend_url, help="Backend URL")
    parser.add_argument("--frontend-url", default=default_frontend_url, help="Frontend URL")
    parser.add_argument("--interval", type=int, default=10, help="Check interval in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    
    monitor = HealthMonitor(
        backend_url=args.backend_url,
        frontend_url=args.frontend_url,
        check_interval=args.interval,
        verbose=args.verbose
    )
    
    if args.once:
        # Run once and exit
        async def run_once():
            results = await monitor.check_all_endpoints()
            output = monitor.format_results(results)
            print(output)

            # Save to file as well
            with open('logs/latest_health_check.json', 'w') as f:
                json.dump({
                    'summary': {
                        'total_checks': len(results),
                        'failed_checks': len([r for r in results if r.status_code != 200 and r.status_code is not None]),
                        'timestamp': datetime.now().isoformat()
                    },
                    'checks': [{
                        'service': r.service,
                        'endpoint': r.endpoint,
                        'status': r.status,
                        'response_time': r.response_time,
                        'status_code': r.status_code,
                        'error': r.error,
                        'timestamp': r.timestamp.isoformat()
                    } for r in results]
                }, f, indent=2)

            # Exit with error code if any checks failed
            has_issues = any(r.status_code != 200 for r in results if r.status_code is not None)
            if has_issues:
                sys.exit(1)

        asyncio.run(run_once())
    else:
        # Run continuous monitoring
        asyncio.run(monitor.run_continuous_monitoring())

if __name__ == "__main__":
    main() 