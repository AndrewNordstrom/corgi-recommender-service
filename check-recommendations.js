// Paste this into the browser console when viewing your timeline
// It will help diagnose why recommendations aren't showing

console.log("🔍 Checking for recommendations in the feed...\n");

// Check for posts in the timeline
const posts = document.querySelectorAll('[role="article"], .status, .post, .timeline-item, article');
console.log(`Found ${posts.length} posts in the timeline`);

// Check for recommendation indicators
let recommendationCount = 0;
const recommendationPosts = [];

posts.forEach((post, index) => {
    // Check various ways a post might be marked as a recommendation
    const checks = {
        hasRecommendationClass: post.classList.contains('post--recommendation') || 
                               post.classList.contains('status--recommendation') ||
                               post.classList.contains('corgi-recommendation'),
        hasRecommendationAttribute: post.hasAttribute('data-corgi-recommendation') ||
                                   post.hasAttribute('data-source') && post.getAttribute('data-source') === 'corgi',
        hasRecommendationBadge: post.querySelector('.recommendation-badge, .recommended-badge, [class*="recommend"]') !== null,
        hasRecommendationText: post.textContent.includes('Recommended') || 
                              post.textContent.includes('For you') ||
                              post.textContent.includes('Suggested')
    };
    
    const isRecommendation = Object.values(checks).some(check => check);
    
    if (isRecommendation) {
        recommendationCount++;
        recommendationPosts.push({
            index,
            element: post,
            checks
        });
    }
});

console.log(`\n📊 Results:`);
console.log(`- Total posts: ${posts.length}`);
console.log(`- Recommendations found: ${recommendationCount}`);
console.log(`- Percentage: ${posts.length > 0 ? (recommendationCount / posts.length * 100).toFixed(1) : 0}%`);

if (recommendationCount > 0) {
    console.log("\n✅ Recommendations detected! Details:");
    recommendationPosts.forEach(rec => {
        console.log(`  Post #${rec.index + 1}:`, rec.checks);
    });
} else {
    console.log("\n❌ No recommendations detected in the UI!");
    console.log("\n🔍 Checking network requests for recommendation API calls...");
    
    // Check performance entries for API calls
    const entries = performance.getEntriesByType('resource');
    const recAPICalls = entries.filter(entry => 
        entry.name.includes('recommendation') || 
        entry.name.includes('/api/v1/timeline')
    );
    
    if (recAPICalls.length > 0) {
        console.log(`\n📡 Found ${recAPICalls.length} recommendation-related API calls:`);
        recAPICalls.forEach(call => {
            console.log(`  - ${call.name} (${call.duration.toFixed(0)}ms)`);
        });
    }
    
    console.log("\n💡 Possible issues:");
    console.log("1. Frontend not adding recommendation markers to posts");
    console.log("2. API returning recommendations but without 'is_recommendation' flag");
    console.log("3. CSS hiding recommendation indicators");
    console.log("4. JavaScript errors preventing proper rendering");
}

// Check for console errors
const consoleErrors = [];
const originalError = console.error;
console.error = function(...args) {
    consoleErrors.push(args);
    originalError.apply(console, args);
};

// Look for Corgi-related messages
console.log("\n📝 Checking for Corgi-related console messages...");
const corgiLogs = [];

// You'll need to check the console manually for these, but here's what to look for:
console.log("\nLook for messages containing:");
console.log("- '[Corgi]'");
console.log("- 'recommendation'");
console.log("- 'offline mode'");
console.log("- 'API connection'");

// Return summary
const summary = {
    totalPosts: posts.length,
    recommendationsFound: recommendationCount,
    recommendationPosts: recommendationPosts.map(r => ({
        index: r.index,
        checks: r.checks
    }))
};

console.log("\n📋 Summary object available as 'recommendationSummary'");
window.recommendationSummary = summary;

console.log("\n✨ Check complete! Scroll up to see full results."); 