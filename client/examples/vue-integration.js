/**
 * Example Vue/Nuxt integration for Corgi Recommender Service
 * 
 * This file demonstrates how to integrate the Corgi Recommender Service
 * with a Vue/Nuxt application.
 */

// Import client modules
import { 
  useApiConfig, 
  useStatusActions, 
  useTimelineLogger, 
  usePostLoggingConsent 
} from '../index.js';

// Example Nuxt plugin for post logging
export default defineNuxtPlugin({
  name: 'corgi-recommender',
  enforce: 'post', // Run after other plugins
  setup() {
    const nuxtApp = useNuxtApp()
    console.log('Corgi Recommender Service plugin initialized')

    // Configure API endpoints
    const apiConfig = useApiConfig()
    
    // Override API base URL if needed
    if (process.env.CORGI_API_BASE_URL) {
      apiConfig.setApiBaseUrl(process.env.CORGI_API_BASE_URL)
    }
    
    // Access toast notification system if available
    const toast = nuxtApp.$toast || { 
      success: (msg) => console.log(`Success: ${msg}`),
      error: (msg) => console.error(`Error: ${msg}`) 
    }

    // Start the timeline logger when user has given consent
    const { consentToPostLogging } = usePostLoggingConsent({
      currentUser: nuxtApp.$currentUser,
      updateUserPreferences: nuxtApp.$updateUserPreferences
    })
    
    if (consentToPostLogging.value && process.client) {
      const { logPosts } = useTimelineLogger({ 
        consentToPostLogging: consentToPostLogging.value,
        toast
      })
      
      // Hook into timeline data events
      nuxtApp.hook('timeline:items', (items) => {
        console.log('Timeline items detected:', items?.length || 0)
        if (Array.isArray(items) && items.length > 0) {
          logPosts(items)
        }
      })
    }
    
    // Provide the API config and integration hooks to the app
    nuxtApp.provide('corgiConfig', apiConfig)
    
    // Provide wrapped status actions
    nuxtApp.provide('useCorgiStatusActions', (options) => {
      return useStatusActions({
        ...options,
        toast
      })
    })
    
    // Return API for use in app
    return {
      provide: {
        corgiConfig: apiConfig
      }
    }
  }
})

// Example usage in a Vue component
/*
<script setup>
const props = defineProps({
  status: Object
})

const { client } = useMasto()
const { currentUser } = useUser()
const toast = useToast()

// Use the enhanced status actions with interaction logging
const { 
  toggleFavourite, 
  toggleReblog,
  toggleBookmark,
  toggleMoreLikeThis,
  toggleLessLikeThis,
  isLoading 
} = useStatusActions({
  status: props.status,
  client,
  getUserId: () => currentUser.value?.id,
  toast
})
</script>

<template>
  <div class="status-actions">
    <button @click="toggleFavourite" :disabled="isLoading.favourited">
      Like
    </button>
    <button @click="toggleReblog" :disabled="isLoading.reblogged">
      Boost
    </button>
    <button @click="toggleMoreLikeThis" :disabled="isLoading.moreLikeThis">
      More like this
    </button>
  </div>
</template>
*/