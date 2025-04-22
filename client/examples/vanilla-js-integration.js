/**
 * Example vanilla JavaScript integration for Corgi Recommender Service
 * 
 * This file demonstrates how to integrate the Corgi Recommender Service
 * with a vanilla JavaScript application.
 */

// Import client modules
import { 
  getApiConfig, 
  createStatusMiddleware,
  createDomObserver
} from '../index.js';

// Initialize the Corgi Recommender Service
function initCorgiRecommender(options = {}) {
  const { 
    apiBaseUrl = null,
    getUserId = () => localStorage.getItem('userId'),
    mastodonClient = null
  } = options;
  
  // Get API configuration
  const apiConfig = getApiConfig(apiBaseUrl);
  console.log('Corgi Recommender Service initialized with API:', apiConfig.baseUrl);
  
  // Create status middleware for intercepting Mastodon API calls
  const statusMiddleware = createStatusMiddleware({
    apiBaseUrl,
    getUserId,
    onSuccess: (action, result) => {
      console.log(`Successfully logged ${action}:`, result);
    },
    onError: (error) => {
      console.error('Failed to log interaction:', error);
    }
  });
  
  // Create DOM observer for tracking interactions through UI
  const domObserver = createDomObserver({
    apiBaseUrl,
    getUserId,
    onSuccess: (message) => {
      // Show a toast or notification
      showNotification(message);
    },
    onError: (message) => {
      console.error(message);
    }
  });
  
  // Start the DOM observer
  domObserver.start();
  
  // Wrap Mastodon client if provided
  if (mastodonClient) {
    const wrappedClient = statusMiddleware.wrapMastodonClient(mastodonClient);
    console.log('Mastodon client wrapped with interaction logging');
    
    // Return the wrapped client
    return {
      apiConfig,
      mastodonClient: wrappedClient,
      domObserver,
      cleanup: () => {
        domObserver.stop();
      }
    };
  }
  
  // Return API if no client provided
  return {
    apiConfig,
    logInteraction: statusMiddleware.logInteraction,
    domObserver,
    cleanup: () => {
      domObserver.stop();
    }
  };
}

// Simple notification function
function showNotification(message, type = 'info') {
  // Check if notifications are supported
  if (!('Notification' in window)) {
    console.log(message);
    return;
  }
  
  // Check if permission has been granted
  if (Notification.permission === 'granted') {
    new Notification('Corgi Recommender', {
      body: message,
      icon: '/icon.png'
    });
  } else if (Notification.permission !== 'denied') {
    Notification.requestPermission().then(permission => {
      if (permission === 'granted') {
        new Notification('Corgi Recommender', {
          body: message,
          icon: '/icon.png'
        });
      }
    });
  }
  
  // Also log to console
  console.log(message);
}

// Example usage
/*
// Initialize at the start of your application
const corgi = initCorgiRecommender({
  apiBaseUrl: 'https://api.corgi-recommender.example.com',
  getUserId: () => getCurrentUser()?.id,
  mastodonClient: mastodonClient // Your Mastodon API client instance
});

// Log interactions manually if needed
document.querySelector('#like-button').addEventListener('click', () => {
  corgi.logInteraction({
    postId: '12345',
    actionType: 'favorite',
    context: { source: 'manual' }
  });
});

// Clean up when done
window.addEventListener('unload', () => {
  corgi.cleanup();
});
*/

export { initCorgiRecommender, showNotification };