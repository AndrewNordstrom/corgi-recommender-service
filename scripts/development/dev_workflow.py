#!/usr/bin/env python3
"""
Automated Development Workflow Manager

This script provides a unified development workflow that eliminates manual browser checking
and provides real-time feedback on both backend and frontend health.
"""

import asyncio
import subprocess
import sys
import os
import time
import json
import signal
from datetime import datetime
from typing import List, Dict, Optional
import argparse
import logging
from dataclasses import dataclass
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

@dataclass
class ServiceStatus:
    name: str
    status: str
    pid: Optional[int] = None
    port: Optional[int] = None
    url: Optional[str] = None
    last_check: Optional[datetime] = None

class DevWorkflowManager:
    def __init__(self,
                 backend_port: int = 5000,
                 frontend_port: int = 3000,
                 verbose: bool = False):
        load_dotenv()
        self.backend_port = int(os.environ.get('CORGI_API_HOST_PORT', backend_port))
        self.frontend_port = int(os.environ.get('FRONTEND_PORT', frontend_port))
        self.verbose = verbose

        # Service tracking
        self.services = {
            'backend': ServiceStatus('Backend API', 'stopped', port=self.backend_port, url=f'http://localhost:{self.backend_port}'),
            'frontend': ServiceStatus('Frontend', 'stopped', port=self.frontend_port, url=f'http://localhost:{self.frontend_port}'),
            'health_monitor': ServiceStatus('Health Monitor', 'stopped'),
            'browser_monitor': ServiceStatus('Browser Monitor', 'stopped')
        }

        self.processes = {}

        # Setup logging
        log_level = logging.INFO if verbose else logging.WARNING
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)

        # Create logs directory
        os.makedirs('logs', exist_ok=True)

        # Handle cleanup on exit
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle cleanup on exit"""
        print("\n🛑 Shutting down development workflow...")
        self.stop_all_services()
        sys.exit(0)

    def is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use"""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('localhost', port)) == 0
        except:
            return False

    def start_backend(self) -> bool:
        """Start the backend service"""
        if self.is_port_in_use(self.backend_port):
            self.logger.info(f"Backend already running on port {self.backend_port}")
            self.services['backend'].status = 'running'
            return True

        try:
            # Start Flask backend
            env = os.environ.copy()
            env['PORT'] = str(self.backend_port)
            env['HOST'] = 'localhost'

            # Ensure all necessary DB vars are present for the subprocess
            for key in ['POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'CORGI_API_HOST_PORT', 'USER_HASH_SALT']:
                if key in os.environ:
                    env[key] = os.environ[key]

            backend_log_file = open('logs/backend.log', 'w')
            process = subprocess.Popen(
                [sys.executable, 'app.py'],
                env=env,
                stdout=backend_log_file,
                stderr=subprocess.STDOUT,
                cwd=os.getcwd()
            )

            self.processes['backend'] = process
            self.services['backend'].status = 'starting'
            self.services['backend'].pid = process.pid

            # Give it a moment to start
            time.sleep(3)

            if process.poll() is None and self.is_port_in_use(self.backend_port):
                self.services['backend'].status = 'running'
                self.logger.info(f"✅ Backend started on port {self.backend_port} (PID: {process.pid})")
                return True
            else:
                self.services['backend'].status = 'failed'
                self.logger.error("❌ Backend failed to start. Check logs/backend.log")
                return False

        except Exception as e:
            self.services['backend'].status = 'failed'
            self.logger.error(f"❌ Failed to start backend: {e}")
            return False

    def start_frontend(self) -> bool:
        """Start the frontend service (ELK)"""
        if self.is_port_in_use(self.frontend_port):
            self.logger.info(f"Frontend already running on port {self.frontend_port}")
            self.services['frontend'].status = 'running'
            return True
        # For this project, the ELK frontend is managed by Docker Compose
        # We will just update its status based on port availability
        self.logger.info("Frontend is managed by Docker. Checking port...")
        if self.is_port_in_use(self.frontend_port):
             self.services['frontend'].status = 'running'
             return True
        else:
             self.services['frontend'].status = 'stopped'
             self.logger.warning("ELK frontend not detected on port 3000. Please start it separately.")
             return False


    def start_health_monitor(self) -> bool:
        """Start the health monitoring service"""
        try:
            process = subprocess.Popen([
                sys.executable, 'scripts/development/health_monitor.py',
                '--backend-url', f'http://localhost:{self.backend_port}',
                '--frontend-url', f'http://localhost:{self.frontend_port}',
                '--interval', '10'
            ] + (['--verbose'] if self.verbose else []),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            self.processes['health_monitor'] = process
            self.services['health_monitor'].status = 'running'
            self.services['health_monitor'].pid = process.pid

            self.logger.info(f"✅ Health monitor started (PID: {process.pid})")
            return True

        except Exception as e:
            self.services['health_monitor'].status = 'failed'
            self.logger.error(f"❌ Failed to start health monitor: {e}")
            return False

    def start_browser_monitor(self) -> bool:
        """Start the browser monitoring service"""
        try:
            process = subprocess.Popen([
                sys.executable, 'scripts/development/browser_monitor.py',
                '--frontend-url', f'http://localhost:{self.frontend_port}',
                '--interval', '30',
                '--headless'
            ] + (['--verbose'] if self.verbose else []),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            self.processes['browser_monitor'] = process
            self.services['browser_monitor'].status = 'running'
            self.services['browser_monitor'].pid = process.pid

            self.logger.info(f"✅ Browser monitor started (PID: {process.pid})")
            return True

        except Exception as e:
            self.services['browser_monitor'].status = 'failed'
            self.logger.error(f"❌ Failed to start browser monitor: {e}")
            return False

    def stop_service(self, service_name: str):
        """Stop a specific service"""
        if service_name in self.processes:
            process = self.processes[service_name]
            try:
                os.kill(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                if process.poll() is None:
                    os.kill(process.pid, signal.SIGKILL)
            except Exception:
                pass

            self.processes.pop(service_name, None)
            self.services[service_name].status = 'stopped'
            self.services[service_name].pid = None

    def stop_all_services(self):
        """Stop all running services"""
        for service_name in list(self.processes.keys()):
            self.stop_service(service_name)
        print("✅ All services stopped.")

    def clear_console(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def get_header(self):
        return "="*80 + f"\nDevelopment Workflow Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" + "="*80

    def get_footer(self):
        return "="*80 + f"\n💡 Monitoring active - press Ctrl+C to stop\n" + \
               f"📁 Logs: logs/health_monitor.log, logs/browser_monitor.log, logs/backend.log\n" + \
               f"🌐 Backend: http://localhost:{self.backend_port} | 🎨 Frontend: http://localhost:{self.frontend_port}\n" + "="*80

    def display_status_snapshot(self):
        """Display a snapshot of the current development workflow status."""
        for service in self.services.values():
            status_color = "\033[92m" if service.status == 'running' else "\033[93m" if 'starting' in service.status else "\033[91m"
            status_emoji = '✅' if service.status == 'running' else '⏳' if 'starting' in service.status else '❌'
            pid_info = f"PID: {service.pid:<5}" if service.pid else ""
            print(f"{status_color}{status_emoji} {service.name:<18} {service.status:<10} {pid_info}\033[0m")

        print("\n📊 Quick Status:")

        health_status_line = "⚪ Health checks pending..."
        if os.path.exists('logs/latest_health_check.json'):
            try:
                with open('logs/latest_health_check.json', 'r') as f:
                    health_data = json.load(f)
                
                # Handle both dict and list formats for robustness
                checks = []
                if isinstance(health_data, dict):
                    checks = health_data.get('checks', [])
                elif isinstance(health_data, list):
                    checks = health_data

                health_issues = [
                    check for check in checks
                    if check.get('status_code', 200) != 200 or check.get('status') != 'ok'
                ]
                if health_issues:
                    health_status_line = f"🚨 {len(health_issues)} health issues detected - check logs/latest_health_check.json"
                else:
                    health_status_line = "✅ All health checks passed"
            except (json.JSONDecodeError, FileNotFoundError):
                health_status_line = "❌ Failed to read health check data"

        browser_status_line = "⚪ Browser checks pending..."
        if os.path.exists('logs/latest_browser_check.json'):
            try:
                with open('logs/latest_browser_check.json', 'r') as f:
                    browser_data = json.load(f)
                browser_issues = [page for page in browser_data if page.get('status') != 'ok']
                if browser_issues:
                    browser_status_line = f"🚨 {len(browser_issues)} browser issues detected - check logs/latest_browser_check.json"
                else:
                    browser_status_line = "✅ All browser checks passed"
            except (json.JSONDecodeError, FileNotFoundError):
                browser_status_line = "❌ Failed to read browser check data"

        print(health_status_line)
        print(browser_status_line)


    async def run_full_workflow(self):
        """Run the full development workflow"""
        print("🚀 Starting full development workflow...")
        print("This will automatically monitor your services and alert you to issues")

        print("\n📦 Starting core services...")
        self.start_backend()
        self.start_frontend()

        print("\n⏳ Waiting for services to stabilize...")
        await asyncio.sleep(5)

        print("\n🔍 Starting monitoring services...")
        self.start_health_monitor()
        self.start_browser_monitor()

        await asyncio.sleep(2)

        try:
            while True:
                self.clear_console()
                print(self.get_header())
                self.display_status_snapshot()
                print(self.get_footer())
                await asyncio.sleep(15)

        except asyncio.CancelledError:
            print("\nWorkflow cancelled. Stopping services...")
        finally:
            self.stop_all_services()

def main():
    parser = argparse.ArgumentParser(description="Automated Development Workflow Manager")
    parser.add_argument("--status", action="store_true", help="Show status and exit (Not implemented)")
    parser.add_argument("--stop", action="store_true", help="Stop all services")

    args = parser.parse_args()

    manager = DevWorkflowManager()

    if args.stop:
        manager.stop_all_services()
    else:
        try:
            asyncio.run(manager.run_full_workflow())
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")

if __name__ == "__main__":
    main() 