#!/usr/bin/env python3
"""
Browser Automation Monitor for Frontend Issues

This script uses Selenium to automatically check frontend functionality,
console errors, and network failures - eliminating the need for manual browser checking.
"""

import asyncio
import json
import time
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
import logging
import argparse
from dataclasses import dataclass

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

@dataclass
class BrowserCheckResult:
    page: str
    status: str
    load_time: float
    console_errors: List[str]
    network_errors: List[str]
    timestamp: datetime = None
    screenshot_path: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class BrowserMonitor:
    def __init__(self, 
                 frontend_url: str = None,
                 headless: bool = True,
                 verbose: bool = False):
        # Auto-detect frontend URL from environment variables
        if frontend_url is None:
            elk_port = os.getenv("ELK_PORT", "5314")
            frontend_url = f"http://localhost:{elk_port}"
        self.frontend_url = frontend_url
        self.headless = headless
        self.verbose = verbose
        
        # Setup logging
        log_level = logging.INFO if verbose else logging.WARNING
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('logs/browser_monitor.log', mode='a')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Create directories
        os.makedirs('logs', exist_ok=True)
        os.makedirs('logs/screenshots', exist_ok=True)
        
        # Pages to check
        self.pages_to_check = [
            '/',
            '/corgi',
            '/dashboard',
            '/explore',
            '/metrics',
            '/docs',
        ]
        
        self.driver = None

    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium not available. Install with: pip install selenium")
        
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        # Simple logging setup - avoid complex performance logging for now
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            return True
        except Exception as e:
            self.logger.error(f"Failed to setup Chrome driver: {e}")
            self.logger.error("Make sure Chrome and ChromeDriver are installed")
            return False

    def cleanup_driver(self):
        """Cleanup WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def check_page(self, page_path: str) -> BrowserCheckResult:
        """Check a single page for errors"""
        url = f"{self.frontend_url}{page_path}"
        start_time = time.time()
        
        console_errors = []
        network_errors = []
        status = "✅ HEALTHY"
        screenshot_path = None
        
        try:
            # Navigate to page
            self.driver.get(url)
            
            # Wait for page to load
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                status = "⏱️  LOAD TIMEOUT"
            
            # Get console errors
            console_logs = self.driver.get_log('browser')
            console_errors = [
                f"{log['level']}: {log['message']}" 
                for log in console_logs 
                if log['level'] in ['SEVERE', 'ERROR']
            ]
            
            # Get network errors from performance logs
            try:
                perf_logs = self.driver.get_log('performance')
                for log in perf_logs:
                    message = json.loads(log['message'])
                    if message['message']['method'] == 'Network.responseReceived':
                        response = message['message']['params']['response']
                        if response['status'] >= 400:
                            network_errors.append(f"HTTP {response['status']}: {response['url']}")
            except:
                pass  # Performance logs might not be available
            
            # Check for specific error indicators
            try:
                # Look for common error patterns
                error_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Error') or contains(text(), '404') or contains(text(), '503')]")
                if error_elements:
                    status = "🔴 PAGE ERRORS DETECTED"
                    console_errors.extend([elem.text for elem in error_elements[:3]])  # Limit to first 3
            except:
                pass
            
            # Check if page title indicates an error
            page_title = self.driver.title.lower()
            if any(error_word in page_title for error_word in ['error', '404', '503', 'not found']):
                status = "🔴 ERROR PAGE"
            
            # Take screenshot if there are issues
            if status != 'ok' or console_errors or network_errors:
                try:
                    # Sanitize page name for filename
                    page_name_sanitized = page_path.strip('/').replace('/', '_') or 'home'
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    path = f"logs/screenshots/{page_name_sanitized}_{timestamp}.png"
                    self.driver.save_screenshot(path)
                    screenshot_path = path
                except Exception as e:
                    status = 'error'
                    console_errors.append(f"Screenshot failed: {e}")
            
            # Update status based on errors found
            if console_errors and status == "✅ HEALTHY":
                status = "⚠️  CONSOLE ERRORS"
            if network_errors and status == "✅ HEALTHY":
                status = "🌐 NETWORK ERRORS"
            
        except WebDriverException as e:
            status = "💥 BROWSER ERROR"
            console_errors.append(f"WebDriver error: {str(e)}")
        except Exception as e:
            status = "💥 UNKNOWN ERROR"
            console_errors.append(f"Unknown error: {str(e)}")
        
        load_time = time.time() - start_time
        
        return BrowserCheckResult(
            page=page_path,
            status=status,
            load_time=load_time,
            console_errors=console_errors,
            network_errors=network_errors,
            screenshot_path=screenshot_path
        )

    def check_all_pages(self) -> List[BrowserCheckResult]:
        """Check all configured pages"""
        if not self.setup_driver():
            return []
        
        results = []
        try:
            for page in self.pages_to_check:
                result = self.check_page(page)
                results.append(result)
                
                # Brief pause between checks
                time.sleep(1)
                
        finally:
            self.cleanup_driver()
        
        return results

    def format_results(self, results: List[BrowserCheckResult]) -> str:
        """Format results for display"""
        if not results:
            return "No browser check results available"
        
        lines = []
        lines.append("=" * 80)
        lines.append(f"Browser Check Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        
        for result in results:
            load_time_ms = result.load_time * 1000
            lines.append(f"Page: {result.page:<15} {result.status:<25} ({load_time_ms:.0f}ms)")
            
            if result.console_errors:
                lines.append(f"  Console Errors ({len(result.console_errors)}):")
                for error in result.console_errors[:3]:  # Show first 3
                    lines.append(f"    - {error}")
                if len(result.console_errors) > 3:
                    lines.append(f"    ... and {len(result.console_errors) - 3} more")
            
            if result.network_errors:
                lines.append(f"  Network Errors ({len(result.network_errors)}):")
                for error in result.network_errors[:3]:  # Show first 3
                    lines.append(f"    - {error}")
                if len(result.network_errors) > 3:
                    lines.append(f"    ... and {len(result.network_errors) - 3} more")
            
            if result.screenshot_path:
                lines.append(f"  Screenshot: {result.screenshot_path}")
            
            lines.append("")
        
        return "\n".join(lines)

    async def run_continuous_monitoring(self, interval: int = 30):
        """Run continuous browser monitoring"""
        self.logger.info(f"Starting browser monitoring (interval: {interval}s)")
        self.logger.info(f"Frontend URL: {self.frontend_url}")
        self.logger.info(f"Headless mode: {self.headless}")
        
        try:
            while True:
                results = self.check_all_pages()
                
                # Always show results if there are issues
                has_issues = any(
                    result.status != "✅ HEALTHY" or result.console_errors or result.network_errors
                    for result in results
                )
                
                if has_issues or self.verbose:
                    output = self.format_results(results)
                    print(output)
                    
                    # Save to file for debugging
                    with open('logs/latest_browser_check.json', 'w') as f:
                        json.dump([{
                            'page': r.page,
                            'status': r.status,
                            'load_time': r.load_time,
                            'console_errors': r.console_errors,
                            'network_errors': r.network_errors,
                            'timestamp': r.timestamp.isoformat(),
                            'screenshot_path': r.screenshot_path
                        } for r in results], f, indent=2)
                
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("Browser monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Browser monitoring error: {e}")

def main():
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium not available!")
        print("Install with: pip install selenium")
        print("Also install ChromeDriver: https://chromedriver.chromium.org/")
        sys.exit(1)
    
    # Auto-detect frontend URL from environment variables
    elk_port = os.getenv("ELK_PORT", "5314")
    default_frontend_url = f"http://localhost:{elk_port}"
    
    parser = argparse.ArgumentParser(description="Automated Browser Monitor for Frontend Issues")
    parser.add_argument("--frontend-url", default=default_frontend_url, help="Frontend URL")
    parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode")
    parser.add_argument("--show-browser", action="store_true", help="Show browser window")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    
    monitor = BrowserMonitor(
        frontend_url=args.frontend_url,
        headless=not args.show_browser,
        verbose=args.verbose
    )
    
    if args.once:
        # Run once and exit
        results = monitor.check_all_pages()
        output = monitor.format_results(results)
        print(output)
        
        # Save to file for debugging
        with open('logs/latest_browser_check.json', 'w') as f:
            json.dump([{
                'page': r.page,
                'status': r.status,
                'load_time': r.load_time,
                'console_errors': r.console_errors,
                'network_errors': r.network_errors,
                'timestamp': r.timestamp.isoformat(),
                'screenshot_path': r.screenshot_path
            } for r in results], f, indent=2)
            
        # Exit with error code if any checks failed
        has_issues = any(
            result.status != "✅ HEALTHY" or result.console_errors or result.network_errors
            for result in results
        )
        if has_issues:
            sys.exit(1)
    else:
        # Run continuous monitoring
        asyncio.run(monitor.run_continuous_monitoring(args.interval))

if __name__ == "__main__":
    main() 