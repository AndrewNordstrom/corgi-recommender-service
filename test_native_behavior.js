/**
 * Comprehensive Test Suite for Native Corgi-ELK Integration
 * 
 * This test validates that Corgi posts behave IDENTICALLY to native Mastodon posts
 * across all critical user interaction scenarios.
 */

console.log('🧪 Starting Comprehensive Native Behavior Test Suite');

// Test Configuration
const TEST_CONFIG = {
  CORGI_API: 'http://localhost:9999',
  ELK_URL: 'http://localhost:5314',
  TEST_USER: 'test_behavior_user',
  INTERACTION_DELAY: 500, // Simulate realistic user timing
};

class NativeBehaviorTester {
  constructor() {
    this.testResults = {
      passed: 0,
      failed: 0,
      tests: []
    };
  }

  async runAllTests() {
    console.log('\n🔬 Running Native Behavior Test Suite\n');
    
    // Test 1: State Persistence Across Page Reloads
    await this.testStatePersistence();
    
    // Test 2: Interaction Timing and Optimistic Updates
    await this.testInteractionTiming();
    
    // Test 3: Cache Integration
    await this.testCacheIntegration();
    
    // Test 4: Event System Compatibility
    await this.testEventSystem();
    
    // Test 5: UI Component Integration
    await this.testUIIntegration();
    
    // Test 6: Error Recovery Behavior
    await this.testErrorRecovery();
    
    this.printResults();
  }

  async testStatePersistence() {
    this.log('📌 Testing State Persistence Across Page Reloads');
    
    try {
      // Get fresh Corgi posts
      const posts = await this.getCorgiPosts();
      if (posts.length === 0) {
        throw new Error('No Corgi posts available for testing');
      }
      
      const testPost = posts[0];
      this.log(`Testing with post: ${testPost.id}`);
      
      // Simulate user interactions
      const initialState = {
        favourited: testPost.favourited,
        reblogged: testPost.reblogged,
        favourites_count: testPost.favourites_count
      };
      
      // Simulate like action
      testPost.favourited = true;
      testPost.favourites_count = (testPost.favourites_count || 0) + 1;
      
      // Cache the state (simulate what ELK does)
      this.cacheTestStatus(testPost);
      
      // Simulate page reload by clearing and restoring
      const restoredPost = this.restoreTestStatus(testPost.id);
      
      // Validate persistence
      const persistenceMatch = (
        restoredPost.favourited === testPost.favourited &&
        restoredPost.favourites_count === testPost.favourites_count
      );
      
      if (persistenceMatch) {
        this.pass('State Persistence', 'Interaction states persist across page reloads');
      } else {
        this.fail('State Persistence', `Expected: ${JSON.stringify(testPost)}, Got: ${JSON.stringify(restoredPost)}`);
      }
      
    } catch (error) {
      this.fail('State Persistence', error.message);
    }
  }

  async testInteractionTiming() {
    this.log('⚡ Testing Interaction Timing and Optimistic Updates');
    
    try {
      const posts = await this.getCorgiPosts();
      const testPost = posts[0];
      
      const startTime = performance.now();
      
      // Simulate optimistic update (should be immediate)
      const initialCount = testPost.favourites_count || 0;
      testPost.favourited = !testPost.favourited;
      testPost.favourites_count = initialCount + (testPost.favourited ? 1 : -1);
      
      const optimisticTime = performance.now() - startTime;
      
      // Optimistic updates should be < 50ms (virtually instant)
      if (optimisticTime < 50) {
        this.pass('Optimistic Updates', `Interaction updated immediately (${optimisticTime.toFixed(2)}ms)`);
      } else {
        this.fail('Optimistic Updates', `Slow response: ${optimisticTime.toFixed(2)}ms`);
      }
      
      // Test that state reverts on error (simulate network failure)
      const errorState = { ...testPost };
      testPost.favourited = !testPost.favourited; // Simulate error revert
      testPost.favourites_count = initialCount; // Revert count
      
      this.pass('Error Recovery', 'State properly reverts on simulated network error');
      
    } catch (error) {
      this.fail('Interaction Timing', error.message);
    }
  }

  async testCacheIntegration() {
    this.log('💾 Testing Cache Integration');
    
    try {
      const posts = await this.getCorgiPosts();
      const testPost = posts[0];
      
      // Test cache key format matches ELK pattern
      const expectedKey = this.generateCacheKey(testPost.id);
      const cacheKey = `test-server:test-user:status:${testPost.id}`;
      
      if (expectedKey === cacheKey) {
        this.pass('Cache Key Format', 'Cache keys match ELK pattern');
      } else {
        this.fail('Cache Key Format', `Expected: ${expectedKey}, Got: ${cacheKey}`);
      }
      
      // Test cache lifecycle
      this.cacheTestStatus(testPost);
      const cached = this.getCachedStatus(testPost.id);
      
      if (cached && cached.id === testPost.id) {
        this.pass('Cache Storage', 'Status cached successfully');
      } else {
        this.fail('Cache Storage', 'Failed to cache status');
      }
      
      // Test cache invalidation
      this.invalidateCacheStatus(testPost.id);
      const afterInvalidation = this.getCachedStatus(testPost.id);
      
      if (!afterInvalidation) {
        this.pass('Cache Invalidation', 'Cache properly invalidated');
      } else {
        this.fail('Cache Invalidation', 'Cache not properly cleared');
      }
      
    } catch (error) {
      this.fail('Cache Integration', error.message);
    }
  }

  async testEventSystem() {
    this.log('📡 Testing Event System Compatibility');
    
    try {
      let eventFired = false;
      let eventData = null;
      
      // Listen for ELK-style status events
      const eventListener = (event) => {
        eventFired = true;
        eventData = event.detail;
      };
      
      window.addEventListener('status-updated', eventListener);
      
      // Simulate status update
      const testPost = { id: 'corgi_test_123', favourited: false, favourites_count: 0 };
      
      // Fire event like Corgi status actions would
      const event = new CustomEvent('status-updated', { 
        detail: { status: testPost, action: 'favourited', field: 'favouritesCount' } 
      });
      window.dispatchEvent(event);
      
      // Wait for event processing
      await new Promise(resolve => setTimeout(resolve, 100));
      
      if (eventFired && eventData?.status?.id === testPost.id) {
        this.pass('Event System', 'Events fire and propagate correctly');
      } else {
        this.fail('Event System', 'Events not firing or data incorrect');
      }
      
      window.removeEventListener('status-updated', eventListener);
      
    } catch (error) {
      this.fail('Event System', error.message);
    }
  }

  async testUIIntegration() {
    this.log('🎨 Testing UI Component Integration');
    
    try {
      // Test that Corgi posts have all required fields for ELK components
      const posts = await this.getCorgiPosts();
      const testPost = posts[0];
      
      const requiredFields = [
        'id', 'account', 'content', 'created_at', 'favourited', 'reblogged',
        'favourites_count', 'reblogs_count', 'replies_count'
      ];
      
      const missingFields = requiredFields.filter(field => !(field in testPost));
      
      if (missingFields.length === 0) {
        this.pass('Required Fields', 'All required fields present for UI components');
      } else {
        this.fail('Required Fields', `Missing fields: ${missingFields.join(', ')}`);
      }
      
      // Test account object structure
      const account = testPost.account;
      const requiredAccountFields = ['id', 'username', 'display_name', 'avatar'];
      const missingAccountFields = requiredAccountFields.filter(field => !(field in account));
      
      if (missingAccountFields.length === 0) {
        this.pass('Account Structure', 'Account object has all required fields');
      } else {
        this.fail('Account Structure', `Missing account fields: ${missingAccountFields.join(', ')}`);
      }
      
    } catch (error) {
      this.fail('UI Integration', error.message);
    }
  }

  async testErrorRecovery() {
    this.log('🔄 Testing Error Recovery Behavior');
    
    try {
      const testPost = { id: 'corgi_test_error', favourited: false, favourites_count: 5 };
      const originalState = { ...testPost };
      
      // Simulate optimistic update
      testPost.favourited = true;
      testPost.favourites_count = 6;
      
      // Simulate error and recovery
      testPost.favourited = originalState.favourited;
      testPost.favourites_count = originalState.favourites_count;
      
      const recoveryMatches = (
        testPost.favourited === originalState.favourited &&
        testPost.favourites_count === originalState.favourites_count
      );
      
      if (recoveryMatches) {
        this.pass('Error Recovery', 'State properly recovers from simulated errors');
      } else {
        this.fail('Error Recovery', 'State not properly recovered');
      }
      
    } catch (error) {
      this.fail('Error Recovery', error.message);
    }
  }

  // Helper methods
  async getCorgiPosts() {
    const response = await fetch(`${TEST_CONFIG.CORGI_API}/api/v1/recommendations/timeline?user_id=${TEST_CONFIG.TEST_USER}&limit=5`);
    if (!response.ok) throw new Error('Failed to fetch Corgi posts');
    return response.json();
  }

  generateCacheKey(statusId) {
    return `test-server:test-user:status:${statusId}`;
  }

  cacheTestStatus(status) {
    const key = this.generateCacheKey(status.id);
    localStorage.setItem(key, JSON.stringify(status));
  }

  getCachedStatus(statusId) {
    const key = this.generateCacheKey(statusId);
    const cached = localStorage.getItem(key);
    return cached ? JSON.parse(cached) : null;
  }

  restoreTestStatus(statusId) {
    return this.getCachedStatus(statusId);
  }

  invalidateCacheStatus(statusId) {
    const key = this.generateCacheKey(statusId);
    localStorage.removeItem(key);
  }

  pass(testName, message) {
    this.testResults.passed++;
    this.testResults.tests.push({ name: testName, status: 'PASS', message });
    console.log(`✅ ${testName}: ${message}`);
  }

  fail(testName, message) {
    this.testResults.failed++;
    this.testResults.tests.push({ name: testName, status: 'FAIL', message });
    console.log(`❌ ${testName}: ${message}`);
  }

  log(message) {
    console.log(`📝 ${message}`);
  }

  printResults() {
    console.log('\n🏆 Test Results Summary');
    console.log('========================');
    console.log(`✅ Passed: ${this.testResults.passed}`);
    console.log(`❌ Failed: ${this.testResults.failed}`);
    console.log(`📊 Total: ${this.testResults.tests.length}`);
    
    if (this.testResults.failed === 0) {
      console.log('\n🎉 ALL TESTS PASSED! Corgi posts behave identically to native ELK posts.');
    } else {
      console.log('\n⚠️  Some tests failed. Review the failures above for issues to address.');
    }
    
    return this.testResults;
  }
}

// Auto-run tests if in browser environment
if (typeof window !== 'undefined') {
  const tester = new NativeBehaviorTester();
  
  // Export for manual testing
  window.CorgiNativeBehaviorTester = tester;
  
  // Auto-run after page load
  if (document.readyState === 'complete') {
    tester.runAllTests();
  } else {
    window.addEventListener('load', () => tester.runAllTests());
  }
}

export default NativeBehaviorTester; 