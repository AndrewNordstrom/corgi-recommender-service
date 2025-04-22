// Simple script to enhance Elk posts with recommendation badges and profile links

(function() {
  // Configuration
  const debug = true;
  
  // Log function if debug is enabled
  const log = debug ? console.log.bind(console, '[ElkEnhancer]') : () => {};
  
  log('Initializing Elk Post Enhancer');
  
  // Function to enhance timeline posts
  function enhancePosts() {
    log('Looking for posts to enhance...');
    
    // Select all status elements that need enhancement
    const statuses = document.querySelectorAll('.status-container');
    
    if (statuses.length > 0) {
      log(`Found ${statuses.length} posts to enhance`);
      
      statuses.forEach(status => {
        try {
          // Skip if already enhanced
          if (status.hasAttribute('data-enhanced')) return;
          
          // Mark as enhanced to avoid processing multiple times
          status.setAttribute('data-enhanced', 'true');
          
          // Try to extract post data from element
          const postData = extractPostData(status);
          
          if (postData) {
            // Add recommendation badge if needed
            if (postData.is_recommendation) {
              addRecommendationBadge(status, postData);
            }
            
            // Enhance profile links if needed
            if (postData.account && postData.account.url) {
              enhanceProfileLinks(status, postData);
            }
          }
        } catch (err) {
          console.error('Error enhancing post:', err);
        }
      });
    } else {
      log('No posts found');
    }
  }
  
  // Extract post data from DOM or dataset
  function extractPostData(statusElement) {
    try {
      // First try to find data in the status element's dataset
      let statusDataElement = statusElement.querySelector('[data-status]');
      if (statusDataElement && statusDataElement.dataset.status) {
        return JSON.parse(statusDataElement.dataset.status);
      }
      
      // If not found, check if it's in a parent element
      statusDataElement = statusElement.closest('[data-status]');
      if (statusDataElement && statusDataElement.dataset.status) {
        return JSON.parse(statusDataElement.dataset.status);
      }
      
      // If still not found, try to extract from DOM structure
      log('No status data found, attempting to extract from DOM');
      
      // Find avatar, username, display name
      const avatar = statusElement.querySelector('.account__avatar img, img.avatar');
      const displayName = statusElement.querySelector('.display-name, .account__display-name');
      const username = statusElement.querySelector('.username, .account__acct');
      
      if (avatar && (displayName || username)) {
        return {
          account: {
            avatar: avatar.src,
            display_name: displayName ? displayName.textContent.trim() : '',
            username: username ? username.textContent.trim().replace('@', '') : '',
            url: findProfileLink(statusElement)
          },
          is_recommendation: statusElement.classList.contains('status--recommendation') ||
                            statusElement.querySelector('.status--recommendation, .status-recommended') !== null
        };
      }
      
      log('Could not extract post data');
      return null;
    } catch (err) {
      console.error('Error extracting post data:', err);
      return null;
    }
  }
  
  // Find profile link in status element
  function findProfileLink(statusElement) {
    const profileLinks = statusElement.querySelectorAll('a[href*="/@"]');
    if (profileLinks.length > 0) {
      return profileLinks[0].href;
    }
    return '';
  }
  
  // Add recommendation badge to status
  function addRecommendationBadge(statusElement, postData) {
    log('Adding recommendation badge');
    
    // Check if badge already exists
    if (statusElement.querySelector('.recommendation-badge')) return;
    
    // Create badge element
    const badge = document.createElement('div');
    badge.className = 'recommendation-badge';
    badge.style.cssText = `
      position: absolute;
      top: 8px;
      right: 8px;
      background-color: rgba(var(--rgb-primary), 0.1);
      color: var(--color-primary);
      border-radius: 9999px;
      padding: 4px 8px;
      font-size: 12px;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 4px;
      z-index: 10;
    `;
    
    // Add star icon
    const starIcon = document.createElement('span');
    starIcon.textContent = '★';
    starIcon.style.marginRight = '2px';
    badge.appendChild(starIcon);
    
    // Add text
    const text = document.createElement('span');
    text.textContent = postData.recommendation_reason || 'Recommended for you';
    badge.appendChild(text);
    
    // Find position to insert badge
    const container = statusElement.querySelector('.status__content-wrapper') || statusElement;
    container.style.position = 'relative';
    container.appendChild(badge);
  }
  
  // Enhance profile links in status
  function enhanceProfileLinks(statusElement, postData) {
    log('Enhancing profile links');
    
    if (!postData.account || !postData.account.url) return;
    
    // Find avatar and make it clickable
    const avatar = statusElement.querySelector('.account__avatar img, img.avatar');
    if (avatar) {
      const avatarParent = avatar.parentElement;
      
      // Only modify if it's not already a link
      if (avatarParent && avatarParent.tagName !== 'A') {
        const avatarLink = document.createElement('a');
        avatarLink.href = postData.account.url;
        avatarLink.target = '_blank';
        avatarLink.rel = 'noopener noreferrer';
        avatarLink.className = 'enhanced-avatar-link';
        avatarLink.style.cssText = 'display: block; transition: opacity 0.2s;';
        avatarLink.addEventListener('mouseenter', () => { avatarLink.style.opacity = '0.9'; });
        avatarLink.addEventListener('mouseleave', () => { avatarLink.style.opacity = '1'; });
        
        // Replace avatar with linked version
        avatarParent.appendChild(avatarLink);
        avatarLink.appendChild(avatar);
      }
    }
    
    // Find username and make it clickable
    const username = statusElement.querySelector('.username, .account__acct');
    if (username && username.parentElement && username.parentElement.tagName !== 'A') {
      const usernameLink = document.createElement('a');
      usernameLink.href = postData.account.url;
      usernameLink.target = '_blank';
      usernameLink.rel = 'noopener noreferrer';
      usernameLink.className = 'enhanced-username-link';
      usernameLink.style.cssText = 'color: inherit; text-decoration: none;';
      usernameLink.addEventListener('mouseenter', () => { usernameLink.style.textDecoration = 'underline'; });
      usernameLink.addEventListener('mouseleave', () => { usernameLink.style.textDecoration = 'none'; });
      
      // Replace username with linked version
      username.parentElement.appendChild(usernameLink);
      usernameLink.appendChild(username);
    }
    
    // Find display name and make it clickable
    const displayName = statusElement.querySelector('.display-name, .account__display-name');
    if (displayName && displayName.parentElement && displayName.parentElement.tagName !== 'A') {
      const displayNameLink = document.createElement('a');
      displayNameLink.href = postData.account.url;
      displayNameLink.target = '_blank';
      displayNameLink.rel = 'noopener noreferrer';
      displayNameLink.className = 'enhanced-display-name-link';
      displayNameLink.style.cssText = 'color: inherit; text-decoration: none; font-weight: bold;';
      displayNameLink.addEventListener('mouseenter', () => { displayNameLink.style.textDecoration = 'underline'; });
      displayNameLink.addEventListener('mouseleave', () => { displayNameLink.style.textDecoration = 'none'; });
      
      // Replace display name with linked version
      displayName.parentElement.appendChild(displayNameLink);
      displayNameLink.appendChild(displayName);
    }
  }
  
  // Run enhancer on page load
  document.addEventListener('DOMContentLoaded', enhancePosts);
  
  // Set up observer to detect new posts
  const observer = new MutationObserver((mutations) => {
    let shouldEnhance = false;
    
    mutations.forEach((mutation) => {
      if (mutation.addedNodes && mutation.addedNodes.length > 0) {
        for (let i = 0; i < mutation.addedNodes.length; i++) {
          const node = mutation.addedNodes[i];
          if (node.nodeType === Node.ELEMENT_NODE) {
            // If node is a status or contains statuses
            if (node.classList && (
                node.classList.contains('status') ||
                node.classList.contains('status-container') ||
                node.querySelector('.status, .status-container')
            )) {
              shouldEnhance = true;
              break;
            }
          }
        }
      }
    });
    
    if (shouldEnhance) {
      enhancePosts();
    }
  });
  
  // Start observing
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
  
  // Also enhance posts when navigating between pages
  window.addEventListener('popstate', () => {
    setTimeout(enhancePosts, 500);
  });
  
  log('Enhancer ready');
})();