/**
 * Corgi Seamless Integration Composable for ELK
 * 
 * This composable provides seamless integration between ELK and Corgi
 * recommendations, making AI recommendations appear naturally in timelines.
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'

// Helper function to get current user ID from ELK
function getCurrentUserId(): string {
  console.log('[Corgi] 🔍 Attempting to get current user ID...')
  
  if (typeof window !== 'undefined') {
    // Method 1: Try to get from ELK's current user state (most reliable)
    try {
      // Check for ELK's global state
      const elkGlobal = (window as any)?.$elk || (window as any)?.__ELK__ || (window as any)?._elk
      if (elkGlobal?.currentUser?.account?.acct) {
        console.log('[Corgi] ✅ Found user from ELK global state:', elkGlobal.currentUser.account.acct)
        return elkGlobal.currentUser.account.acct
      }
    } catch (e) {
      console.log('[Corgi] Could not access ELK global state:', e)
    }

    // Method 2: Try to get from Nuxt app context
    try {
      const nuxtApp = (window as any)?.$nuxt
      if (nuxtApp?.$currentUser?.account?.acct) {
        console.log('[Corgi] ✅ Found user from Nuxt app:', nuxtApp.$currentUser.account.acct)
        return nuxtApp.$currentUser.account.acct
      }
    } catch (e) {
      console.log('[Corgi] Could not access Nuxt app:', e)
    }

    // Method 3: Try localStorage for current user handle (ELK stores this)
    try {
      const currentUserHandle = localStorage.getItem('elk-current-user-handle')
      if (currentUserHandle && currentUserHandle !== 'null' && currentUserHandle !== 'undefined') {
        console.log('[Corgi] ✅ Found user from localStorage handle:', currentUserHandle)
        return currentUserHandle
      }
    } catch (e) {
      console.log('[Corgi] Could not access localStorage handle:', e)
    }

    // Method 4: Try to parse accounts from localStorage
    try {
      const accountsStr = localStorage.getItem('elk-accounts')
      if (accountsStr) {
        const accounts = JSON.parse(accountsStr)
        // Look for active account or first account
        const activeAccount = accounts.find((acc: any) => acc.active) || accounts[0]
        if (activeAccount?.account?.acct) {
          console.log('[Corgi] ✅ Found user from localStorage accounts:', activeAccount.account.acct)
          return activeAccount.account.acct
        }
      }
    } catch (e) {
      console.log('[Corgi] Could not parse localStorage accounts:', e)
    }

    // Method 5: Try to get from ELK settings
    try {
      const settingsStr = localStorage.getItem('elk-settings')
      if (settingsStr) {
        const settings = JSON.parse(settingsStr)
        // Look for user handles in settings
        for (const key in settings) {
          if (key.includes('@') && key.includes('.')) {
            console.log('[Corgi] ✅ Found user from settings:', key)
            return key
          }
        }
      }
    } catch (e) {
      console.log('[Corgi] Could not parse localStorage settings:', e)
    }

    // Method 6: Try to extract from current URL path
    try {
      const path = window.location.pathname
      // Look for patterns like /mastodon.social/@username or /@username
      const userMatch = path.match(/\/@([^\/]+)/) || path.match(/\/([^\/]+@[^\/]+)/)
      if (userMatch && userMatch[1] && userMatch[1] !== 'home' && userMatch[1] !== 'public') {
        const userHandle = userMatch[1].includes('@') ? userMatch[1] : `${userMatch[1]}@${window.location.hostname}`
        console.log('[Corgi] ✅ Found user from URL path:', userHandle)
        return userHandle
      }
    } catch (e) {
      console.log('[Corgi] Could not extract user from URL:', e)
    }

    // Method 7: Try to get from meta tags
    try {
      const metaUser = document.querySelector('meta[name="current-user"]')?.getAttribute('content')
      if (metaUser && metaUser !== 'null' && metaUser !== 'undefined') {
        console.log('[Corgi] ✅ Found user from meta tag:', metaUser)
        return metaUser
      }
    } catch (e) {
      console.log('[Corgi] Could not access meta tags:', e)
    }

    // Method 8: Try to get from Vue/Nuxt reactive state
    try {
      // Check for Vue app instance
      const vueApp = (window as any)?.__VUE_APP__ || (window as any)?._vueApp
      if (vueApp?.config?.globalProperties?.$currentUser?.account?.acct) {
        console.log('[Corgi] ✅ Found user from Vue app:', vueApp.config.globalProperties.$currentUser.account.acct)
        return vueApp.config.globalProperties.$currentUser.account.acct
      }
    } catch (e) {
      console.log('[Corgi] Could not access Vue app:', e)
    }
  }

  console.log('[Corgi] ⚠️ Could not determine user ID, falling back to anonymous')
  return 'anonymous'
}

export interface CorgiRecommendation {
  id: string
  account: {
    id: string
    username: string
    acct: string
    display_name: string
    avatar: string
    url: string
  }
  content: string
  created_at: string
  is_recommendation?: boolean
  recommendation_reason?: string
  uri: string
  url: string
  reblog?: null
  media_attachments: any[]
  replies_count: number
  reblogs_count: number
  favourites_count: number
  favourited?: boolean
  reblogged?: boolean
}

export interface CorgiConfig {
  apiUrl: string
  enabled: boolean
  proxyMode: boolean
}

// Transform stub posts into full Mastodon-compatible posts
function transformToMastodonPost(rec: any): CorgiRecommendation {
  // If it's already a full Mastodon post, just add recommendation metadata
  if (rec.account && rec.account.username) {
    return {
      ...rec,
      is_recommendation: true,
      recommendation_reason: rec.recommendation_reason || rec.reason || 'AI recommended based on your interests',
      // Ensure the post has proper navigation URLs
      url: rec.url || rec.uri,
      uri: rec.uri || rec.url
    }
  }

  // Helper function to convert Mastodon URL to ELK URL for navigation
  function convertToELKUrl(mastodonUrl: string): string {
    if (!mastodonUrl || mastodonUrl.includes('example.com')) {
      return mastodonUrl
    }
    
    try {
      // Convert https://mastodon.world/@user/123 to http://localhost:5314/mastodon.world/@user/123
      const url = new URL(mastodonUrl)
      
      // Extract the path components
      const pathParts = url.pathname.split('/')
      const hostname = url.hostname
      
      // Handle different Mastodon URL formats:
      // https://mastodon.world/@user/123456 -> /mastodon.world/@user/123456
      // https://mastodon.social/users/username/statuses/123456 -> /mastodon.social/@username/123456
      
      if (pathParts.includes('users') && pathParts.includes('statuses')) {
        // Format: /users/username/statuses/123456
        const userIndex = pathParts.indexOf('users')
        const statusIndex = pathParts.indexOf('statuses')
        if (userIndex >= 0 && statusIndex >= 0 && pathParts[userIndex + 1] && pathParts[statusIndex + 1]) {
          const username = pathParts[userIndex + 1]
          const statusId = pathParts[statusIndex + 1]
          return `http://localhost:5314/${hostname}/@${username}/${statusId}`
        }
      } else if (pathParts[1] && pathParts[1].startsWith('@') && pathParts[2]) {
        // Format: /@username/123456
        return `http://localhost:5314/${hostname}${url.pathname}`
      }
      
      // Fallback: just prepend ELK base URL
      return `http://localhost:5314/${hostname}${url.pathname}`
    } catch (e) {
      console.warn('[Corgi] Could not convert URL:', mastodonUrl, e)
      return mastodonUrl
    }
  }

  // Helper functions for extracting account info from URLs
  function extractUsernameFromUrl(url: string): string {
    try {
      const match = url.match(/@([^\/]+)/) || url.match(/users\/([^\/]+)/)
      return match ? match[1] : 'unknown'
    } catch {
      return 'unknown'
    }
  }

  function extractAcctFromUrl(url: string): string {
    try {
      const urlObj = new URL(url)
      const username = extractUsernameFromUrl(url)
      return `${username}@${urlObj.hostname}`
    } catch {
      return 'unknown@unknown'
    }
  }

  function extractAccountUrlFromPostUrl(postUrl: string): string {
    try {
      const urlObj = new URL(postUrl)
      const username = extractUsernameFromUrl(postUrl)
      return `${urlObj.protocol}//${urlObj.hostname}/@${username}`
    } catch {
      return 'https://example.com/@unknown'
    }
  }

  // Transform the recommendation into a Mastodon-compatible post
  const postUrl = rec.url || rec.uri || `https://example.com/posts/${rec.id || rec.post_id || 'unknown'}`
  const elkUrl = convertToELKUrl(postUrl)
  
  return {
    id: rec.id || rec.post_id || Math.random().toString(36).substr(2, 9),
    created_at: rec.created_at || new Date().toISOString(),
    content: rec.content || rec.text || 'Recommended content',
    account: {
      id: rec.account?.id || rec.author_id || Math.random().toString(36).substr(2, 9),
      username: rec.account?.username || rec.author_username || extractUsernameFromUrl(postUrl),
      acct: rec.account?.acct || rec.author_acct || extractAcctFromUrl(postUrl),
      display_name: rec.account?.display_name || rec.author_display_name || rec.author_username || extractUsernameFromUrl(postUrl),
      url: rec.account?.url || rec.author_url || extractAccountUrlFromPostUrl(postUrl),
      avatar: rec.account?.avatar || rec.author_avatar || 'https://via.placeholder.com/48x48.png?text=👤',
      avatar_static: rec.account?.avatar_static || rec.author_avatar || 'https://via.placeholder.com/48x48.png?text=👤'
    },
    url: elkUrl, // Use ELK-compatible URL for navigation
    uri: rec.uri || postUrl, // Keep original URI
    favourites_count: rec.favourites_count || rec.favorites_count || 0,
    reblogs_count: rec.reblogs_count || rec.boosts_count || 0,
    replies_count: rec.replies_count || 0,
    language: rec.language || 'en',
    visibility: rec.visibility || 'public',
    media_attachments: rec.media_attachments || [],
    mentions: rec.mentions || [],
    tags: rec.tags || [],
    emojis: rec.emojis || [],
    card: rec.card || null,
    is_recommendation: true,
    recommendation_reason: rec.recommendation_reason || rec.reason || 'AI recommended based on your interests',
    recommendation_score: rec.score || rec.recommendation_score || 0.5
  }
}

export function useCorgiSeamless() {
  // Configuration
  const config = ref<CorgiConfig>({
    apiUrl: process.env.CORGI_API_URL || 'http://localhost:5002',
    enabled: true,
    proxyMode: true
  })

  // State
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const recommendations = ref<CorgiRecommendation[]>([])
  const lastFetchTime = ref<Date | null>(null)

  // Computed
  const isHealthy = computed(() => error.value === null)
  const hasRecommendations = computed(() => recommendations.value.length > 0)

  // API functions
  async function checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${config.value.apiUrl}/health`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      
      const data = await response.json()
      error.value = null
      return data.status === 'healthy'
    } catch (err) {
      error.value = `Health check failed: ${err instanceof Error ? err.message : 'Unknown error'}`
      return false
    }
  }

  async function fetchRecommendations(count = 20, userId?: string): Promise<CorgiRecommendation[]> {
    // Use provided userId or get current user
    const actualUserId = userId || getCurrentUserId()
    isLoading.value = true
    error.value = null

    try {
      const response = await fetch(`${config.value.apiUrl}/api/v1/recommendations?limit=${count}&user_id=${actualUserId}`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch recommendations: HTTP ${response.status}`)
      }

      const data = await response.json()
      
      // Ensure data is in expected format
      const recs = Array.isArray(data) ? data : (data.recommendations || [])
      
      recommendations.value = recs.map((rec: any) => transformToMastodonPost(rec))

      lastFetchTime.value = new Date()
      return recommendations.value
      
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch recommendations'
      console.error('Corgi recommendations error:', err)
      return []
    } finally {
      isLoading.value = false
    }
  }

  async function fetchTimeline(endpoint = 'home', params: Record<string, any> = {}): Promise<CorgiRecommendation[]> {
    isLoading.value = true
    error.value = null

    try {
      const searchParams = new URLSearchParams()
      
      // Add default user_id if not provided - use current authenticated user
      if (!params.user_id) {
        params.user_id = getCurrentUserId()
      }
      
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value))
        }
      })

      const url = `${config.value.apiUrl}/api/v1/timelines/${endpoint}?${searchParams}`
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch timeline: HTTP ${response.status}`)
      }

      const data = await response.json()
      const timeline = Array.isArray(data) ? data : []
      
      // Transform timeline posts to ensure they're Mastodon-compatible
      const transformedTimeline = timeline.map((post: any) => transformToMastodonPost(post))
      
      lastFetchTime.value = new Date()
      return transformedTimeline
      
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch timeline'
      console.error('Corgi timeline error:', err)
      return []
    } finally {
      isLoading.value = false
    }
  }

  async function logInteraction(postId: string, action: string, details: Record<string, any> = {}): Promise<void> {
    try {
      await fetch(`${config.value.apiUrl}/api/v1/interactions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: details.user_id || getCurrentUserId(),
          post_id: postId,
          action_type: action,
          timestamp: new Date().toISOString(),
          context: {
            source: 'elk_corgi_integration',
            ...details
          }
        })
      })
    } catch (err) {
      console.warn('Failed to log interaction:', err)
      // Don't throw - interaction logging is non-critical
    }
  }

  // Lifecycle
  let healthCheckInterval: NodeJS.Timeout | null = null

  onMounted(() => {
    // Initial health check
    checkHealth()
    
    // Periodic health checks every 30 seconds
    healthCheckInterval = setInterval(checkHealth, 30000)
  })

  onUnmounted(() => {
    if (healthCheckInterval) {
      clearInterval(healthCheckInterval)
    }
  })

  // Return public API
  return {
    // Configuration
    config: readonly(config),
    
    // State
    isLoading: readonly(isLoading),
    error: readonly(error),
    recommendations: readonly(recommendations),
    lastFetchTime: readonly(lastFetchTime),
    
    // Computed
    isHealthy,
    hasRecommendations,
    
    // Methods
    checkHealth,
    fetchRecommendations,
    fetchTimeline,
    logInteraction,
    
    // Utilities
    updateConfig: (newConfig: Partial<CorgiConfig>) => {
      config.value = { ...config.value, ...newConfig }
    }
  }
}

// Helper function to inject Corgi recommendations into a timeline
export function injectRecommendations(
  timeline: any[], 
  recommendations: CorgiRecommendation[], 
  ratio = 0.3 // 30% of posts should be recommendations
): any[] {
  if (!recommendations.length) return timeline

  const combined = [...timeline]
  const recCount = Math.floor(timeline.length * ratio)
  const selectedRecs = recommendations.slice(0, recCount)

  // Inject recommendations at natural intervals
  selectedRecs.forEach((rec, index) => {
    const insertIndex = Math.floor((index + 1) * (timeline.length / selectedRecs.length))
    combined.splice(insertIndex + index, 0, rec)
  })

  return combined
}

// Export default for convenience
export default useCorgiSeamless 