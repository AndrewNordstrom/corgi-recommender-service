/**
 * Corgi Recommender Service - Post Logger
 * 
 * This module provides utilities for logging post views and timeline content.
 * It includes both Vue/Nuxt composables and standalone functions for vanilla JS.
 */

import { useApiConfig, getApiConfig } from './api-config.js';

// Logger utility
const logger = {
  debug: (message, ...args) => console.debug(`[Corgi] ${message}`, ...args),
  error: (message, ...args) => console.error(`[Corgi] ${message}`, ...args),
  info: (message, ...args) => console.info(`[Corgi] ${message}`, ...args),
  warn: (message, ...args) => console.warn(`[Corgi] ${message}`, ...args)
};

/**
 * Extract post metadata from Mastodon status
 * 
 * @param {Object} status Mastodon status object
 * @returns {Object} Extracted metadata
 */
function extractMetadataFromStatus(status) {
  if (!status || !status.id) {
    logger.warn('Attempted to extract metadata from invalid status:', status);
    return null;
  }

  return {
    post_id: status.id,
    author_id: status.account?.id,
    author_name: status.account?.username,
    content: status.content,
    content_type: status.mediaAttachments?.length > 0 ? 'media' : 'text',
    created_at: status.createdAt,
    interaction_counts: {
      favorites: status.favouritesCount || 0,
      reblogs: status.reblogsCount || 0,
      replies: status.repliesCount || 0,
    },
    mastodon_post: status // Include full post for better data
  };
}

/**
 * Vue composable for post logging consent management
 */
export function usePostLoggingConsent(options = {}) {
  const { currentUser, updateUserPreferences } = options;
  
  const isVueAvailable = typeof window !== 'undefined' && (window.Vue || window.__VUE__);
  
  // Create computed property for consent status
  const consentToPostLogging = isVueAvailable && window.Vue && window.Vue.computed
    ? window.Vue.computed({
        get: () => currentUser.value?.preferences?.consentToPostLogging || false,
        set: (value) => {
          updateUserPreferences({ consentToPostLogging: value });
        },
      })
    : {
        get value() { 
          return currentUser?.value?.preferences?.consentToPostLogging || false;
        },
        set value(val) {
          if (updateUserPreferences) {
            updateUserPreferences({ consentToPostLogging: val });
          }
        }
      };

  return { consentToPostLogging };
}

/**
 * Reactive set to track already logged posts
 */
const createLoggedPostsTracker = () => {
  const isVueAvailable = typeof window !== 'undefined' && (window.Vue || window.__VUE__);
  
  return isVueAvailable && window.Vue && window.Vue.ref
    ? window.Vue.ref(new Set())
    : { value: new Set() };
};

// Singleton instance for tracking logged posts
const loggedPosts = createLoggedPostsTracker();

/**
 * Log posts to the API
 * 
 * @param {Object} post Post data
 * @param {Object} options Options for logging
 * @returns {Promise} API response
 */
async function savePostMetadata(post, options = {}) {
  try {
    const { apiBaseUrl = null, toast = null } = options;
    
    // Get API config
    const config = apiBaseUrl 
      ? getApiConfig(apiBaseUrl)
      : useApiConfig().postsApiUrl.value;
    
    const endpoint = typeof config === 'string' ? config : config.postsUrl;
    
    logger.debug(`Saving post metadata to: ${endpoint}`);

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(post)
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Show success toast if available
    if (toast?.success) {
      toast.success('Post logged successfully', 2000);
    }
    
    return data;
  } catch (error) {
    logger.error('Error saving post metadata:', error);
    
    // Show error toast if available
    if (options.toast?.error) {
      options.toast.error('Failed to log post', 3000);
    }
    
    throw error;
  }
}

/**
 * Log timeline posts to the API
 * 
 * @param {Array} posts Array of Mastodon status objects
 * @param {Object} options Options for logging
 */
export async function logTimelinePosts(posts, options = {}) {
  const { 
    consentToPostLogging = true, 
    apiBaseUrl = null,
    toast = null
  } = options;

  // Check for user consent
  if (!consentToPostLogging) {
    return;
  }

  // Process each post
  for (const status of posts) {
    // Skip if already logged
    if (loggedPosts.value.has(status.id)) {
      continue;
    }

    // Extract metadata
    const metadata = extractMetadataFromStatus(status);
    if (!metadata) continue;

    try {
      // Save to database
      await savePostMetadata(metadata, { apiBaseUrl, toast });
      
      // Mark as logged
      loggedPosts.value.add(status.id);
    } catch (error) {
      logger.error('Failed to log post:', error);
    }
  }
}

/**
 * Vue composable for timeline post logging
 */
export function useTimelineLogger(options = {}) {
  const { 
    consentToPostLogging = true,
    apiBaseUrl = null,
    toast = null
  } = options;
  
  const isVueAvailable = typeof window !== 'undefined' && (window.Vue || window.__VUE__);

  // Only proceed if user has given consent and we're in a browser
  if (!consentToPostLogging || typeof window === 'undefined') {
    return {};
  }

  // Setup lifecycle hooks for Vue if available
  if (isVueAvailable && window.Vue) {
    window.Vue.onMounted(() => {
      setupDomObserver({ apiBaseUrl, toast });
    });
  } else if (typeof document !== 'undefined') {
    // For non-Vue environments, set up directly if document is available
    setupDomObserver({ apiBaseUrl, toast });
  }
  
  // Return utility functions
  return {
    logPosts: (posts) => logTimelinePosts(posts, { consentToPostLogging, apiBaseUrl, toast }),
    extractMetadata: extractMetadataFromStatus
  };
}

/**
 * Set up DOM mutation observer to detect new posts
 * 
 * @param {Object} options Options for the observer
 */
function setupDomObserver(options = {}) {
  const { apiBaseUrl = null, toast = null } = options;
  
  // Function to log a post
  function logPost(postData) {
    // For debugging - shows what we're actually logging
    logger.debug('Logging post from DOM:', {
      id: postData.id,
      authorId: postData.account?.id,
      content: postData.content?.substring(0, 50) + '...'
    });
    
    // Skip if already logged
    if (loggedPosts.value.has(postData.id)) {
      return;
    }
    
    // Save to API
    savePostMetadata({
      post_id: postData.id,
      author_id: postData.account?.id || 'unknown',
      author_name: postData.account?.username || '',
      content: postData.content || '',
      content_type: postData.contentType || 'text',
      created_at: postData.createdAt || new Date().toISOString(),
      interaction_counts: {
        favorites: postData.favouritesCount || 0,
        reblogs: postData.reblogsCount || 0,
        replies: postData.repliesCount || 0,
      },
    }, { apiBaseUrl, toast })
      .then(() => {
        loggedPosts.value.add(postData.id);
      })
      .catch(logger.error);
  }
  
  // Set up mutation observer
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === 'childList' && mutation.addedNodes.length) {
        // Find status cards that were added
        const statusElements = document.querySelectorAll('article.status:not([data-logged="true"])');
        
        if (statusElements.length) {
          // Mark them as logged
          statusElements.forEach((el) => {
            const statusId = el.getAttribute('data-status-id')
              || el.getAttribute('data-id')
              || el.querySelector('[data-status-id]')?.getAttribute('data-status-id');
              
            if (statusId) {
              el.setAttribute('data-logged', 'true');
              
              // Extract what data we can from the DOM
              const authorElement = el.querySelector('.status-author, .account, [data-author-id]');
              const contentElement = el.querySelector('.status-content, .content');
              const authorId = authorElement?.getAttribute('data-author-id')
                || authorElement?.querySelector('[href*="/accounts/"]')?.href?.match(/\/accounts\/([^/]+)/)?.[1];
              
              // Extract interaction counts
              const getCount = (selector) => {
                const el = selector.startsWith('.') 
                  ? el.querySelector(selector)
                  : el.querySelector(`.${selector}, [data-${selector}], .${selector}-count, [data-${selector}-count]`);
                
                if (!el) return 0;
                
                const countText = el.textContent.match(/\d+/)?.[0];
                return countText ? parseInt(countText, 10) : 0;
              };
              
              if (authorId && statusId) {
                logPost({
                  id: statusId,
                  account: {
                    id: authorId,
                    username: authorElement?.textContent?.trim() || '',
                  },
                  content: contentElement?.innerHTML || '',
                  createdAt: new Date().toISOString(),
                  favouritesCount: getCount('favorite'),
                  reblogsCount: getCount('reblog'),
                  repliesCount: getCount('reply'),
                  contentType: el.querySelector('img:not(.emoji), video, audio') ? 'media' : 'text',
                });
              }
            }
          });
        }
      }
    }
  });
  
  // Find appropriate container to observe
  const timelineContainer = document.querySelector('.timeline-container, .timeline, [role="feed"]');
  if (timelineContainer) {
    observer.observe(timelineContainer, { childList: true, subtree: true });
    logger.info('Timeline observer attached to', timelineContainer);
  } else {
    // Fall back to observing the body if no timeline container is found
    observer.observe(document.body, { childList: true, subtree: true });
    logger.info('Timeline observer attached to document.body (fallback)');
  }
  
  // Clean up on page unload
  window.addEventListener('unload', () => {
    observer.disconnect();
  });
  
  return observer;
}

export default {
  logTimelinePosts,
  useTimelineLogger,
  usePostLoggingConsent,
  extractMetadataFromStatus,
  savePostMetadata
};