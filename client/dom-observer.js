/**
 * Corgi Recommender Service - DOM Observer
 * 
 * This module provides DOM mutation observers for tracking user interactions
 * with posts when direct API interception isn't possible.
 * 
 * It's particularly useful for:
 * - Third-party Mastodon clients where you don't control the API calls
 * - Non-SPA applications where interactions happen through standard links
 * - Fallback tracking when API interception fails
 */

import { getApiConfig } from './api-config.js';

// Logger utility
const logger = {
  debug: (message, ...args) => console.debug(`[Corgi] ${message}`, ...args),
  error: (message, ...args) => console.error(`[Corgi] ${message}`, ...args),
  info: (message, ...args) => console.info(`[Corgi] ${message}`, ...args),
  warn: (message, ...args) => console.warn(`[Corgi] ${message}`, ...args)
};

/**
 * Configuration options for DOM observer
 * @typedef {Object} DomObserverOptions
 * @property {string} apiBaseUrl - Base URL for the API
 * @property {Function} getUserId - Function to get the current user ID
 * @property {Object} selectors - CSS selectors for finding elements
 * @property {string} selectors.timeline - Selector for timeline container
 * @property {string} selectors.post - Selector for post elements
 * @property {string} selectors.favorite - Selector for favorite button
 * @property {string} selectors.reblog - Selector for reblog button
 * @property {string} selectors.reply - Selector for reply button
 * @property {string} selectors.bookmark - Selector for bookmark button
 * @property {Object} toast - Toast notification handlers
 */

/**
 * Create a DOM observer for tracking post interactions
 * 
 * @param {DomObserverOptions} options - Configuration options
 * @returns {Object} Observer control methods
 */
export function createDomObserver(options = {}) {
  const {
    apiBaseUrl = null,
    getUserId = () => null,
    selectors = {
      timeline: '.timeline, .timeline-container, [role="feed"]',
      post: 'article.status, .status, [data-status-id]',
      favorite: '[aria-label*="favorite" i], [aria-label*="like" i], .status-favorite',
      reblog: '[aria-label*="boost" i], [aria-label*="reblog" i], .status-reblog',
      reply: '[aria-label*="reply" i], [aria-label*="comment" i], .status-reply',
      bookmark: '[aria-label*="bookmark" i], .status-bookmark'
    },
    toast = {
      success: (message) => logger.info(message),
      error: (message) => logger.error(message)
    }
  } = options;

  // Get API config
  const config = getApiConfig(apiBaseUrl);
  const interactionsUrl = config.interactionsUrl;
  
  // Track which posts we've already processed
  const processedPosts = new Set();
  const processedInteractions = new Set();
  
  // Create click observer for interaction buttons
  let clickObserver = null;
  
  /**
   * Log an interaction to the API
   * 
   * @param {string} postId - Post ID
   * @param {string} actionType - Action type (favorite, reblog, etc.)
   * @returns {Promise} API response
   */
  async function logInteraction(postId, actionType) {
    try {
      const userId = typeof getUserId === 'function' ? getUserId() : null;
      
      // Skip if we can't identify the user
      if (!userId) {
        logger.warn('Cannot log interaction: No user ID available');
        return;
      }
      
      // Create unique key for this interaction to prevent duplicates
      const interactionKey = `${userId}:${postId}:${actionType}:${Date.now()}`;
      
      // Skip if we've already logged this exact interaction recently
      if (processedInteractions.has(interactionKey)) {
        return;
      }
      
      // Add to processed set temporarily (clear after 5 seconds)
      processedInteractions.add(interactionKey);
      setTimeout(() => processedInteractions.delete(interactionKey), 5000);
      
      // Prepare log data
      const logData = {
        user_id: userId,
        post_id: postId,
        action_type: actionType,
        context: { source: 'dom_observer' }
      };
      
      logger.debug(`Logging interaction to ${interactionsUrl}:`, logData);
      
      // Send to API
      const response = await fetch(interactionsUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(logData)
      });
      
      if (response.ok) {
        toast.success(`${actionType.charAt(0).toUpperCase() + actionType.slice(1)} logged`);
        return await response.json();
      } else {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      logger.error('Failed to log interaction:', error);
      toast.error('Failed to log interaction');
      throw error;
    }
  }
  
  /**
   * Extract post ID from an element or its ancestors
   * 
   * @param {Element} element - DOM element to check
   * @returns {string|null} Post ID or null if not found
   */
  function extractPostId(element) {
    // Try to get ID from the element itself
    let postId = element.getAttribute('data-status-id') || 
                 element.getAttribute('data-id') ||
                 element.id?.match(/^status-(.+)$/)?.[1];
    
    if (postId) return postId;
    
    // Try to get ID from parent elements (up to 5 levels)
    let parent = element.parentElement;
    let levels = 0;
    
    while (parent && levels < 5) {
      postId = parent.getAttribute('data-status-id') || 
               parent.getAttribute('data-id') ||
               parent.id?.match(/^status-(.+)$/)?.[1];
      
      if (postId) return postId;
      
      parent = parent.parentElement;
      levels++;
    }
    
    // Try to get ID from URL or href
    if (element.href) {
      const match = element.href.match(/\/statuses?\/([^/?#]+)/);
      if (match) return match[1];
    }
    
    // Try to find a link with a status URL
    const statusLink = element.querySelector('a[href*="/statuses/"]');
    if (statusLink) {
      const match = statusLink.href.match(/\/statuses?\/([^/?#]+)/);
      if (match) return match[1];
    }
    
    return null;
  }
  
  /**
   * Determine action type from element
   * 
   * @param {Element} element - DOM element to check
   * @returns {string|null} Action type or null if not recognized
   */
  function determineActionType(element) {
    // Check for favorite/like
    if (element.matches(selectors.favorite) || 
        element.closest(selectors.favorite) ||
        element.innerHTML.match(/i-ri:heart|favorite|like/i)) {
      return 'favorite';
    }
    
    // Check for reblog/boost
    if (element.matches(selectors.reblog) ||
        element.closest(selectors.reblog) ||
        element.innerHTML.match(/i-ri:repeat|boost|reblog/i)) {
      return 'reblog';
    }
    
    // Check for reply/comment
    if (element.matches(selectors.reply) ||
        element.closest(selectors.reply) ||
        element.innerHTML.match(/i-ri:chat|reply|comment/i)) {
      return 'reply';
    }
    
    // Check for bookmark
    if (element.matches(selectors.bookmark) ||
        element.closest(selectors.bookmark) ||
        element.innerHTML.match(/i-ri:bookmark|bookmark/i)) {
      return 'bookmark';
    }
    
    return null;
  }
  
  /**
   * Handle click events on the document
   * 
   * @param {Event} event - Click event
   */
  function handleClick(event) {
    const target = event.target;
    
    // Skip if not a button or link
    if (!target.tagName.match(/^(BUTTON|A)$/i) && !target.closest('button, a')) {
      return;
    }
    
    // Find the post ID
    const clickElement = target.tagName.match(/^(BUTTON|A)$/i) ? target : target.closest('button, a');
    const postId = extractPostId(clickElement);
    
    if (!postId) {
      return;
    }
    
    // Determine action type
    const actionType = determineActionType(clickElement);
    
    if (!actionType) {
      return;
    }
    
    logger.debug(`Detected ${actionType} click on post ${postId}`);
    
    // Log the interaction
    logInteraction(postId, actionType).catch(logger.error);
  }
  
  /**
   * Start observing DOM for interactions
   */
  function start() {
    if (typeof document === 'undefined') {
      logger.error('DOM observer cannot start: document is not available');
      return;
    }
    
    // Set up click listener for the whole document
    document.addEventListener('click', handleClick);
    
    logger.info('DOM observer started');
  }
  
  /**
   * Stop observing DOM for interactions
   */
  function stop() {
    if (typeof document === 'undefined') {
      return;
    }
    
    document.removeEventListener('click', handleClick);
    
    logger.info('DOM observer stopped');
  }
  
  return {
    start,
    stop,
    logInteraction
  };
}

/**
 * Create a standalone plugin for popular Mastodon clients
 * 
 * @param {Object} options - Plugin options
 * @returns {Object} Plugin methods
 */
export function createMastodonClientPlugin(options = {}) {
  const {
    apiBaseUrl = null,
    client = 'unknown',
    getUserId = () => null
  } = options;
  
  let observer = null;
  
  // Different configuration based on client type
  const clientConfig = {
    default: {
      selectors: {
        timeline: '.timeline, [role="feed"]',
        post: 'article.status',
        favorite: '.status__action-bar-button--favourite',
        reblog: '.status__action-bar-button--reblog',
        reply: '.status__action-bar-button--reply',
        bookmark: '.status__action-bar-button--bookmark'
      }
    },
    pinafore: {
      selectors: {
        timeline: '.timeline-item-list',
        post: '.status-article',
        favorite: '.status-favorite-button',
        reblog: '.status-boost-button',
        reply: '.status-reply-button',
        bookmark: '.status-bookmark-button'
      }
    },
    sengi: {
      selectors: {
        timeline: '.stream-body',
        post: '.status',
        favorite: '[title*="Favorite"]',
        reblog: '[title*="Boost"]',
        reply: '[title*="Reply"]',
        bookmark: '[title*="Bookmark"]'
      }
    },
    elk: {
      selectors: {
        timeline: '.timeline-container',
        post: 'article.status',
        favorite: '[aria-label*="Favorite"]',
        reblog: '[aria-label*="Boost"]',
        reply: '[aria-label*="Reply"]',
        bookmark: '[aria-label*="Bookmark"]'
      }
    }
  };
  
  // Get client-specific config or default
  const clientSelectors = clientConfig[client] || clientConfig.default;
  
  /**
   * Initialize the plugin
   */
  function init() {
    observer = createDomObserver({
      apiBaseUrl,
      getUserId,
      selectors: clientSelectors.selectors
    });
    
    observer.start();
    
    logger.info(`Mastodon client plugin initialized for ${client}`);
  }
  
  /**
   * Clean up the plugin
   */
  function cleanup() {
    if (observer) {
      observer.stop();
    }
  }
  
  return {
    init,
    cleanup
  };
}

export default {
  createDomObserver,
  createMastodonClientPlugin
};