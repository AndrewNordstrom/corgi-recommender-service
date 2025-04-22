/**
 * Corgi Recommender Service API configuration
 * 
 * This module provides configuration for the Corgi Recommender Service API endpoints.
 * It can be used in both Vue/Nuxt applications and vanilla JavaScript.
 */

// Default production API base URL - override with environment variables
const DEFAULT_API_BASE = 'https://localhost:5002';

// Default API prefix - can be overridden by environment variables
const DEFAULT_API_PREFIX = '/api/v1';
const API_PREFIX = process.env.API_PREFIX || DEFAULT_API_PREFIX;

// API endpoints relative to the base URL
const API_ENDPOINTS = {
  interactions: `${API_PREFIX}/interactions`,
  posts: `${API_PREFIX}/posts`,
  recommendations: `${API_PREFIX}/recommendations`,
  privacy: `${API_PREFIX}/privacy`,
  health: `${API_PREFIX}/health`
};

/**
 * API configuration for Vue/Nuxt applications using Composition API
 */
export function useApiConfig() {
  // Use reactive references if Vue is available
  const isVueAvailable = typeof Vue !== 'undefined' || typeof window !== 'undefined' && window.__VUE__;
  
  // Create getters that read from environment or default values
  const createRef = (value) => {
    if (isVueAvailable && typeof window !== 'undefined' && window.Vue && window.Vue.ref) {
      return window.Vue.ref(value);
    }
    // Simple getter/setter for non-Vue environments
    let _value = value;
    return {
      get value() { return _value; },
      set value(newValue) { _value = newValue; }
    };
  };

  // API base URL
  const apiBaseUrl = createRef(
    process.env.CORGI_API_BASE_URL || 
    (typeof window !== 'undefined' && window.__CORGI_API_BASE_URL) || 
    DEFAULT_API_BASE
  );

  // Create endpoint URLs based on base URL
  const interactionsApiUrl = createRef(`${apiBaseUrl.value}${API_ENDPOINTS.interactions}`);
  const postsApiUrl = createRef(`${apiBaseUrl.value}${API_ENDPOINTS.posts}`);
  const recommendationsApiUrl = createRef(`${apiBaseUrl.value}${API_ENDPOINTS.recommendations}`);
  const privacyApiUrl = createRef(`${apiBaseUrl.value}${API_ENDPOINTS.privacy}`);
  const healthApiUrl = createRef(`${apiBaseUrl.value}${API_ENDPOINTS.health}`);

  // Update all URLs when base URL changes
  if (isVueAvailable && typeof window !== 'undefined' && window.Vue && window.Vue.watch) {
    window.Vue.watch(apiBaseUrl, (newBaseUrl) => {
      interactionsApiUrl.value = `${newBaseUrl}${API_ENDPOINTS.interactions}`;
      postsApiUrl.value = `${newBaseUrl}${API_ENDPOINTS.posts}`;
      recommendationsApiUrl.value = `${newBaseUrl}${API_ENDPOINTS.recommendations}`;
      privacyApiUrl.value = `${newBaseUrl}${API_ENDPOINTS.privacy}`;
      healthApiUrl.value = `${newBaseUrl}${API_ENDPOINTS.health}`;
    });
  }

  return {
    apiBaseUrl,
    interactionsApiUrl,
    postsApiUrl,
    recommendationsApiUrl,
    privacyApiUrl,
    healthApiUrl,
    
    // Method to update the base URL programmatically
    setApiBaseUrl(newBaseUrl) {
      apiBaseUrl.value = newBaseUrl;
    }
  };
}

/**
 * API configuration for vanilla JavaScript applications
 */
export function getApiConfig(customBaseUrl = null) {
  const baseUrl = customBaseUrl || 
    process.env.CORGI_API_BASE_URL || 
    (typeof window !== 'undefined' && window.__CORGI_API_BASE_URL) || 
    DEFAULT_API_BASE;
    
  return {
    baseUrl,
    interactionsUrl: `${baseUrl}${API_ENDPOINTS.interactions}`,
    postsUrl: `${baseUrl}${API_ENDPOINTS.posts}`,
    recommendationsUrl: `${baseUrl}${API_ENDPOINTS.recommendations}`,
    privacyUrl: `${baseUrl}${API_ENDPOINTS.privacy}`,
    healthUrl: `${baseUrl}${API_ENDPOINTS.health}`
  };
}

export default {
  useApiConfig,
  getApiConfig
};