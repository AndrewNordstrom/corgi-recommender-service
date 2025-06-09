#!/usr/bin/env python3
"""
Simple script to check if recommendations are showing in ELK
Run this AFTER you're already logged in to ELK
"""

import asyncio
from playwright.async_api import async_playwright
import json
import time

async def check_recommendations():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Collect console messages
        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg))
        
        print("🔍 Opening ELK at localhost:3004...")
        await page.goto("http://localhost:3004", wait_until="networkidle")
        
        print("⏳ Waiting for timeline to load...")
        await page.wait_for_timeout(3000)
        
        # Check if we're logged in by looking for timeline posts
        posts = await page.locator('[role="article"], article, .status').count()
        
        if posts == 0:
            print("❌ No posts found - you need to be logged in first!")
            print("Please log in manually and run this script again.")
            await browser.close()
            return
        
        print(f"✅ Found {posts} posts in timeline")
        
        # Check console for Corgi messages
        corgi_messages = [msg for msg in console_messages if "[Corgi]" in msg.text or "recommendation" in msg.text.lower()]
        
        if corgi_messages:
            print(f"\n📝 Found {len(corgi_messages)} Corgi-related console messages:")
            for msg in corgi_messages[:5]:
                print(f"  - {msg.text}")
        
        # Check for recommendations in the DOM
        print("\n🔍 Checking for recommendation markers...")
        
        # Execute JavaScript to check for recommendations
        result = await page.evaluate("""
            () => {
                const posts = document.querySelectorAll('[role="article"], article, .status');
                let recCount = 0;
                const details = [];
                
                posts.forEach((post, i) => {
                    const hasRecClass = post.className.includes('recommendation');
                    const hasRecAttr = post.hasAttribute('data-corgi-recommendation');
                    const hasRecBadge = post.querySelector('.recommendation-badge') !== null;
                    const hasRecText = post.textContent.includes('Recommended') || post.textContent.includes('For you');
                    
                    if (hasRecClass || hasRecAttr || hasRecBadge || hasRecText) {
                        recCount++;
                        details.push({
                            index: i,
                            hasClass: hasRecClass,
                            hasAttr: hasRecAttr,
                            hasBadge: hasRecBadge,
                            hasText: hasRecText
                        });
                    }
                });
                
                return {
                    totalPosts: posts.length,
                    recommendationCount: recCount,
                    details: details
                };
            }
        """)
        
        print(f"\n📊 Results:")
        print(f"  - Total posts: {result['totalPosts']}")
        print(f"  - Recommendations found: {result['recommendationCount']}")
        
        if result['recommendationCount'] > 0:
            print("\n✅ Recommendations detected! Details:")
            for rec in result['details'][:3]:
                print(f"  Post #{rec['index'] + 1}:")
                print(f"    - Has recommendation class: {rec['hasClass']}")
                print(f"    - Has data attribute: {rec['hasAttr']}")
                print(f"    - Has badge: {rec['hasBadge']}")
                print(f"    - Has text indicator: {rec['hasText']}")
        else:
            print("\n❌ No recommendations found in the UI!")
            
            # Check Network tab data
            print("\n🔍 Checking for API calls...")
            resources = await page.evaluate("""
                () => {
                    const entries = performance.getEntriesByType('resource');
                    return entries
                        .filter(e => e.name.includes('9999') || e.name.includes('recommendation'))
                        .map(e => e.name);
                }
            """)
            
            if resources:
                print("Found API calls:")
                for url in resources:
                    print(f"  - {url}")
            
            # Take a screenshot
            timestamp = int(time.time())
            screenshot_path = f"logs/screenshots/rec_check_{timestamp}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"\n📸 Screenshot saved to: {screenshot_path}")
            
            print("\n💡 Possible issues:")
            print("  1. API not returning 'is_recommendation' field")
            print("  2. Frontend not adding markers to recommended posts")
            print("  3. Recommendations mixed with regular posts without distinction")
            print("  4. Check the screenshot to see what's actually displayed")
        
        # Keep browser open for manual inspection
        print("\n🔎 Browser will stay open for 30 seconds for manual inspection...")
        print("Press Ctrl+C to close earlier")
        
        try:
            await asyncio.sleep(30)
        except KeyboardInterrupt:
            pass
        
        await browser.close()

if __name__ == "__main__":
    print("🚀 ELK Recommendation Checker")
    print("="*50)
    print("Make sure you're already logged in to ELK before running this!")
    print("="*50)
    
    asyncio.run(check_recommendations()) 