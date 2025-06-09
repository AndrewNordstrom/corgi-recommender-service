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
        self.backend_port = backend_port
        self.frontend_port = frontend_port
        self.verbose = verbose
        
        # Service tracking
        self.services = {
            'backend': ServiceStatus('Backend API', 'stopped', port=backend_port, url=f'http://localhost:{backend_port}'),
            'frontend': ServiceStatus('Frontend', 'stopped', port=frontend_port, url=f'http://localhost:{frontend_port}'),
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
            
            process = subprocess.Popen(
                [sys.executable, 'app.py'],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
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
                self.logger.error("❌ Backend failed to start")
                return False
                
        except Exception as e:
            self.services['backend'].status = 'failed'
            self.logger.error(f"❌ Failed to start backend: {e}")
            return False

    def start_frontend(self) -> bool:
        """Start the frontend service"""
        if self.is_port_in_use(self.frontend_port):
            self.logger.info(f"Frontend already running on port {self.frontend_port}")
            self.services['frontend'].status = 'running'
            return True
        
        try:
            # Check if we're in the frontend directory or need to change
            frontend_dir = 'frontend' if os.path.exists('frontend') else '.'
            
            # Start Next.js frontend
            process = subprocess.Popen(
                ['npm', 'run', 'dev'],
                cwd=frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=dict(os.environ, PORT=str(self.frontend_port))
            )
            
            self.processes['frontend'] = process
            self.services['frontend'].status = 'starting'
            self.services['frontend'].pid = process.pid
            
            # Give it time to start (Next.js takes longer)
            for _ in range(15):  # Wait up to 15 seconds
                time.sleep(1)
                if self.is_port_in_use(self.frontend_port):
                    break
            
            if process.poll() is None and self.is_port_in_use(self.frontend_port):
                self.services['frontend'].status = 'running'
                self.logger.info(f"✅ Frontend started on port {self.frontend_port} (PID: {process.pid})")
                return True
            else:
                self.services['frontend'].status = 'failed'
                self.logger.error("❌ Frontend failed to start") 
                return False
                
        except Exception as e:
            self.services['frontend'].status = 'failed'
            self.logger.error(f"❌ Failed to start frontend: {e}")
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
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
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
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
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
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except:
                pass
            
            del self.processes[service_name]
            self.services[service_name].status = 'stopped'
            self.services[service_name].pid = None

    def stop_all_services(self):
        """Stop all running services"""
        for service_name in list(self.processes.keys()):
            self.stop_service(service_name)

    def get_service_status(self) -> Dict:
        """Get current status of all services"""
        status = {}
        for name, service in self.services.items():
            # Update status for running processes
            if service.pid and name in self.processes:
                process = self.processes[name]
                if process.poll() is not None:
                    # Process has died
                    service.status = 'failed'
                    service.pid = None
                    del self.processes[name]
            
            status[name] = {
                'name': service.name,
                'status': service.status,
                'pid': service.pid,
                'port': service.port,
                'url': service.url
            }
        
        return status

    def display_status(self):
        """Display current status of all services"""
        status = self.get_service_status()
        
        print("\n" + "=" * 80)
        print(f"Development Workflow Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        for service_name, info in status.items():
            status_emoji = {
                'running': '✅',
                'starting': '🟡',
                'stopped': '⚫',
                'failed': '❌'
            }.get(info['status'], '❓')
            
            print(f"{status_emoji} {info['name']:<20} {info['status']:<10}", end="")
            
            if info['pid']:
                print(f" PID: {info['pid']:<8}", end="")
            if info['port']:
                print(f" Port: {info['port']:<6}", end="")
            if info['url']:
                print(f" URL: {info['url']}", end="")
            
            print()
        
        print("\n📊 Quick Status:")
        if status['backend']['status'] == 'running' and status['frontend']['status'] == 'running':
            print("✅ Both services are running - ready for development!")
        elif status['backend']['status'] == 'running':
            print("⚠️  Backend only - frontend may need attention")
        elif status['frontend']['status'] == 'running':
            print("⚠️  Frontend only - backend may need attention")
        else:
            print("❌ Services need to be started")

    async def run_full_workflow(self):
        """Run the complete development workflow"""
        print("🚀 Starting Corgi Recommender Development Workflow")
        print("This will automatically monitor your services and alert you to issues")
        
        # Start core services
        print("\n📦 Starting core services...")
        backend_ok = self.start_backend()
        frontend_ok = self.start_frontend()
        
        if not backend_ok and not frontend_ok:
            print("❌ Failed to start any services. Check your setup.")
            return
        
        # Wait a bit for services to stabilize
        print("⏳ Waiting for services to stabilize...")
        await asyncio.sleep(5)
        
        # Start monitoring services
        print("\n🔍 Starting monitoring services...")
        self.start_health_monitor()
        self.start_browser_monitor()
        
        # Main monitoring loop
        try:
            while True:
                self.display_status()
                
                # Check if monitoring services are capturing issues
                if os.path.exists('logs/latest_health_check.json'):
                    with open('logs/latest_health_check.json', 'r') as f:
                        health_data = json.load(f)
                        issues = [r for r in health_data if r.get('status_code') != 200]
                        if issues:
                            print(f"\n🚨 {len(issues)} health issues detected - check logs/latest_health_check.json")
                
                if os.path.exists('logs/latest_browser_check.json'):
                    with open('logs/latest_browser_check.json', 'r') as f:
                        browser_data = json.load(f)
                        issues = [r for r in browser_data if r['console_errors'] or r['network_errors']]
                        if issues:
                            print(f"🚨 {len(issues)} browser issues detected - check logs/latest_browser_check.json")
                
                print(f"\n💡 Monitoring active - press Ctrl+C to stop")
                print(f"📁 Logs: logs/health_monitor.log, logs/browser_monitor.log")
                print(f"🌐 Backend: http://localhost:{self.backend_port}")
                print(f"🎨 Frontend: http://localhost:{self.frontend_port}")
                
                await asyncio.sleep(15)  # Update every 15 seconds
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping development workflow...")
        finally:
            self.stop_all_services()

def main():
    parser = argparse.ArgumentParser(description="Automated Development Workflow Manager")
    parser.add_argument("--backend-port", type=int, default=5000, help="Backend port")
    parser.add_argument("--frontend-port", type=int, default=3000, help="Frontend port")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--stop", action="store_true", help="Stop all services")
    
    args = parser.parse_args()
    
    manager = DevWorkflowManager(
        backend_port=args.backend_port,
        frontend_port=args.frontend_port,
        verbose=args.verbose
    )
    
    if args.status:
        manager.display_status()
    elif args.stop:
        manager.stop_all_services()
        print("✅ All services stopped")
    else:
        asyncio.run(manager.run_full_workflow())

if __name__ == "__main__":
    main() 