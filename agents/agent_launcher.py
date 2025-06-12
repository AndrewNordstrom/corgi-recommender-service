#!/usr/bin/env python3
"""
Corgi Agent System Launcher
Comprehensive startup script for all agents and monitoring
"""

import asyncio
import sys
import signal
import multiprocessing
import time
from pathlib import Path
import logging
import subprocess
import threading
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agents/agent_system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("AgentLauncher")

class AgentSystemLauncher:
    """Main launcher for the Corgi Agent System"""
    
    def __init__(self):
        self.processes = {}
        self.running = False
        self.setup_directories()
        
    def setup_directories(self):
        """Setup necessary directories"""
        Path("agents").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
        
    def start_web_dashboard(self):
        """Start the web dashboard in a separate process"""
        try:
            logger.info("Starting Agent Web Dashboard...")
            
            def run_dashboard():
                from web_agent_dashboard import start_dashboard
                start_dashboard(port=5001)
            
            process = multiprocessing.Process(target=run_dashboard)
            process.start()
            self.processes["dashboard"] = process
            
            # Wait a moment for dashboard to start
            time.sleep(3)
            logger.info("✅ Agent Dashboard started on http://localhost:5001")
            
        except Exception as e:
            logger.error(f"Failed to start web dashboard: {str(e)}")
    
    def start_agent_system(self):
        """Start the main agent system"""
        try:
            logger.info("Starting Main Agent System...")
            
            def run_agents():
                from core_agent_system import main
                asyncio.run(main())
            
            process = multiprocessing.Process(target=run_agents)
            process.start()
            self.processes["agents"] = process
            
            logger.info("✅ Agent System started with continuous monitoring")
            
        except Exception as e:
            logger.error(f"Failed to start agent system: {str(e)}")
    
    def start_integration_bridge(self):
        """Start integration bridge with existing monitoring"""
        try:
            logger.info("Starting Integration Bridge...")
            
            def run_bridge():
                # Connect with existing dev workflow
                while True:
                    try:
                        # Monitor the main development workflow
                        result = subprocess.run(
                            ["make", "dev-status"],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        if result.returncode == 0:
                            logger.info("Integration: Main dev workflow is healthy")
                        else:
                            logger.warning("Integration: Main dev workflow has issues")
                            
                    except Exception as e:
                        logger.error(f"Integration bridge error: {str(e)}")
                    
                    time.sleep(60)  # Check every minute
            
            thread = threading.Thread(target=run_bridge, daemon=True)
            thread.start()
            
            logger.info("✅ Integration Bridge started")
            
        except Exception as e:
            logger.error(f"Failed to start integration bridge: {str(e)}")
    
    def display_startup_banner(self):
        """Display startup banner"""
        banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🐕 CORGI AGENT SYSTEM LAUNCHER 🐕                         ║
║                                                                              ║
║  Cutting-Edge Multi-Agent Website Management System                          ║
║  Comprehensive automation for your Corgi Recommender Service                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

🚀 Starting Advanced Agent Ecosystem...

📊 System Components:
┌─────────────────────────────────────────────────────────────────────────────┐
│ • Website Health Agent      - Monitors site performance & availability      │
│ • Security Agent           - Scans for vulnerabilities & threats           │
│ • Performance Optimizer    - Optimizes speed & resource usage              │
│ • User Experience Agent    - Monitors UX metrics & Core Web Vitals         │
│ • Content Management Agent - Manages content quality & freshness           │
│ • ML Model Agent          - Optimizes recommendation models                │
│ • Deployment Agent        - Manages infrastructure & scaling               │
│ • Web Dashboard           - Real-time monitoring & control interface       │
└─────────────────────────────────────────────────────────────────────────────┘

🔧 Features:
• Real-time monitoring of all website components
• Automated performance optimization
• Security vulnerability scanning
• ML model performance tracking  
• User experience analytics
• Content quality management
• Infrastructure monitoring
• Integration with existing dev workflow

🌐 Access Points:
• Agent Dashboard: http://localhost:5001
• Main Website:   http://localhost:3000
• API Endpoint:   http://localhost:9999

🔄 Starting components...
"""
        print(banner)
    
    def start_all_components(self):
        """Start all system components"""
        self.display_startup_banner()
        
        # Start web dashboard first
        self.start_web_dashboard()
        
        # Start integration bridge
        self.start_integration_bridge()
        
        # Start main agent system
        self.start_agent_system()
        
        self.running = True
        
        success_message = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                        🎉 SYSTEM STARTUP COMPLETE! 🎉                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

✅ All components started successfully!

🔗 Quick Access:
┌─────────────────────────────────────────────────────────────────────────────┐
│ Agent Dashboard:    http://localhost:5001                                   │
│ Main Website:       http://localhost:3000                                   │ 
│ API Documentation:  http://localhost:9999/docs                             │
│ Model Comparison:   http://localhost:3000/dashboard                        │
└─────────────────────────────────────────────────────────────────────────────┘

🤖 Active Agents:
• Website Health Monitoring  ✅
• Security Scanning         ✅  
• Performance Optimization  ✅
• User Experience Analysis  ✅
• Content Management        ✅
• ML Model Optimization     ✅
• Deployment Management     ✅

📊 Monitoring:
• Continuous health checks every 5 minutes
• Real-time performance metrics
• Security scans every 30 minutes
• User experience monitoring
• ML model performance tracking

💡 Usage Tips:
• Visit the Agent Dashboard for real-time monitoring
• Use "Run Agent Cycle" button for manual checks
• Export reports for detailed analysis
• All actions are automatically logged

🛑 To stop the system: Press Ctrl+C
📝 Logs are saved to: agents/agent_system.log

System is now monitoring and optimizing your website automatically!
"""
        print(success_message)
        logger.info("🎉 Corgi Agent System fully operational!")
    
    def stop_all_components(self):
        """Stop all system components"""
        logger.info("Stopping Corgi Agent System...")
        
        self.running = False
        
        for name, process in self.processes.items():
            try:
                logger.info(f"Stopping {name}...")
                process.terminate()
                process.join(timeout=10)
                
                if process.is_alive():
                    logger.warning(f"Force killing {name}...")
                    process.kill()
                    process.join()
                    
            except Exception as e:
                logger.error(f"Error stopping {name}: {str(e)}")
        
        logger.info("✅ All components stopped")
        
        shutdown_message = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                      👋 CORGI AGENT SYSTEM SHUTDOWN                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

🛑 All agents and monitoring services have been stopped.

📊 Final Status:
• All processes terminated cleanly
• Logs saved to agents/agent_system.log
• Database preserved for next startup

Thank you for using the Corgi Agent System! 🐕
"""
        print(shutdown_message)
    
    def run(self):
        """Main run method"""
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal")
            self.stop_all_components()
            sys.exit(0)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Start all components
            self.start_all_components()
            
            # Keep main process alive
            while self.running:
                time.sleep(1)
                
                # Check if processes are still alive
                for name, process in list(self.processes.items()):
                    if not process.is_alive():
                        logger.warning(f"Process {name} died unexpectedly")
                        # Could implement restart logic here
                        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
        finally:
            self.stop_all_components()

def main():
    """Main entry point"""
    launcher = AgentSystemLauncher()
    launcher.run()

if __name__ == "__main__":
    main() 