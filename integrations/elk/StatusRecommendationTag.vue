<script setup lang="ts">
import type { mastodon } from 'masto'

interface Props {
  status: mastodon.v1.Status & {
    is_recommendation?: boolean
    recommendation_reason?: string
    reason_detail?: string
    recommendation_score?: number
  }
}

const props = defineProps<Props>()

// Transform generic reasons into specific, user-friendly messages
const getSpecificReasonText = () => {
  const reasonDetail = props.status.reason_detail || props.status.recommendation_reason
  
  if (!reasonDetail) {
    return 'Recommended for you'
  }
  
  // Handle specific hashtag trending
  if (reasonDetail.startsWith('Trending in #')) {
    return reasonDetail
  }
  
  // Handle specific author network reasons
  if (reasonDetail.startsWith('Popular among followers of @')) {
    return reasonDetail
  }
  
  // Handle instance-specific trending
  if (reasonDetail.startsWith('Trending on ') || reasonDetail.startsWith('Popular on ')) {
    return reasonDetail
  }
  
  // Handle specific author interactions
  if (reasonDetail.includes('Because you liked a post by this author')) {
    return 'Because you liked a post by this author'
  }
  
  // Transform generic reasons with more context
  switch (reasonDetail) {
    case 'Trending in topics you follow':
      // Try to get more specific if we have tags
      if (props.status.tags && props.status.tags.length > 0) {
        const firstTag = props.status.tags[0].name
        return `Trending in #${firstTag}`
      }
      return 'Trending in topics you follow'
      
    case 'Popular in your network':
      return 'Popular in your network'
      
    case 'Based on posts you\'ve liked':
      return 'Based on posts you\'ve liked'
      
    default:
      return reasonDetail
  }
}

// Get appropriate icon for the recommendation reason
const getReasonIcon = () => {
  const reasonDetail = props.status.reason_detail || props.status.recommendation_reason || ''
  
  if (reasonDetail.includes('Trending') || reasonDetail.includes('trending')) {
    return 'i-ri:fire-fill'
  }
  
  if (reasonDetail.includes('Popular') || reasonDetail.includes('followers')) {
    return 'i-ri:group-fill'
  }
  
  if (reasonDetail.includes('liked') || reasonDetail.includes('author')) {
    return 'i-ri:heart-fill'
  }
  
  if (reasonDetail.includes('#')) {
    return 'i-ri:hashtag'
  }
  
  return 'i-ri:star-fill'
}

// Get color class based on recommendation score
const getScoreColorClass = () => {
  const score = props.status.recommendation_score || 0
  
  if (score > 0.8) return 'text-green-600 dark:text-green-400'
  if (score > 0.6) return 'text-blue-600 dark:text-blue-400'
  if (score > 0.4) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-gray-600 dark:text-gray-400'
}
</script>

<template>
  <div
    v-if="status.is_recommendation"
    class="absolute top-2 right-2 z-10 flex gap-1 items-center rounded-full bg-primary bg-opacity-10 dark:bg-opacity-20 backdrop-blur-sm border border-primary border-opacity-20 text-primary text-xs font-medium px-2 py-1 shadow-sm"
  >
    <!-- Recommendation icon -->
    <div :class="getReasonIcon()" class="w-3 h-3" />
    
    <!-- Specific reason text -->
    <span class="max-w-32 truncate" :title="getSpecificReasonText()">
      {{ getSpecificReasonText() }}
    </span>
    
    <!-- Optional: Show recommendation score as a subtle indicator -->
    <span 
      v-if="status.recommendation_score && status.recommendation_score > 0"
      :class="getScoreColorClass()"
      class="ml-1 text-xs opacity-75"
      :title="`Recommendation score: ${(status.recommendation_score * 100).toFixed(0)}%`"
    >
      •
    </span>
  </div>
</template>

<style scoped>
/* Additional hover effects for better UX */
.absolute:hover {
  transform: scale(1.05);
  transition: transform 0.2s ease-in-out;
}

/* Ensure text is readable on various backgrounds */
.backdrop-blur-sm {
  backdrop-filter: blur(4px);
}

/* Responsive text sizing */
@media (max-width: 640px) {
  .max-w-32 {
    max-width: 6rem;
  }
}
</style> 