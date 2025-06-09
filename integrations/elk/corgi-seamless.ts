/**
 * Corgi Seamless Integration Composable for ELK
 * 
 * This composable provides seamless integration between ELK and Corgi
 * recommendations, making AI recommendations appear naturally in timelines.
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'

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
      recommendation_reason: rec.recommendation_reason || rec.reason || 'AI recommended based on your interests'
    }
  }

  // If it's a stub post, create a full Mastodon-compatible structure
  const postId = rec.id || `rec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  const authorId = rec.author_id || `user_${Math.random().toString(36).substr(2, 6)}`
  const authorName = rec.author_name || `User ${authorId.slice(-4)}`
  
  return {
    id: postId,
    uri: `https://example.com/posts/${postId}`,
    url: `https://example.com/posts/${postId}`,
    account: {
      id: authorId,
      username: authorName.toLowerCase().replace(/\s+/g, ''),
      acct: `${authorName.toLowerCase().replace(/\s+/g, '')}@example.com`,
      display_name: authorName,
      avatar: `https://avatar.oxro.io/avatar.svg?name=${encodeURIComponent(authorName)}&background=random`,
      url: `https://example.com/@${authorName.toLowerCase().replace(/\s+/g, '')}`
    },
    content: rec.content || 'AI-generated recommendation content',
    created_at: rec.created_at || new Date().toISOString(),
    reblog: null,
    media_attachments: rec.media_attachments || [],
    replies_count: rec.replies_count || 0,
    reblogs_count: rec.reblogs_count || 0,
    favourites_count: rec.favourites_count || 0,
    favourited: rec.favourited || false,
    reblogged: rec.reblogged || false,
    is_recommendation: true,
    recommendation_reason: rec.recommendation_reason || rec.reason || 'AI recommended based on your interests'
  }
}

export function useCorgiSeamless() {
  // Configuration
  const config = ref<CorgiConfig>({
    apiUrl: process.env.CORGI_API_URL || 'http://localhost:9999',
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

  async function fetchRecommendations(count = 20, userId = 'demo_user'): Promise<CorgiRecommendation[]> {
    isLoading.value = true
    error.value = null

    try {
      const response = await fetch(`${config.value.apiUrl}/api/v1/recommendations?limit=${count}&user_id=${userId}`)
      
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
      
      // Add default user_id if not provided
      if (!params.user_id) {
        params.user_id = 'demo_user'
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
          post_id: postId,
          action,
          timestamp: new Date().toISOString(),
          ...details
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