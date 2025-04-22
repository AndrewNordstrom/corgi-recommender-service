// Elk custom post component integration

// Wait for the Elk application to fully load
document.addEventListener('DOMContentLoaded', function() {
  // Function to enhance posts
  function enhancePosts() {
    // Find all status/post elements - adjust the selector as needed based on Elk's DOM structure
    const statuses = document.querySelectorAll('.status, .status-compose__content-wrapper, .timeline-item');
    
    if (statuses.length > 0) {
      console.log('Found', statuses.length, 'status elements to enhance');
      
      statuses.forEach(status => {
        // Check if this status has already been enhanced
        if (status.getAttribute('data-enhanced') === 'true') {
          return;
        }
        
        // Try to extract post data
        const postData = extractPostData(status);
        
        if (postData) {
          enhanceStatus(status, postData);
          status.setAttribute('data-enhanced', 'true');
        }
      });
    }
  }
  
  // Function to extract post data from a status element
  function extractPostData(status) {
    try {
      // Try to find post data in the element's dataset
      let postJson = null;
      
      // Check for various ways Elk might store post data
      if (status.dataset.status) {
        postJson = JSON.parse(status.dataset.status);
      } else if (status.querySelector('[data-status]')) {
        postJson = JSON.parse(status.querySelector('[data-status]').dataset.status);
      }
      
      // If we found JSON data, use it
      if (postJson) {
        return postJson;
      }
      
      // Otherwise, try to extract from DOM elements
      return {
        account: {
          display_name: extractText(status, '.display-name, .account__display-name'),
          username: extractText(status, '.username, .account__acct').replace('@', ''),
          url: extractHref(status, '.account-link, a[href*="/@"]'),
          avatar: extractSrc(status, '.account__avatar img, .avatar img')
        }
      };
    } catch (e) {
      console.error('Error extracting post data:', e);
      return null;
    }
  }
  
  // Helper functions to extract data from DOM
  function extractText(element, selector) {
    const found = element.querySelector(selector);
    return found ? found.textContent.trim() : '';
  }
  
  function extractHref(element, selector) {
    const found = element.querySelector(selector);
    return found ? found.href : '';
  }
  
  function extractSrc(element, selector) {
    const found = element.querySelector(selector);
    return found ? found.src : '';
  }
  
  // Function to enhance a status with account information
  function enhanceStatus(statusElement, postData) {
    try {
      // Only continue if we have account data
      if (!postData.account) return;
      
      // Find the header section of the post (or create one if missing)
      let header = statusElement.querySelector('.status__header, .status-header, .timeline-item__header');
      
      if (!header) {
        // Try to find a suitable container for the header
        const contentContainer = statusElement.querySelector('.status__content-wrapper, .status-content, .timeline-item__content');
        
        if (contentContainer) {
          // Create and insert a header before the content
          header = document.createElement('div');
          header.className = 'custom-status-header';
          contentContainer.parentNode.insertBefore(header, contentContainer);
        }
      }
      
      // Only proceed if we found or created a header
      if (!header) return;
      
      // Clean existing avatar if present
      const existingAvatar = header.querySelector('.custom-avatar-link');
      if (existingAvatar) existingAvatar.parentNode.removeChild(existingAvatar);
      
      // Create avatar element (linked to profile)
      if (postData.account.avatar && postData.account.url) {
        const avatarLink = document.createElement('a');
        avatarLink.href = postData.account.url;
        avatarLink.target = '_blank';
        avatarLink.rel = 'noopener noreferrer';
        avatarLink.className = 'custom-avatar-link';
        
        const avatarImg = document.createElement('img');
        avatarImg.src = postData.account.avatar;
        avatarImg.alt = postData.account.display_name || postData.account.username || '';
        avatarImg.className = 'custom-avatar';
        avatarImg.style.cssText = 'width: 48px; height: 48px; border-radius: 50%; object-fit: cover;';
        
        avatarLink.appendChild(avatarImg);
        
        // Add to header
        header.prepend(avatarLink);
      }
      
      // Create user info container
      const userInfo = document.createElement('div');
      userInfo.className = 'custom-user-info';
      userInfo.style.cssText = 'display: flex; flex-direction: column; margin-left: 12px;';
      
      // Add display name (linked to profile)
      if (postData.account.display_name && postData.account.url) {
        const displayNameLink = document.createElement('a');
        displayNameLink.href = postData.account.url;
        displayNameLink.target = '_blank';
        displayNameLink.rel = 'noopener noreferrer';
        displayNameLink.className = 'custom-display-name';
        displayNameLink.textContent = postData.account.display_name;
        displayNameLink.style.cssText = 'font-weight: bold; color: var(--text-color, #000); text-decoration: none;';
        
        userInfo.appendChild(displayNameLink);
      }
      
      // Add username (linked to profile)
      if (postData.account.username && postData.account.url) {
        const usernameLink = document.createElement('a');
        usernameLink.href = postData.account.url;
        usernameLink.target = '_blank';
        usernameLink.rel = 'noopener noreferrer';
        usernameLink.className = 'custom-username';
        usernameLink.textContent = '@' + postData.account.username;
        usernameLink.style.cssText = 'color: var(--text-muted, #666); text-decoration: none; font-size: 14px;';
        
        userInfo.appendChild(usernameLink);
      }
      
      // Add user info to header
      if (userInfo.children.length > 0) {
        // Position the header elements
        header.style.cssText = 'display: flex; align-items: center; margin-bottom: 12px;';
        
        // Check if userInfo is already in the header
        const existingUserInfo = header.querySelector('.custom-user-info');
        if (existingUserInfo) {
          existingUserInfo.parentNode.removeChild(existingUserInfo);
        }
        
        // Add user info after avatar
        const avatarEl = header.querySelector('.custom-avatar-link') || header.firstChild;
        if (avatarEl) {
          avatarEl.after(userInfo);
        } else {
          header.appendChild(userInfo);
        }
      }
      
      console.log('Enhanced status for', postData.account.username);
    } catch (e) {
      console.error('Error enhancing status:', e);
    }
  }
  
  // Run enhancement immediately
  enhancePosts();
  
  // Set up a mutation observer to watch for new posts being added
  const observer = new MutationObserver(function(mutations) {
    let shouldEnhance = false;
    
    mutations.forEach(function(mutation) {
      // Look for added nodes that might be statuses
      if (mutation.addedNodes && mutation.addedNodes.length > 0) {
        for (let i = 0; i < mutation.addedNodes.length; i++) {
          const node = mutation.addedNodes[i];
          if (node.nodeType === Node.ELEMENT_NODE) {
            // Check if this is a status or contains statuses
            if (node.classList && (
                node.classList.contains('status') || 
                node.classList.contains('timeline-item') ||
                node.querySelector('.status, .timeline-item')
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
  
  // Start observing the document for new posts
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
  
  // Also run enhancement when navigating between pages
  window.addEventListener('popstate', function() {
    setTimeout(enhancePosts, 500);
  });
  
  // Log that the script has been loaded
  console.log('Elk post enhancement script loaded');
});