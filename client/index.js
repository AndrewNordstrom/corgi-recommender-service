/**
 * Corgi Recommender Service - Client Integration
 * 
 * This module exports all client integration utilities for the Corgi Recommender Service.
 */

// API configuration
export { useApiConfig, getApiConfig } from './api-config.js';

// Status interaction middleware
export { useStatusActions, createStatusMiddleware } from './status.js';

// Post logging utilities
export { 
  logTimelinePosts,
  useTimelineLogger,
  usePostLoggingConsent,
  extractMetadataFromStatus,
  savePostMetadata
} from './post-logger.js';

// DOM observation utilities
export {
  createDomObserver,
  createMastodonClientPlugin
} from './dom-observer.js';

// Diagnostics utilities
export { interactionDiagnostics } from './utils/interaction-diagnostics.js';

// Default exports for convenience
export default {
  // API configuration
  apiConfig: {
    useApiConfig,
    getApiConfig
  },
  
  // Status interaction middleware
  status: {
    useStatusActions,
    createStatusMiddleware
  },
  
  // Post logging utilities
  postLogger: {
    logTimelinePosts,
    useTimelineLogger,
    usePostLoggingConsent,
    extractMetadataFromStatus,
    savePostMetadata
  },
  
  // DOM observation utilities
  domObserver: {
    createDomObserver,
    createMastodonClientPlugin
  },
  
  // Diagnostics utilities
  diagnostics: {
    interactionDiagnostics
  }
};