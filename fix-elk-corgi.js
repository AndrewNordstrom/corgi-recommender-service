// Enhanced seamless ELK-Corgi integration for visual recommendations
// Paste this in the ELK browser console to see recommendations naturally in your timeline

// Set Corgi API URL
window.__CORGI_API_BASE_URL = 'http://localhost:5002';
localStorage.setItem('corgi_api_url', 'http://localhost:5002');
localStorage.setItem('corgi_enabled', 'true');

console.log('✅ Corgi API configured to use port 9999');

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
</style>
`;

// Inject styles
if (!document.getElementById('corgi-recommendation-styles')) {
  document.head.insertAdjacentHTML('beforeend', corgiStyles);
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
    '.conversation-thread .status'
  ];
  
  let postsFound = 0;
  let recsFound = 0;
  
  postSelectors.forEach(selector => {
    const posts = document.querySelectorAll(selector);
    
    posts.forEach(post => {
      if (post.hasAttribute('data-corgi-enhanced')) return;
      
      postsFound++;
      
      // Look for recommendation indicators in the post content or data
      const isRecommendation = checkIfRecommendation(post);
      
      if (isRecommendation) {
        recsFound++;
        
        // Add subtle styling
        post.classList.add('corgi-recommendation');
        
        // Add recommendation badge
        if (!post.querySelector('.corgi-rec-badge')) {
          const badge = document.createElement('div');
          badge.className = 'corgi-rec-badge';
          badge.textContent = '✨ Recommended';
          badge.title = 'This post was recommended by Corgi AI';
          
          // Find the best position to insert the badge
          const insertPosition = findBestInsertPosition(post);
          insertPosition.appendChild(badge);
        }
        
        console.log('🎯 Enhanced recommendation post:', post);
      }
      
      post.setAttribute('data-corgi-enhanced', 'true');
    });
  });
  
  if (recsFound > 0) {
    console.log(`✨ Enhanced ${recsFound} recommendation posts out of ${postsFound} total posts`);
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
    'trending in your network'
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
  const recClasses = ['recommendation', 'suggested', 'recommended', 'enhanced', 'boosted'];
  if (recClasses.some(cls => post.classList.contains(cls))) {
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
            node.querySelector('[data-post-id], .status-wrapper, .status, .timeline-item')
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
      window.corgiEnhanceTimeout = setTimeout(enhancePostsWithRecommendations, 100);
    }
  });
  
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
  
  console.log('🔍 Corgi observer started - watching for new posts');
  return observer;
}

// Check if we can reach Corgi API
fetch('http://localhost:5002/health')
  .then(r => r.json())
  .then(data => {
    console.log('✅ Corgi API is responding:', data);
    
    // Start enhancing posts
    enhancePostsWithRecommendations();
    
    // Start observer for dynamic content
    window.corgiObserver = startCorgiObserver();
    
    // Enhance posts periodically to catch any missed ones
    setInterval(enhancePostsWithRecommendations, 5000);
    
    console.log('\n🎉 Seamless ELK-Corgi integration active!');
    console.log('Recommendations will now appear with subtle styling in your timeline.');
  })
  .catch(e => {
    console.error('❌ Cannot reach Corgi API:', e);
    console.log('Make sure Corgi API is running on port 9999');
  });

// Force ELK to use Corgi proxy for timeline if possible
if (window.$nuxt) {
  try {
    if (window.$nuxt.$config && window.$nuxt.$config.public) {
      window.$nuxt.$config.public.corgiApiUrl = 'http://localhost:5002';
      window.$nuxt.$config.public.useCorgi = true;
    }
  } catch (e) {
    console.log('Could not update Nuxt config, but visual enhancements will still work');
  }
}

console.log('\n📝 Enhanced integration loaded!');
console.log('🔄 The page will now automatically detect and style recommendation posts.');
console.log('✨ Look for posts with golden borders and "Recommended" badges!'); 