/**
 * Interaction Count Diagnostics Utility
 *
 * This utility helps debug and test real-time interaction count updates.
 * It can be used to log and track changes in interaction counts over time.
 */

class InteractionCountDiagnostics {
  constructor() {
    this.enabled = false
    this.stats = {
      totalRefreshes: 0,
      totalPostsUpdated: 0,
      totalChangesDetected: 0,
      lastUpdateTime: null,
      changesByPost: {},
      changesByType: {
        favorites: 0,
        reblogs: 0,
        replies: 0,
        bookmarks: 0,
      },
      refreshHistory: [],
      lastPollingDuration: 0,
    }
  }

  /**
   * Enable or disable diagnostics
   * @param {boolean} enabled - Whether to enable diagnostics
   */
  setEnabled(enabled) {
    this.enabled = enabled
    if (enabled) {
      console.log('🧪 Interaction count diagnostics enabled')
    }
    else {
      console.log('🧪 Interaction count diagnostics disabled')
    }
    return this
  }

  /**
   * Record a refresh attempt
   * @param {string} source - Optional source of the refresh
   */
  recordRefresh(source = 'polling') {
    if (!this.enabled)
      return

    this.stats.totalRefreshes++
    this.stats.lastUpdateTime = new Date().toISOString()
    this.stats.refreshHistory.push({
      time: this.stats.lastUpdateTime,
      source,
    })

    // Limit history to last 20 entries
    if (this.stats.refreshHistory.length > 20) {
      this.stats.refreshHistory.shift()
    }

    console.log(`🔄 [${this.stats.totalRefreshes}] Interaction count refresh from ${source}`)
    return this
  }

  /**
   * Set the duration of the last polling operation
   * @param {number} duration - Time in milliseconds
   */
  setPollingDuration(duration) {
    if (!this.enabled)
      return
    this.stats.lastPollingDuration = duration
    console.log(`⏱️ Polling took ${duration}ms`)
    return this
  }

  /**
   * Record a post update
   * @param {string} postId - ID of the post
   * @param {boolean} hasChanges - Whether any counts changed
   */
  recordPostUpdate(postId, hasChanges) {
    if (!this.enabled)
      return

    this.stats.totalPostsUpdated++

    if (hasChanges) {
      this.stats.totalChangesDetected++
      this.stats.changesByPost[postId] = (this.stats.changesByPost[postId] || 0) + 1
      console.log(`📊 Post ${postId} had changes (updated ${this.stats.changesByPost[postId]} times)`)
    }
    return this
  }

  /**
   * Record a change in a specific count type
   * @param {string} type - Type of interaction (favorites, reblogs, etc.)
   * @param {number} delta - Change amount
   */
  recordCountChange(type, delta) {
    if (!this.enabled || delta === 0)
      return

    this.stats.changesByType[type] = (this.stats.changesByType[type] || 0) + Math.abs(delta)
    console.log(`📈 ${type} changed by ${delta > 0 ? '+' : ''}${delta}`)
    return this
  }

  /**
   * Get all collected statistics
   * @returns {object} Statistics object
   */
  getStats() {
    return this.stats
  }

  /**
   * Print a summary of diagnostics to console
   */
  printSummary() {
    if (!this.enabled) {
      console.log('Diagnostics are disabled. Enable with setEnabled(true)')
      return
    }

    console.log('=== Interaction Count Diagnostics Summary ===')
    console.log(`Total refreshes: ${this.stats.totalRefreshes}`)
    console.log(`Posts updated: ${this.stats.totalPostsUpdated}`)
    console.log(`Changes detected: ${this.stats.totalChangesDetected}`)
    console.log(`Last update: ${this.stats.lastUpdateTime}`)

    console.log('\nChanges by type:')
    Object.entries(this.stats.changesByType).forEach(([type, count]) => {
      console.log(`- ${type}: ${count}`)
    })

    console.log('\nMost frequently changed posts:')
    const sortedPosts = Object.entries(this.stats.changesByPost)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)

    if (sortedPosts.length === 0) {
      console.log('No post changes detected yet')
    }
    else {
      sortedPosts.forEach(([postId, count]) => {
        console.log(`- ${postId}: ${count} changes`)
      })
    }

    console.log('\nLast polling duration:', this.stats.lastPollingDuration, 'ms')
    console.log('=======================================')
  }

  /**
   * Reset all statistics
   */
  reset() {
    this.stats = {
      totalRefreshes: 0,
      totalPostsUpdated: 0,
      totalChangesDetected: 0,
      lastUpdateTime: null,
      changesByPost: {},
      changesByType: {
        favorites: 0,
        reblogs: 0,
        replies: 0,
        bookmarks: 0,
      },
      refreshHistory: [],
      lastPollingDuration: 0,
    }
    console.log('🧹 Interaction count diagnostics reset')
    return this
  }
}

// Export a singleton instance
export const interactionDiagnostics = new InteractionCountDiagnostics()

// Also export the class for testing or multiple instances
export default InteractionCountDiagnostics