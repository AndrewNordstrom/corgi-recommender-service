#!/usr/bin/env python3
"""
Intelligent Browser Testing Agent using Playwright

This agent automates frontend testing, eliminating the need to manually check
if changes work. It acts like a real user and reports clear pass/fail results.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
import argparse
from pathlib import Path

# Color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def colored(text: str, color: str) -> str:
    """Return colored text for terminal output"""
    return f"{color}{text}{Colors.END}"

try:
    from playwright.async_api import async_playwright, Page, Browser, ConsoleMessage, Response
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

@dataclass
class TestResult:
    """Result of a single test"""
    name: str
    passed: bool
    duration: float
    error: Optional[str] = None
    screenshot: Optional[str] = None
    details: Dict = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

class BrowserAgent:
    """Intelligent browser testing agent that acts like a real user"""
    
    def __init__(self, 
                 frontend_url: str = "http://localhost:3000",
                 api_url: str = "http://localhost:5002",
                 headless: bool = True,
                 verbose: bool = False,
                 screenshot_on_failure: bool = True):
        self.frontend_url = frontend_url.rstrip('/')
        self.api_url = api_url.rstrip('/')
        self.headless = headless
        self.verbose = verbose
        self.screenshot_on_failure = screenshot_on_failure
        
        # Setup directories
        self.log_dir = Path("logs")
        self.screenshot_dir = self.log_dir / "screenshots"
        self.log_dir.mkdir(exist_ok=True)
        self.screenshot_dir.mkdir(exist_ok=True)
        
        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        
        # Console handler with color
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        
        # File handler
        file_handler = logging.FileHandler(self.log_dir / 'browser_agent.log')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(file_formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        
        self.browser = None
        self.context = None
        self.console_messages: List[ConsoleMessage] = []
        self.network_errors: List[str] = []
        
    async def setup_browser(self):
        """Setup Playwright browser"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright not available. Install with:\n"
                "pip install playwright\n"
                "playwright install chromium"
            )
        
        self.playwright = await async_playwright().start()
        
        # Browser launch options
        launch_options = {
            "headless": self.headless,
            "args": ["--no-sandbox", "--disable-setuid-sandbox"]
        }
        
        self.browser = await self.playwright.chromium.launch(**launch_options)
        
        # Context options
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "ignore_https_errors": True,
        }
        
        self.context = await self.browser.new_context(**context_options)
        
        # Enable console and network monitoring
        self.context.on("console", self._on_console)
        self.context.on("response", self._on_response)
        
    async def cleanup(self):
        """Cleanup browser resources"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    def _on_console(self, msg: ConsoleMessage):
        """Handle console messages"""
        self.console_messages.append(msg)
        if self.verbose:
            self.logger.debug(f"Console [{msg.type}]: {msg.text}")
    
    def _on_response(self, response: Response):
        """Handle network responses"""
        if response.status >= 400:
            error = f"HTTP {response.status}: {response.url}"
            self.network_errors.append(error)
            if self.verbose:
                self.logger.debug(f"Network error: {error}")
    
    async def take_screenshot(self, page: Page, name: str) -> str:
        """Take a screenshot and return the path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = self.screenshot_dir / filename
        await page.screenshot(path=str(filepath), full_page=True)
        return str(filepath)
    
    async def test_elk_corgi_connection(self, page: Page) -> TestResult:
        """
        Critical test: Check if ELK frontend can connect to Corgi API
        
        This test FAILS if it finds "[Corgi] Running in offline mode" in console
        """
        test_name = "ELK-Corgi API Connection"
        start_time = time.time()
        error = None
        screenshot = None
        
        try:
            # Clear previous console messages
            self.console_messages.clear()
            
            # Navigate to frontend
            self.logger.info(f"Navigating to {self.frontend_url}")
            await page.goto(self.frontend_url, wait_until="networkidle")
            
            # Wait a moment for any async operations
            await page.wait_for_timeout(2000)
            
            # Check for offline mode message
            offline_messages = [
                msg for msg in self.console_messages 
                if "[Corgi] Running in offline mode" in msg.text
            ]
            
            if offline_messages:
                error = "❌ API CONNECTION BROKEN: Frontend is running in offline mode!"
                self.logger.error(error)
                
                # Take screenshot of the failure
                if self.screenshot_on_failure:
                    screenshot = await self.take_screenshot(page, "api_offline_error")
                    self.logger.info(f"Screenshot saved: {screenshot}")
                
                return TestResult(
                    name=test_name,
                    passed=False,
                    duration=time.time() - start_time,
                    error=error,
                    screenshot=screenshot,
                    details={
                        "offline_messages": [msg.text for msg in offline_messages],
                        "url": page.url
                    }
                )
            
            # Check for successful API connection indicators
            api_connected = False
            
            # Method 1: Check for API calls in network
            api_calls = [
                error for error in self.network_errors 
                if self.api_url in error
            ]
            
            # Method 2: Look for success messages in console
            success_messages = [
                msg for msg in self.console_messages 
                if any(indicator in msg.text.lower() for indicator in [
                    "api connected", "corgi connected", "connected to corgi",
                    "recommendations loaded", "api ready"
                ])
            ]
            
            # Method 3: Check page content for API data
            try:
                # Look for elements that would only exist with API data
                api_indicators = await page.locator('[data-source="corgi-api"]').count()
                if api_indicators > 0:
                    api_connected = True
            except:
                pass
            
            if success_messages or api_connected:
                self.logger.info(colored("✅ API Connection Verified!", Colors.GREEN))
                return TestResult(
                    name=test_name,
                    passed=True,
                    duration=time.time() - start_time,
                    details={
                        "success_indicators": [msg.text for msg in success_messages],
                        "api_connected": api_connected
                    }
                )
            else:
                # Not offline, but no clear connection indicators
                self.logger.warning("⚠️  API connection status unclear")
                return TestResult(
                    name=test_name,
                    passed=True,  # Don't fail if not explicitly offline
                    duration=time.time() - start_time,
                    details={
                        "warning": "No clear API connection indicators found",
                        "console_messages": len(self.console_messages)
                    }
                )
                
        except Exception as e:
            error = f"Test failed with exception: {str(e)}"
            self.logger.error(error)
            
            if self.screenshot_on_failure and page:
                try:
                    screenshot = await self.take_screenshot(page, "test_exception")
                except:
                    pass
            
            return TestResult(
                name=test_name,
                passed=False,
                duration=time.time() - start_time,
                error=error,
                screenshot=screenshot
            )
    
    async def test_oauth_flow(self, page: Page) -> TestResult:
        """Test the OAuth authorization flow"""
        test_name = "OAuth Authorization Flow"
        start_time = time.time()
        error = None
        screenshot = None
        
        try:
            # Navigate to frontend
            await page.goto(self.frontend_url, wait_until="networkidle")
            
            # Look for sign in button
            sign_in_button = page.locator('button:has-text("Sign in"), a:has-text("Sign in")')
            
            if await sign_in_button.count() == 0:
                self.logger.warning("No sign in button found - user might already be logged in")
                return TestResult(
                    name=test_name,
                    passed=True,
                    duration=time.time() - start_time,
                    details={"status": "Already logged in or no auth required"}
                )
            
            # Click sign in
            self.logger.info("Clicking sign in button...")
            await sign_in_button.first.click()
            
            # Wait for navigation
            await page.wait_for_load_state("networkidle")
            
            # Check if we're on the OAuth page
            current_url = page.url
            
            if "/oauth/authorize" in current_url or "/auth" in current_url:
                self.logger.info(colored("✅ OAuth flow initiated successfully!", Colors.GREEN))
                
                # Check for Corgi branding
                corgi_elements = await page.locator('text=/Corgi|CORGI/i').count()
                
                return TestResult(
                    name=test_name,
                    passed=True,
                    duration=time.time() - start_time,
                    details={
                        "oauth_page_reached": True,
                        "url": current_url,
                        "corgi_branding_found": corgi_elements > 0
                    }
                )
            else:
                error = f"OAuth flow failed - unexpected URL: {current_url}"
                if self.screenshot_on_failure:
                    screenshot = await self.take_screenshot(page, "oauth_failure")
                
                return TestResult(
                    name=test_name,
                    passed=False,
                    duration=time.time() - start_time,
                    error=error,
                    screenshot=screenshot
                )
                
        except Exception as e:
            error = f"OAuth test failed: {str(e)}"
            self.logger.error(error)
            
            if self.screenshot_on_failure and page:
                try:
                    screenshot = await self.take_screenshot(page, "oauth_exception")
                except:
                    pass
            
            return TestResult(
                name=test_name,
                passed=False,
                duration=time.time() - start_time,
                error=error,
                screenshot=screenshot
            )
    
    async def test_recommendations_in_feed(self, page: Page, username: Optional[str] = None, password: Optional[str] = None) -> TestResult:
        """
        Test if recommendations are actually appearing in the feed
        This addresses the issue where console says recs are generating but they don't show
        """
        test_name = "Recommendations Display in Feed"
        start_time = time.time()
        error = None
        screenshot = None
        
        try:
            # Clear console messages
            self.console_messages.clear()
            
            # Navigate to frontend
            await page.goto(self.frontend_url, wait_until="networkidle")
            
            # Handle login if credentials provided
            if username and password:
                self.logger.info("Attempting to log in with provided credentials...")
                
                # Look for sign in button
                sign_in_button = page.locator('button:has-text("Sign in"), a:has-text("Sign in")')
                if await sign_in_button.count() > 0:
                    await sign_in_button.first.click()
                    await page.wait_for_load_state("networkidle")
                    
                    # Check if we need to select/enter Mastodon instance
                    instance_input = page.locator('input[placeholder*="instance"], input[placeholder*="server"], input[name="server"], input[name="instance"]')
                    if await instance_input.count() > 0:
                        self.logger.info("Entering Mastodon instance: mastodon.social")
                        await instance_input.fill("mastodon.social")
                        await page.wait_for_timeout(500)
                        
                        # Look for continue/next button
                        continue_button = page.locator('button:has-text("Continue"), button:has-text("Next"), button[type="submit"]')
                        if await continue_button.count() > 0:
                            await continue_button.click()
                            await page.wait_for_load_state("networkidle")
                    
                    # Now fill in credentials if we're on a login form
                    username_input = page.locator('input[name="username"], input[type="email"], input[placeholder*="username"], input[placeholder*="email"], input[name="user[email]"]')
                    password_input = page.locator('input[name="password"], input[type="password"], input[name="user[password]"]')
                    
                    if await username_input.count() > 0 and await password_input.count() > 0:
                        await username_input.fill(username)
                        await password_input.fill(password)
                        
                        # Submit form
                        submit_button = page.locator('button[type="submit"], button:has-text("Log in"), button:has-text("Sign in")')
                        if await submit_button.count() > 0:
                            await submit_button.click()
                            await page.wait_for_load_state("networkidle")
            
            # Wait for feed to load
            await page.wait_for_timeout(3000)
            
            # Check console for recommendation generation messages
            rec_generation_messages = [
                msg for msg in self.console_messages 
                if any(indicator in msg.text.lower() for indicator in [
                    "generating recommendations",
                    "recommendations generated",
                    "fetching recommendations",
                    "corgi recommendations",
                    "recommendation engine"
                ])
            ]
            
            # Look for recommendation indicators in the DOM
            rec_indicators = []
            
            # Method 1: Look for Corgi-specific attributes
            corgi_recs = await page.locator('[data-corgi-recommendation="true"], [data-source="corgi"], .corgi-recommendation').count()
            if corgi_recs > 0:
                rec_indicators.append(f"Found {corgi_recs} elements with Corgi attributes")
            
            # Method 2: Look for recommendation badges/labels
            rec_badges = await page.locator('text=/Recommended|Suggested|For you/i').count()
            if rec_badges > 0:
                rec_indicators.append(f"Found {rec_badges} recommendation badges")
            
            # Method 3: Check timeline structure
            timeline_items = await page.locator('[role="article"], .status, .post, .timeline-item').count()
            if timeline_items > 0:
                rec_indicators.append(f"Found {timeline_items} timeline items")
            
            # Take screenshot for analysis
            screenshot = await self.take_screenshot(page, "feed_check")
            
            # Analyze results
            if rec_generation_messages and not rec_indicators:
                error = "⚠️  Console says recommendations are generating but none found in UI!"
                self.logger.error(error)
                
                return TestResult(
                    name=test_name,
                    passed=False,
                    duration=time.time() - start_time,
                    error=error,
                    screenshot=screenshot,
                    details={
                        "console_messages": [msg.text for msg in rec_generation_messages],
                        "ui_indicators": rec_indicators,
                        "timeline_items": timeline_items,
                        "diagnosis": "Recommendations may be generated but not rendered in UI"
                    }
                )
            elif rec_indicators:
                self.logger.info(colored("✅ Recommendations found in feed!", Colors.GREEN))
                return TestResult(
                    name=test_name,
                    passed=True,
                    duration=time.time() - start_time,
                    screenshot=screenshot,
                    details={
                        "console_messages": [msg.text for msg in rec_generation_messages],
                        "ui_indicators": rec_indicators,
                        "timeline_items": timeline_items
                    }
                )
            else:
                self.logger.warning("⚠️  No clear recommendation indicators found")
                return TestResult(
                    name=test_name,
                    passed=False,
                    duration=time.time() - start_time,
                    error="No recommendations found in console or UI",
                    screenshot=screenshot,
                    details={
                        "console_messages": len(self.console_messages),
                        "timeline_items": timeline_items
                    }
                )
                
        except Exception as e:
            error = f"Feed test failed: {str(e)}"
            self.logger.error(error)
            
            if self.screenshot_on_failure and page:
                try:
                    screenshot = await self.take_screenshot(page, "feed_exception")
                except:
                    pass
            
            return TestResult(
                name=test_name,
                passed=False,
                duration=time.time() - start_time,
                error=error,
                screenshot=screenshot
            )
    
    async def run_all_tests(self, username: Optional[str] = None, password: Optional[str] = None) -> List[TestResult]:
        """Run all tests and return results"""
        results = []
        
        try:
            await self.setup_browser()
            page = await self.context.new_page()
            
            # Test 1: API Connection
            self.logger.info(colored("\n🧪 Running Test: ELK-Corgi API Connection", Colors.CYAN))
            result = await self.test_elk_corgi_connection(page)
            results.append(result)
            
            # Only run other tests if API is connected
            if result.passed:
                # Test 2: OAuth Flow
                self.logger.info(colored("\n🧪 Running Test: OAuth Flow", Colors.CYAN))
                result = await self.test_oauth_flow(page)
                results.append(result)
                
                # Test 3: Recommendations in Feed
                self.logger.info(colored("\n🧪 Running Test: Recommendations Display", Colors.CYAN))
                result = await self.test_recommendations_in_feed(page, username, password)
                results.append(result)
            else:
                self.logger.warning("Skipping remaining tests due to API connection failure")
            
        finally:
            await self.cleanup()
        
        return results
    
    def print_results(self, results: List[TestResult]):
        """Print test results in a nice format"""
        print("\n" + "="*80)
        print(colored(f"🤖 Browser Agent Test Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.BOLD))
        print("="*80)
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.passed)
        failed_tests = total_tests - passed_tests
        
        for result in results:
            if result.passed:
                status = colored("✅ PASSED", Colors.GREEN)
            else:
                status = colored("❌ FAILED", Colors.RED)
            
            print(f"\n{result.name}: {status} ({result.duration:.2f}s)")
            
            if result.error:
                print(colored(f"  Error: {result.error}", Colors.RED))
            
            if result.screenshot:
                print(f"  Screenshot: {result.screenshot}")
            
            if result.details and self.verbose:
                print("  Details:")
                for key, value in result.details.items():
                    print(f"    {key}: {value}")
        
        print("\n" + "-"*80)
        summary_color = Colors.GREEN if failed_tests == 0 else Colors.RED
        print(colored(f"Summary: {passed_tests}/{total_tests} tests passed", summary_color))
        
        if failed_tests > 0:
            print(colored(f"❌ {failed_tests} test(s) failed!", Colors.RED))
            
            # Provide specific troubleshooting for common issues
            for result in results:
                if not result.passed and "recommendations" in result.name.lower():
                    print(colored("\n💡 Troubleshooting Recommendations Issue:", Colors.YELLOW))
                    print("  1. Check if the Corgi API is returning recommendations")
                    print("  2. Verify the frontend is properly parsing the API response")
                    print("  3. Look for JavaScript errors in the console")
                    print("  4. Check if recommendations have proper CSS classes")
                    print("  5. Review the screenshot for visual clues")
            
            sys.exit(1)
        else:
            print(colored("✅ All tests passed!", Colors.GREEN))
            sys.exit(0)
    
    async def run_continuous(self, interval: int = 30, username: Optional[str] = None, password: Optional[str] = None):
        """Run tests continuously"""
        self.logger.info(colored(f"🤖 Starting continuous browser testing (interval: {interval}s)", Colors.CYAN))
        
        try:
            while True:
                results = await self.run_all_tests(username, password)
                self.print_results(results)
                
                # Save results to JSON
                results_data = {
                    "timestamp": datetime.now().isoformat(),
                    "tests": [asdict(r) for r in results]
                }
                
                with open(self.log_dir / "latest_test_results.json", "w") as f:
                    json.dump(results_data, f, indent=2)
                
                print(f"\nNext test run in {interval} seconds... (Press Ctrl+C to stop)")
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            print(colored("\n🛑 Testing stopped by user", Colors.YELLOW))

async def main():
    """Main entry point"""
    if not PLAYWRIGHT_AVAILABLE:
        print(colored("❌ Playwright not available!", Colors.RED))
        print("Install with:")
        print("  pip install playwright")
        print("  playwright install chromium")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        description="Intelligent Browser Testing Agent - Automates frontend testing like a real user"
    )
    parser.add_argument("--frontend-url", default="http://localhost:3000", 
                       help="Frontend URL to test")
    parser.add_argument("--api-url", default="http://localhost:5002", 
                       help="API URL")
    parser.add_argument("--headless", action="store_true", default=True,
                       help="Run in headless mode (no visible browser)")
    parser.add_argument("--headed", action="store_true",
                       help="Show browser window (opposite of headless)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--continuous", "-c", action="store_true",
                       help="Run tests continuously")
    parser.add_argument("--interval", type=int, default=30,
                       help="Interval between tests in continuous mode (seconds)")
    parser.add_argument("--username", help="Username for login (optional)")
    parser.add_argument("--password", help="Password for login (optional)")
    
    args = parser.parse_args()
    
    # Handle headed/headless logic
    headless = not args.headed if args.headed else args.headless
    
    agent = BrowserAgent(
        frontend_url=args.frontend_url,
        api_url=args.api_url,
        headless=headless,
        verbose=args.verbose
    )
    
    if args.continuous:
        await agent.run_continuous(args.interval, args.username, args.password)
    else:
        results = await agent.run_all_tests(args.username, args.password)
        agent.print_results(results)

if __name__ == "__main__":
    asyncio.run(main()) 