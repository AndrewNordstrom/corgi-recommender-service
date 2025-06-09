// ==UserScript==
// @name         Corgi ELK Seamless Integration
// @namespace    http://corgi-recommender.com/
// @version      1.0
// @description  Seamlessly integrate Corgi recommendations into ELK timelines
// @author       Corgi Team
// @match        http://localhost:3000/*
// @match        http://localhost:3004/*
// @match        https://elk.zone/*
// @grant        none
// ==/UserScript==

/**
 * Seamless ELK-Corgi Integration for Browser Extension
 * 
 * This script automatically detects and styles recommendation posts in ELK
 * to provide a seamless user experience where recommendations appear natively
 * in the timeline without users realizing it's a separate system.
 */

(function() {
    'use strict';
    
    // Configuration
    const CORGI_API_URL = 'http://localhost:9999';
    const DEBUG = false;
    
    // Utility functions
    function log(message, ...args) {
        if (DEBUG) {
            console.log(`[Corgi] ${message}`, ...args);
        }
    }
    
    function error(message, ...args) {
        console.error(`[Corgi] ${message}`, ...args);
    }
    
    // Enhanced CSS for seamless recommendation styling
    const corgiStyles = `
    <style id="corgi-recommendation-styles">
    /* Subtle glow for recommendation posts */
    .corgi-recommendation {
      position: relative;
      background: linear-gradient(135deg, rgba(255, 193, 7, 0.03) 0%, rgba(255, 235, 59, 0.02) 100%);
      border-left: 3px solid #ffc107;
      box-shadow: 0 2px 8px rgba(255, 193, 7, 0.1);
      transition: all 0.3s ease;
      border-radius: 12px;
      margin: 8px 0;
    }
    
    .corgi-recommendation:hover {
      background: linear-gradient(135deg, rgba(255, 193, 7, 0.05) 0%, rgba(255, 235, 59, 0.03) 100%);
      box-shadow: 0 4px 12px rgba(255, 193, 7, 0.15);
    }
    
    /* Subtle recommendation badge */
    .corgi-rec-badge {
      position: absolute;
      top: 8px;
      right: 12px;
      background: linear-gradient(135deg, #ffc107 0%, #ffb300 100%);
      color: rgba(0, 0, 0, 0.8);
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 12px;
      z-index: 10;
      box-shadow: 0 2px 6px rgba(255, 193, 7, 0.25);
      animation: corgiGlow 2s ease-in-out infinite alternate;
      cursor: help;
    }
    
    @keyframes corgiGlow {
      from { box-shadow: 0 2px 6px rgba(255, 193, 7, 0.25); }
      to { box-shadow: 0 2px 10px rgba(255, 193, 7, 0.4); }
    }
    
    /* ELK-specific selectors for different post containers */
    .status-wrapper.corgi-recommendation,
    .status.corgi-recommendation,
    .timeline-item.corgi-recommendation,
    article.corgi-recommendation {
      border-radius: 12px;
      margin: 8px 0;
    }
    
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
      .corgi-recommendation {
        background: linear-gradient(135deg, rgba(255, 193, 7, 0.08) 0%, rgba(255, 235, 59, 0.04) 100%);
        border-left-color: #ffb300;
      }
      
      .corgi-rec-badge {
        background: linear-gradient(135deg, #ffb300 0%, #ffa000 100%);
        color: rgba(0, 0, 0, 0.9);
      }
    }
    
    /* Fade-in animation for newly enhanced posts */
    .corgi-recommendation.corgi-new {
      animation: corgiEnhanceIn 0.5s ease-out;
    }
    
    @keyframes corgiEnhanceIn {
      from { 
        background: linear-gradient(135deg, rgba(255, 193, 7, 0.1) 0%, rgba(255, 235, 59, 0.08) 100%);
        border-left-width: 5px;
      }
      to { 
        background: linear-gradient(135deg, rgba(255, 193, 7, 0.03) 0%, rgba(255, 235, 59, 0.02) 100%);
        border-left-width: 3px;
      }
    }
    </style>
    `;
    
    // Inject styles
    function injectStyles() {
        if (!document.getElementById('corgi-recommendation-styles')) {
            document.head.insertAdjacentHTML('beforeend', corgiStyles);
            log('Styles injected successfully');
        }
    }
    
    // Enhanced post detection and styling
    function enhancePostsWithRecommendations() {
        // Multiple selectors to catch different ELK DOM structures
        const postSelectors = [
            '[data-post-id]',
            '.status-wrapper',
            '.status',
            '.timeline-item',
            'article[role="article"]',
            '.notification-list-item',
            '.conversation-thread .status',
            'article[data-test="status"]',
            '[data-testid="status"]'
        ];
        
        let postsFound = 0;
        let recsFound = 0;
        let newRecsFound = 0;
        
        postSelectors.forEach(selector => {
            const posts = document.querySelectorAll(selector);
            
            posts.forEach(post => {
                if (post.hasAttribute('data-corgi-enhanced')) return;
                
                postsFound++;
                
                // Look for recommendation indicators in the post content or data
                const isRecommendation = checkIfRecommendation(post);
                
                if (isRecommendation) {
                    recsFound++;
                    newRecsFound++;
                    
                    // Add subtle styling with fade-in animation
                    post.classList.add('corgi-recommendation', 'corgi-new');
                    
                    // Remove the new class after animation
                    setTimeout(() => {
                        post.classList.remove('corgi-new');
                    }, 500);
                    
                    // Add recommendation badge
                    if (!post.querySelector('.corgi-rec-badge')) {
                        const badge = document.createElement('div');
                        badge.className = 'corgi-rec-badge';
                        badge.textContent = '✨ Recommended';
                        badge.title = 'This post was recommended by Corgi AI based on your interests';
                        
                        // Find the best position to insert the badge
                        const insertPosition = findBestInsertPosition(post);
                        insertPosition.appendChild(badge);
                    }
                    
                    log('Enhanced recommendation post:', post);
                }
                
                post.setAttribute('data-corgi-enhanced', 'true');
            });
        });
        
        if (newRecsFound > 0) {
            log(`✨ Enhanced ${newRecsFound} new recommendation posts (${recsFound} total) out of ${postsFound} posts`);
        }
    }
    
    // Smart detection of recommendation posts
    function checkIfRecommendation(post) {
        // Method 1: Check for data attributes that might indicate recommendations
        const dataAttrs = ['data-is-recommendation', 'data-recommended', 'data-corgi-rec'];
        for (const attr of dataAttrs) {
            if (post.hasAttribute(attr) && post.getAttribute(attr) === 'true') {
                return true;
            }
        }
        
        // Method 2: Check for recommendation-related text content
        const textContent = post.textContent.toLowerCase();
        const recIndicators = [
            'recommended for you',
            'you might like',
            'similar to posts you',
            'because you liked',
            'trending in your network',
            'suggested content we think you might find interesting'
        ];
        
        if (recIndicators.some(indicator => textContent.includes(indicator))) {
            return true;
        }
        
        // Method 3: Check for JSON data that might contain recommendation info
        try {
            const scriptTags = post.querySelectorAll('script[type="application/json"]');
            for (const script of scriptTags) {
                const data = JSON.parse(script.textContent);
                if (data.is_recommendation === true || data.isRecommendation === true) {
                    return true;
                }
            }
        } catch (e) {
            // Ignore JSON parsing errors
        }
        
        // Method 4: Check for specific CSS classes that might indicate recommendations
        const recClasses = ['recommendation', 'suggested', 'recommended', 'enhanced', 'boosted', 'injected'];
        if (recClasses.some(cls => post.classList.contains(cls))) {
            return true;
        }
        
        // Method 5: Check for Corgi-specific markers in hidden elements
        const hiddenMarkers = post.querySelectorAll('[data-corgi-marker], [data-injected], [data-recommendation]');
        if (hiddenMarkers.length > 0) {
            return true;
        }
        
        return false;
    }
    
    // Find the best position to insert the recommendation badge
    function findBestInsertPosition(post) {
        // Try to find a header or content area
        const candidates = [
            post.querySelector('.status-header'),
            post.querySelector('.status-content'),
            post.querySelector('.post-header'),
            post.querySelector('.timeline-item-header'),
            post.querySelector('header'),
            post.querySelector('.content'),
            post.querySelector('[data-test="status-content"]'),
            post
        ];
        
        for (const candidate of candidates) {
            if (candidate && candidate.offsetParent !== null) {
                // Make sure the parent has relative positioning for absolute badge positioning
                if (getComputedStyle(candidate).position === 'static') {
                    candidate.style.position = 'relative';
                }
                return candidate;
            }
        }
        
        // Fallback to the post itself
        if (getComputedStyle(post).position === 'static') {
            post.style.position = 'relative';
        }
        return post;
    }
    
    // Enhanced observer for dynamic content
    function startCorgiObserver() {
        const observer = new MutationObserver((mutations) => {
            let shouldEnhance = false;
            
            mutations.forEach((mutation) => {
                // Check for new nodes that might be posts
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const hasPostContent = node.matches && (
                            node.matches('[data-post-id]') ||
                            node.matches('.status-wrapper') ||
                            node.matches('.status') ||
                            node.matches('.timeline-item') ||
                            node.matches('article[role="article"]') ||
                            node.matches('article[data-test="status"]') ||
                            node.querySelector('[data-post-id], .status-wrapper, .status, .timeline-item, article[role="article"]')
                        );
                        
                        if (hasPostContent) {
                            shouldEnhance = true;
                        }
                    }
                });
            });
            
            if (shouldEnhance) {
                // Debounce enhancement to avoid excessive calls
                clearTimeout(window.corgiEnhanceTimeout);
                window.corgiEnhanceTimeout = setTimeout(enhancePostsWithRecommendations, 150);
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        log('Observer started - watching for new posts');
        return observer;
    }
    
    // Check if Corgi API is available
    function checkCorgiAPI() {
        return fetch(`${CORGI_API_URL}/health`, { 
            timeout: 5000,
            signal: AbortSignal.timeout(5000)
        })
        .then(response => response.json())
        .then(data => {
            log('Corgi API is responding:', data);
            return true;
        })
        .catch(error => {
            error('Cannot reach Corgi API:', error);
            return false;
        });
    }
    
    // Force ELK to use Corgi proxy for timeline if possible
    function configureELKIntegration() {
        // Set localStorage config
        localStorage.setItem('corgi_api_url', CORGI_API_URL);
        localStorage.setItem('corgi_enabled', 'true');
        
        // Try to update window config
        window.__CORGI_API_BASE_URL = CORGI_API_URL;
        
        // Try to update Nuxt config if available
        if (window.$nuxt) {
            try {
                if (window.$nuxt.$config && window.$nuxt.$config.public) {
                    window.$nuxt.$config.public.corgiApiUrl = CORGI_API_URL;
                    window.$nuxt.$config.public.useCorgi = true;
                }
            } catch (e) {
                log('Could not update Nuxt config, but visual enhancements will still work');
            }
        }
        
        log('ELK integration configured');
    }
    
    // Initialize the seamless integration
    function initialize() {
        log('Initializing Corgi ELK Seamless Integration...');
        
        // Inject styles immediately
        injectStyles();
        
        // Configure ELK integration
        configureELKIntegration();
        
        // Check API availability and start enhancing
        checkCorgiAPI().then(apiAvailable => {
            if (apiAvailable) {
                // Start enhancing posts
                enhancePostsWithRecommendations();
                
                // Start observer for dynamic content
                window.corgiObserver = startCorgiObserver();
                
                // Enhance posts periodically to catch any missed ones
                setInterval(enhancePostsWithRecommendations, 10000);
                
                console.log('🎉 Corgi ELK Seamless Integration active!');
                console.log('Recommendations will now appear with subtle styling in your timeline.');
            } else {
                error('Corgi API not available - visual enhancements disabled');
                // Still inject styles in case API comes online later
                console.log('🟡 Corgi styles loaded, but API is not responding');
            }
        });
    }
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
    
    // Also initialize when navigating in SPA
    let lastUrl = location.href;
    new MutationObserver(() => {
        const url = location.href;
        if (url !== lastUrl) {
            lastUrl = url;
            setTimeout(initialize, 1000); // Give the new page time to load
        }
    }).observe(document, { subtree: true, childList: true });
    
})(); 