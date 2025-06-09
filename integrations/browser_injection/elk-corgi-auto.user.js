// ==UserScript==
// @name         ELK-Corgi Seamless Integration
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Seamlessly integrate Corgi recommendations into ELK timeline
// @author       Corgi Team
// @match        http://localhost:3004/*
// @match        https://elk.zone/*
// @grant        none
// @run-at       document-end
// ==/UserScript==

(function() {
    'use strict';
    
    console.log('🐕 ELK-Corgi Auto Integration Loading...');
    
    const CORGI_API_URL = 'http://localhost:9999';
    let injectionAttempts = 0;
    const MAX_ATTEMPTS = 10;
    
    // Native ELK styling - matches their actual CSS classes
    const ELK_STYLES = {
        post: 'border-b border-border bg-base p-4 hover:bg-muted/25 transition-colors',
        avatar: 'w-12 h-12 rounded-full bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center',
        username: 'font-semibold text-primary',
        handle: 'text-sm text-muted-foreground',
        timestamp: 'text-sm text-muted-foreground',
        content: 'mt-2 text-base leading-relaxed text-foreground',
        actionBar: 'flex items-center justify-between mt-3 pt-2 text-muted-foreground',
        actionButton: 'flex items-center gap-1 p-2 rounded-full hover:bg-muted/50 transition-colors text-sm',
        recommendationBadge: 'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border border-yellow-500/20'
    };
    
    // Wait for ELK to load and inject recommendations
    function waitAndInject() {
        if (injectionAttempts >= MAX_ATTEMPTS) {
            console.log('🔴 Max injection attempts reached');
            return;
        }
        
        injectionAttempts++;
        console.log(`🔄 Injection attempt ${injectionAttempts}/${MAX_ATTEMPTS}`);
        
        // Look for ELK's timeline container
        const timelineContainer = findTimelineContainer();
        
        if (timelineContainer) {
            console.log('✅ Found timeline container, injecting posts...');
            setupCorgiIntegration(timelineContainer);
        } else {
            console.log('⏳ Timeline not ready, retrying in 2 seconds...');
            setTimeout(waitAndInject, 2000);
        }
    }
    
    function findTimelineContainer() {
        // ELK's possible timeline containers
        const selectors = [
            'main [role="feed"]',
            'main .timeline',
            '.status-list',
            'main > div > div > div', // Common nested structure
            'main [class*="space-y"]', // Spaced container
        ];
        
        for (const selector of selectors) {
            const container = document.querySelector(selector);
            if (container && container.offsetHeight > 200) {
                return container;
            }
        }
        
        // Fallback: create container in main
        const main = document.querySelector('main');
        if (main) {
            const container = document.createElement('div');
            container.className = 'corgi-timeline flex-1 space-y-0';
            container.style.cssText = 'flex: 1; min-height: 400px;';
            
            // Insert at the beginning of main content
            const firstChild = main.querySelector('div');
            if (firstChild) {
                firstChild.appendChild(container);
            } else {
                main.appendChild(container);
            }
            return container;
        }
        
        return null;
    }
    
    async function setupCorgiIntegration(container) {
        try {
            // Configure ELK for local API
            localStorage.setItem('corgi_api_url', CORGI_API_URL);
            
            // Fetch recommendations
            const response = await fetch(`${CORGI_API_URL}/api/v1/timelines/home`);
            if (!response.ok) {
                throw new Error(`API returned ${response.status}`);
            }
            
            const posts = await response.json();
            console.log(`📝 Fetched ${posts.length} posts from Corgi API`);
            
            // Clear existing Corgi posts
            container.querySelectorAll('.corgi-post').forEach(post => post.remove());
            
            // Inject posts with native ELK styling
            posts.forEach((post, index) => {
                const postElement = createNativeELKPost(post, index);
                container.appendChild(postElement);
            });
            
            console.log(`🎉 Successfully integrated ${posts.length} recommendations!`);
            
            // Set up auto-refresh every 5 minutes
            setTimeout(() => setupCorgiIntegration(container), 300000);
            
        } catch (error) {
            console.error('❌ Corgi integration error:', error);
            // Retry in 10 seconds
            setTimeout(() => setupCorgiIntegration(container), 10000);
        }
    }
    
    function createNativeELKPost(post, index) {
        const article = document.createElement('article');
        article.className = `corgi-post ${ELK_STYLES.post}`;
        
        // Add subtle recommendation indicator
        if (post.is_recommendation) {
            article.style.borderLeft = '2px solid rgb(234 179 8)'; // yellow-600
            article.style.background = 'linear-gradient(90deg, rgb(254 249 195 / 0.1) 0%, transparent 100%)';
        }
        
        const avatar = post.is_recommendation ? '✨' : '🐕';
        const displayName = post.is_recommendation ? 'Corgi Recommendations' : 'Corgi Feed';
        const handle = '@corgi';
        
        article.innerHTML = `
            <div class="flex gap-3">
                <div class="${ELK_STYLES.avatar}">
                    <span class="text-lg">${avatar}</span>
                </div>
                
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 flex-wrap">
                        <span class="${ELK_STYLES.username}">${displayName}</span>
                        <span class="${ELK_STYLES.handle}">${handle}</span>
                        <span class="${ELK_STYLES.timestamp}">
                            ${new Date(post.created_at || Date.now()).toLocaleTimeString()}
                        </span>
                        ${post.is_recommendation ? `<span class="${ELK_STYLES.recommendationBadge}">✨ Recommended</span>` : ''}
                    </div>
                    
                    <div class="${ELK_STYLES.content}">
                        ${post.content || post.text || 'Recommendation content'}
                    </div>
                    
                    ${post.recommendation_reason ? `
                        <div class="mt-3 p-3 rounded-lg bg-muted/30 border border-border/50">
                            <div class="flex items-start gap-2">
                                <span class="text-yellow-500 mt-0.5">💡</span>
                                <span class="text-sm text-muted-foreground leading-relaxed">
                                    ${post.recommendation_reason}
                                </span>
                            </div>
                        </div>
                    ` : ''}
                    
                    <div class="${ELK_STYLES.actionBar}">
                        <button class="${ELK_STYLES.actionButton} hover:text-blue-500" title="Reply">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
                            </svg>
                            <span>Reply</span>
                        </button>
                        
                        <button class="${ELK_STYLES.actionButton} hover:text-green-500" title="Boost">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                            </svg>
                            <span>Boost</span>
                        </button>
                        
                        <button class="${ELK_STYLES.actionButton} hover:text-red-500" title="Like">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
                            </svg>
                            <span>Like</span>
                        </button>
                        
                        <button class="${ELK_STYLES.actionButton} hover:text-blue-400" title="Share">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z"/>
                            </svg>
                            <span>Share</span>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        return article;
    }
    
    // Add native ELK CSS integration
    const style = document.createElement('style');
    style.textContent = `
        .corgi-post {
            animation: fadeIn 0.3s ease-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .corgi-post button {
            transition: all 0.2s ease;
        }
        
        .corgi-post button:hover svg {
            transform: scale(1.05);
        }
        
        .corgi-post button:active {
            transform: scale(0.95);
        }
    `;
    document.head.appendChild(style);
    
    // Start integration when page loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', waitAndInject);
    } else {
        waitAndInject();
    }
    
    // Re-inject when navigating in SPA
    let lastUrl = location.href;
    new MutationObserver(() => {
        const url = location.href;
        if (url !== lastUrl) {
            lastUrl = url;
            if (url.includes('/home') || url.includes('/timeline')) {
                console.log('🔄 Page navigation detected, re-injecting...');
                injectionAttempts = 0;
                setTimeout(waitAndInject, 1000);
            }
        }
    }).observe(document, {subtree: true, childList: true});
    
})(); 