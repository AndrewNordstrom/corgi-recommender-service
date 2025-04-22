/**
 * Corgi Recommender Service - Status Interaction Middleware
 * 
 * This module provides middleware for intercepting and logging user interactions 
 * with posts (likes, reblogs, bookmarks, etc.)
 * 
 * It's designed to be used with Mastodon-compatible clients and can wrap existing
 * Mastodon API client methods to add interaction logging.
 */

import { useApiConfig, getApiConfig } from './api-config.js';

/**
 * Logger utility for consistent logging
 */
const logger = {
  debug: (message, ...args) => console.debug(`[Corgi] ${message}`, ...args),
  error: (message, ...args) => console.error(`[Corgi] ${message}`, ...args),
  info: (message, ...args) => console.info(`[Corgi] ${message}`, ...args),
  warn: (message, ...args) => console.warn(`[Corgi] ${message}`, ...args)
};

/**
 * Hook for Vue/Nuxt applications that provides status interaction logging
 * 
 * @param {Object} options - Configuration options
 * @param {Object} options.status - The status object to interact with
 * @param {Function} options.checkLogin - Function to check if user is logged in
 * @param {Object} options.client - Mastodon API client
 * @param {Function} options.getUserId - Function to get current user ID
 * @param {Object} options.toast - Toast notification service (optional)
 * @returns {Object} - Status interaction functions
 */
export function useStatusActions(options) {
  const { 
    status: initialStatus,
    checkLogin,
    client, 
    getUserId = () => null,
    toast = { success: () => {}, error: () => {} }
  } = options || {};

  // Get API configuration
  const { interactionsApiUrl } = useApiConfig();
  
  // Create reactive status ref
  const isVueAvailable = typeof window !== 'undefined' && (window.Vue || window.__VUE__);
  
  let status;
  if (isVueAvailable && window.Vue && window.Vue.ref) {
    status = window.Vue.ref({ ...initialStatus });
    
    // Watch for status changes
    if (window.Vue.watch) {
      window.Vue.watch(
        () => options.status,
        (newStatus) => {
          status.value = { ...newStatus };
        },
        { deep: true, immediate: true }
      );
    }
  } else {
    status = { value: { ...initialStatus } };
  }

  // Loading states for interactions
  const isLoading = isVueAvailable && window.Vue && window.Vue.ref
    ? window.Vue.ref({
        reblogged: false,
        favourited: false,
        bookmarked: false,
        pinned: false,
        muted: false,
        moreLikeThis: false,
        lessLikeThis: false,
      })
    : {
        value: {
          reblogged: false,
          favourited: false,
          bookmarked: false,
          pinned: false,
          muted: false,
          moreLikeThis: false,
          lessLikeThis: false,
        }
      };

  // Computed value for canReblog
  const canReblog = isVueAvailable && window.Vue && window.Vue.computed
    ? window.Vue.computed(() => {
        return checkLogin && checkLogin() && !status.value.reblogged && !isLoading.value.reblogged;
      })
    : {
        get value() {
          return checkLogin && checkLogin() && !status.value.reblogged && !isLoading.value.reblogged;
        }
      };

  /**
   * Log an interaction to the API and toggle the status in Mastodon
   * 
   * @param {string} action - The action type (reblogged, favourited, etc.)
   * @param {Function} toggleAPI - Function to call Mastodon API
   * @param {string} countField - The count field to update (optional)
   */
  async function logAndToggle(action, toggleAPI, countField) {
    try {
      const userId = getUserId ? getUserId() : null;
      const logData = {
        user_id: userId,
        post_id: status.value.id,
        action_type: action,
      };

      // Get API URL from the centralized config
      const apiUrl = interactionsApiUrl.value;

      logger.debug(`📦 Logging ${action} to API at ${apiUrl}:`, logData);

      // Determine action message for toast
      let actionMessage = '';
      switch (action) {
        case 'favourited':
          actionMessage = status.value[action] ? 'Unfavorited' : 'Favorited';
          break;
        case 'reblogged':
          actionMessage = status.value[action] ? 'Unboosted' : 'Boosted';
          break;
        case 'bookmarked':
          actionMessage = status.value[action] ? 'Unbookmarked' : 'Bookmarked';
          break;
        case 'pinned':
          actionMessage = status.value[action] ? 'Unpinned' : 'Pinned';
          break;
        case 'muted':
          actionMessage = status.value[action] ? 'Unmuted' : 'Muted';
          break;
      }

      // Log to API
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(logData),
      });
      
      // Show toast for interaction logging
      if (response.ok) {
        toast.success(`${actionMessage} post`, 2000);
      }

      // Set local status optimistically
      const prevValue = status.value[action];
      status.value[action] = !status.value[action];
      if (countField) {
        status.value[countField] += status.value[action] ? 1 : -1;
      }

      // Call Mastodon API & Wait for Response
      try {
        const newStatus = await toggleAPI();

        // Ensure the UI Reflects the Correct API Response
        if (countField) {
          const prevCount = status.value[countField];
          if (status.value[action] && prevCount === newStatus[countField]) {
            newStatus[countField] -= 1;
          }
        }

        Object.assign(status.value, newStatus);
        logger.debug(`✅ Successfully toggled ${action} on Mastodon`);
      } catch (err) {
        // Revert optimistic update if API call fails
        status.value[action] = prevValue;
        if (countField) {
          status.value[countField] = prevValue ? status.value[countField] + 1 : status.value[countField] - 1;
        }
        throw err;
      }
    } catch (err) {
      logger.error(`❌ Error in ${action}:`, err);
      // Show error toast
      toast.error(`Failed to process ${action} action`, 3000);
      throw err;
    } finally {
      isLoading.value[action] = false;
    }
  }

  /**
   * Toggle reblog state on a status
   */
  const toggleReblog = async () => {
    isLoading.value.reblogged = true;
    return logAndToggle(
      'reblogged',
      () =>
        client.value.v1.statuses.$select(status.value.id)[status.value.reblogged ? 'unreblog' : 'reblog'](),
      'reblogsCount',
    );
  };

  /**
   * Toggle favourite state on a status
   */
  const toggleFavourite = async () => {
    isLoading.value.favourited = true;
    return logAndToggle(
      'favourited',
      () =>
        client.value.v1.statuses.$select(status.value.id)[status.value.favourited ? 'unfavourite' : 'favourite'](),
      'favouritesCount',
    );
  };

  /**
   * Toggle bookmark state on a status
   */
  const toggleBookmark = async () => {
    isLoading.value.bookmarked = true;
    return logAndToggle(
      'bookmarked',
      () =>
        client.value.v1.statuses.$select(status.value.id)[status.value.bookmarked ? 'unbookmark' : 'bookmark'](),
    );
  };

  /**
   * Toggle pin state on a status
   */
  const togglePin = async () => {
    isLoading.value.pinned = true;
    return logAndToggle(
      'pinned',
      () =>
        client.value.v1.statuses.$select(status.value.id)[status.value.pinned ? 'unpin' : 'pin'](),
    );
  };

  /**
   * Toggle mute state on a status
   */
  const toggleMute = async () => {
    isLoading.value.muted = true;
    return logAndToggle(
      'muted',
      () =>
        client.value.v1.statuses.$select(status.value.id)[status.value.muted ? 'unmute' : 'mute'](),
    );
  };

  /**
   * Toggle "more like this" preference for a status (recommendation signal)
   */
  const toggleMoreLikeThis = async () => {
    try {
      isLoading.value.moreLikeThis = true;
      const userId = getUserId ? getUserId() : null;
      const logData = {
        user_id: userId,
        post_id: status.value.id,
        action_type: 'more_like_this',
        context: { source: 'user_preference' },
      };

      // Get API URL from the centralized config
      const apiUrl = interactionsApiUrl.value;

      logger.debug(`📦 Logging more_like_this to API at ${apiUrl}:`, logData);

      // Log to API
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(logData),
      });

      // Update local state
      status.value.more_like_this = !status.value.more_like_this;
      
      // Show toast notification
      if (response.ok) {
        toast.success(`${status.value.more_like_this ? 'More' : 'Fewer'} posts like this will be shown`, 2000);
      }
    } catch (err) {
      logger.error('❌ Error in toggleMoreLikeThis:', err);
      toast.error('Failed to update recommendations', 3000);
    } finally {
      isLoading.value.moreLikeThis = false;
    }
  };

  /**
   * Toggle "less like this" preference for a status (recommendation signal)
   */
  const toggleLessLikeThis = async () => {
    try {
      isLoading.value.lessLikeThis = true;
      const userId = getUserId ? getUserId() : null;
      const logData = {
        user_id: userId,
        post_id: status.value.id,
        action_type: 'less_like_this',
        context: { source: 'user_preference' },
      };

      // Get API URL from the centralized config
      const apiUrl = interactionsApiUrl.value;

      logger.debug(`📦 Logging less_like_this to API at ${apiUrl}:`, logData);

      // Log to API
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(logData),
      });

      // Update local state
      status.value.less_like_this = !status.value.less_like_this;
      
      // Show toast notification
      if (response.ok) {
        toast.success(`${status.value.less_like_this ? 'Fewer' : 'More'} posts like this will be shown`, 2000);
      }
    } catch (err) {
      logger.error('❌ Error in toggleLessLikeThis:', err);
      toast.error('Failed to update recommendations', 3000);
    } finally {
      isLoading.value.lessLikeThis = false;
    }
  };

  return {
    status,
    isLoading,
    canReblog,
    toggleReblog,
    toggleFavourite,
    toggleBookmark,
    togglePin,
    toggleMute,
    toggleMoreLikeThis,
    toggleLessLikeThis,
  };
}

/**
 * Create a standalone status interaction middleware
 * 
 * This is a simpler version for use in non-Vue applications
 * 
 * @param {Object} options Configuration options
 * @returns {Object} Status interaction functions
 */
export function createStatusMiddleware(options = {}) {
  const { 
    apiBaseUrl = null,
    getUserId = () => null,
    onSuccess = () => {},
    onError = () => {}
  } = options;

  // Get API configuration
  const config = getApiConfig(apiBaseUrl);
  
  /**
   * Log a user interaction with a post
   * 
   * @param {Object} interaction Interaction data
   * @returns {Promise} API response
   */
  async function logInteraction(interaction) {
    try {
      const userId = getUserId();
      const { postId, actionType, context = {} } = interaction;
      
      if (!postId || !actionType) {
        throw new Error('Missing required fields: postId and actionType are required');
      }
      
      const logData = {
        user_id: userId,
        post_id: postId,
        action_type: actionType,
        context
      };
      
      logger.debug(`📦 Logging ${actionType} to API:`, logData);
      
      const response = await fetch(config.interactionsUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(logData)
      });
      
      if (response.ok) {
        const result = await response.json();
        onSuccess(actionType, result);
        return result;
      } else {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      logger.error('Failed to log interaction:', error);
      onError(error);
      throw error;
    }
  }
  
  /**
   * Wrap Mastodon API methods with interaction logging
   * 
   * @param {Object} client Mastodon API client
   * @returns {Object} Wrapped client with logging
   */
  function wrapMastodonClient(client) {
    // Don't modify the original client
    const originalClient = { ...client };
    
    // Wrap status interactions
    if (client.v1 && client.v1.statuses) {
      const originalStatusSelect = client.v1.statuses.$select;
      
      client.v1.statuses.$select = (id) => {
        const statusAPI = originalStatusSelect.call(client.v1.statuses, id);
        
        // Create wrapped versions of all interaction methods
        const wrappedAPI = {
          ...statusAPI,
          
          // Override favourite/unfavourite
          async favourite() {
            await logInteraction({ postId: id, actionType: 'favourited' });
            return statusAPI.favourite();
          },
          
          async unfavourite() {
            await logInteraction({ postId: id, actionType: 'unfavourite' });
            return statusAPI.unfavourite();
          },
          
          // Override reblog/unreblog
          async reblog() {
            await logInteraction({ postId: id, actionType: 'reblogged' });
            return statusAPI.reblog();
          },
          
          async unreblog() {
            await logInteraction({ postId: id, actionType: 'unreblog' });
            return statusAPI.unreblog();
          },
          
          // Override bookmark/unbookmark
          async bookmark() {
            await logInteraction({ postId: id, actionType: 'bookmarked' });
            return statusAPI.bookmark();
          },
          
          async unbookmark() {
            await logInteraction({ postId: id, actionType: 'unbookmark' });
            return statusAPI.unbookmark();
          },
          
          // Override pin/unpin
          async pin() {
            await logInteraction({ postId: id, actionType: 'pinned' });
            return statusAPI.pin();
          },
          
          async unpin() {
            await logInteraction({ postId: id, actionType: 'unpin' });
            return statusAPI.unpin();
          },
          
          // Override mute/unmute
          async mute() {
            await logInteraction({ postId: id, actionType: 'muted' });
            return statusAPI.mute();
          },
          
          async unmute() {
            await logInteraction({ postId: id, actionType: 'unmute' });
            return statusAPI.unmute();
          }
        };
        
        return wrappedAPI;
      };
    }
    
    return client;
  }
  
  return {
    logInteraction,
    wrapMastodonClient
  };
}

export default {
  useStatusActions,
  createStatusMiddleware
};