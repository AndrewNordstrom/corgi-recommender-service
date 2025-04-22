# Live Demo

Experience Corgi in action with our interactive live demo. No setup required—just click and explore!

<div class="corgi-live-demo">
  <div class="demo-header">
    <h2>Corgi Recommendation Demo</h2>
    <div class="demo-controls">
      <button id="demo-refresh-btn" class="corgi-button">Refresh Timeline</button>
      <button id="demo-reset-btn" class="corgi-button" style="margin-left:5px">Reset Demo</button>
    </div>
  </div>
  
  <div class="demo-user-bar">
    <div class="demo-user">
      <div class="demo-avatar"></div>
      <div class="demo-user-info">
        <div class="demo-username">DemoUser</div>
        <div class="demo-instance">@demo_user@mastodon.social</div>
      </div>
    </div>
  </div>
  
  <div class="demo-tabs">
    <div class="demo-tab active" data-view="timeline">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>
      <span>Timeline</span>
    </div>
    <div class="demo-tab" data-view="recommendations">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M17 3H7c-1.1 0-2 .9-2 2v16l7-3 7 3V5c0-1.1-.9-2-2-2z"/></svg>
      <span>Recommendations</span>
    </div>
    <div class="demo-tab" data-view="api">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm-5 14H4v-4h11v4zm0-5H4V9h11v4zm5 5h-4V9h4v9z"/></svg>
      <span>API Calls</span>
    </div>
  </div>
  
  <div class="demo-container">
    <div class="demo-content">
      <div class="demo-view" id="demo-timeline-view">
        <div class="demo-section-header">
          <h3>Enhanced Timeline</h3>
          <span class="demo-badge">Live Demo</span>
        </div>
        <div class="demo-timeline" id="demo-timeline">
          <div class="demo-loading">
            <div class="demo-loading-icon">
              <svg class="spin" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 4V2A10 10 0 0 0 2 12h2a8 8 0 0 1 8-8z"/></svg>
            </div>
            <div class="demo-loading-text">Login to view timeline</div>
          </div>
        </div>
      </div>
      
      <div class="demo-view hidden" id="demo-recommendations-view">
        <div class="demo-section-header">
          <h3>Personalized Recommendations</h3>
          <span class="demo-badge">Live Demo</span>
        </div>
        <div class="demo-recommendations" id="demo-recommendations">
          <div class="demo-loading">
            <div class="demo-loading-icon">
              <svg class="spin" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 4V2A10 10 0 0 0 2 12h2a8 8 0 0 1 8-8z"/></svg>
            </div>
            <div class="demo-loading-text">Login to view recommendations</div>
          </div>
        </div>
      </div>
      
      <div class="demo-view hidden" id="demo-api-view">
        <div class="demo-section-header">
          <h3>Recent API Calls</h3>
          <span class="demo-badge">Live Demo</span>
        </div>
        <div class="demo-api-log" id="demo-api-log">
          <div class="demo-api-empty">No API calls logged yet</div>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="corgi-card" style="margin-top: 2rem;">
  <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 1.5rem;">
    <div style="flex: 1; min-width: 280px;">
      <h3 style="margin-top: 0;">🔎 How this demo works</h3>
      <p>This interactive demo uses pre-loaded content to simulate a Corgi instance. When you login as the demo user:</p>
      <ol>
        <li>We retrieve a simulated home timeline with blended recommendations</li>
        <li>We fetch personalized recommendations based on the demo user's interaction history</li>
        <li>All API calls are logged so you can see how Corgi's API works</li>
      </ol>
      <p>You can interact with posts by clicking the favorite or reblog buttons to see how that affects recommendations over time.</p>
    </div>
    <div style="flex-shrink: 0; text-align: center;">
      <img src="assets/corgi-hero.png" alt="Corgi Hero" width="180" style="margin-bottom: 0.5rem;">
    </div>
  </div>
</div>

## Behind the Scenes

This demo showcases how Corgi seamlessly blends recommendations into a Mastodon timeline. In a real-world integration:

1. A Mastodon client connects to Corgi's proxy API instead of directly to a Mastodon instance
2. Corgi forwards timeline requests to the appropriate Mastodon instance
3. Corgi analyzes the response and injects personalized recommendations
4. The enhanced timeline is returned to the client in Mastodon-compatible format

The recommendations evolve based on your interactions - favorites, boosts, explicit feedback, and more.

## Try it with your own data

Ready to see Corgi work with your actual Mastodon account? Check out our [Quickstart Guide](quickstart.md) to set up your own instance in just a few minutes!

<script type="text/javascript">
// This script will be executed when the page loads
document.addEventListener('DOMContentLoaded', function() {
  // Demo data
  const demoUser = {
    id: 'demo_user_123',
    username: 'DemoUser',
    instance: 'mastodon.social',
    avatar: 'https://source.boringavatars.com/beam/120/DemoUser?colors=ffb300,ff8f00,ffca28,ffe082,fff8e1'
  };
  
  // Auto-login on page load
  let isLoggedIn = true;
  
  const demoTimeline = [
    {
      id: 'post_001',
      content: '<p>Just published a new article on decentralized social networks and the future of the Fediverse! <a href="#">Read it here</a></p>',
      created_at: '2025-03-15T14:22:11.000Z',
      account: {
        id: 'user001',
        username: 'techwriter',
        display_name: 'Tech Writer',
        avatar: 'https://source.boringavatars.com/beam/120/user001?colors=ffb300,ff8f00,ffca28,ffe082,fff8e1'
      },
      is_recommendation: true,
      recommendation_reason: 'From an author you might like',
      favorited: false,
      reblogged: false,
      replies_count: 12,
      reblogs_count: 28,
      favourites_count: 43
    },
    {
      id: 'post_002',
      content: '<p>Check out our latest open source contribution to the Fediverse! We\'ve added new accessibility features to our Mastodon client.</p>',
      created_at: '2025-03-15T13:45:22.000Z',
      account: {
        id: 'user002',
        username: 'fediversedev',
        display_name: 'Fediverse Developer',
        avatar: 'https://source.boringavatars.com/beam/120/user002?colors=ffb300,ff8f00,ffca28,ffe082,fff8e1'
      },
      is_recommendation: false,
      favorited: false,
      reblogged: false,
      replies_count: 7,
      reblogs_count: 41,
      favourites_count: 62
    },
    {
      id: 'post_003',
      content: '<p>Excited to announce that our app now supports the new Fediverse recommendation protocol! 🎉</p>',
      created_at: '2025-03-15T12:30:45.000Z',
      account: {
        id: 'user003',
        username: 'productmanager',
        display_name: 'Product Manager',
        avatar: 'https://source.boringavatars.com/beam/120/user003?colors=ffb300,ff8f00,ffca28,ffe082,fff8e1'
      },
      is_recommendation: true,
      recommendation_reason: 'Popular with other users',
      favorited: false,
      reblogged: false,
      replies_count: 15,
      reblogs_count: 76,
      favourites_count: 124
    },
    {
      id: 'post_004',
      content: '<p>Today\'s programming tip: Use pseudonymization techniques to enhance user privacy while still enabling personalization features! 💡</p>',
      created_at: '2025-03-15T11:20:33.000Z',
      account: {
        id: 'user004',
        username: 'coder',
        display_name: 'Coding Tips',
        avatar: 'https://source.boringavatars.com/beam/120/user004?colors=ffb300,ff8f00,ffca28,ffe082,fff8e1'
      },
      is_recommendation: false,
      favorited: false,
      reblogged: false,
      replies_count: 5,
      reblogs_count: 32,
      favourites_count: 87
    },
    {
      id: 'post_005',
      content: '<p>Here\'s my latest sketch - a futuristic Fediverse interface concept where recommendations blend seamlessly with your timeline! <a href="#">#DesignConcept</a></p>',
      created_at: '2025-03-15T10:15:20.000Z',
      account: {
        id: 'user005',
        username: 'uidesigner',
        display_name: 'UI Designer',
        avatar: 'https://source.boringavatars.com/beam/120/user005?colors=ffb300,ff8f00,ffca28,ffe082,fff8e1'
      },
      is_recommendation: true,
      recommendation_reason: 'Recently trending',
      favorited: false,
      reblogged: false,
      replies_count: 9,
      reblogs_count: 24,
      favourites_count: 98
    }
  ];
  
  const demoRecommendations = [
    {
      id: 'rec_001',
      content: '<p>The intersection of privacy and personalization is the next frontier for social media. We need to design systems that respect user autonomy.</p>',
      created_at: '2025-03-15T12:10:45.000Z',
      account: {
        id: 'user006',
        username: 'privacyadvocate',
        display_name: 'Privacy Advocate',
        avatar: 'https://source.boringavatars.com/beam/120/user006?colors=ffb300,ff8f00,ffca28,ffe082,fff8e1'
      },
      recommendation_reason: 'Based on your interests',
      ranking_score: 0.89,
      favorited: false,
      reblogged: false,
      replies_count: 18,
      reblogs_count: 45,
      favourites_count: 132
    },
    {
      id: 'rec_002',
      content: '<p>Just released a new library for building middleware applications on top of ActivityPub! Perfect for adding custom features to Mastodon.</p>',
      created_at: '2025-03-15T11:45:22.000Z',
      account: {
        id: 'user007',
        username: 'opensourcedev',
        display_name: 'Open Source Developer',
        avatar: 'https://source.boringavatars.com/beam/120/user007?colors=ffb300,ff8f00,ffca28,ffe082,fff8e1'
      },
      recommendation_reason: 'From an author you might like',
      ranking_score: 0.85,
      favorited: false,
      reblogged: false,
      replies_count: 7,
      reblogs_count: 36,
      favourites_count: 89
    },
    {
      id: 'rec_003',
      content: '<p>How we built our recommendation engine to be privacy-preserving from day one - new blog post with all the technical details!</p>',
      created_at: '2025-03-15T10:30:15.000Z',
      account: {
        id: 'user008',
        username: 'datascienceethics',
        display_name: 'Data Science Ethics',
        avatar: 'https://source.boringavatars.com/beam/120/user008?colors=ffb300,ff8f00,ffca28,ffe082,fff8e1'
      },
      recommendation_reason: 'Trending in your network',
      ranking_score: 0.81,
      favorited: false,
      reblogged: false,
      replies_count: 12,
      reblogs_count: 54,
      favourites_count: 117
    },
    {
      id: 'rec_004',
      content: '<p>The key to good recommendations isn\'t just algorithms—it\'s transparency. Users should always know why something is recommended to them.</p>',
      created_at: '2025-03-15T09:20:10.000Z',
      account: {
        id: 'user009',
        username: 'userexperience',
        display_name: 'UX Researcher',
        avatar: 'https://source.boringavatars.com/beam/120/user009?colors=ffb300,ff8f00,ffca28,ffe082,fff8e1'
      },
      recommendation_reason: 'Similar to posts you\'ve engaged with',
      ranking_score: 0.78,
      favorited: false,
      reblogged: false,
      replies_count: 9,
      reblogs_count: 28,
      favourites_count: 93
    },
    {
      id: 'rec_005',
      content: '<p>Announcement: Our next community call will focus on open standards for recommendation sharing across Fediverse instances. Join us!</p>',
      created_at: '2025-03-15T08:15:05.000Z',
      account: {
        id: 'user010',
        username: 'fediverseorg',
        display_name: 'Fediverse Organization',
        avatar: 'https://source.boringavatars.com/beam/120/user010?colors=ffb300,ff8f00,ffca28,ffe082,fff8e1'
      },
      recommendation_reason: 'Popular with users like you',
      ranking_score: 0.75,
      favorited: false,
      reblogged: false,
      replies_count: 14,
      reblogs_count: 67,
      favourites_count: 145
    }
  ];
  
  const apiCalls = [
    {
      id: 'api_001',
      method: 'GET',
      endpoint: '/api/v1/timelines/home',
      headers: {
        'Authorization': 'Bearer <redacted>',
        'X-Mastodon-Instance': 'mastodon.social'
      },
      query_params: {
        limit: 20
      },
      response_status: 200,
      timestamp: '2025-03-15T14:30:00.000Z'
    },
    {
      id: 'api_002',
      method: 'GET',
      endpoint: '/api/v1/recommendations',
      headers: {
        'Authorization': 'Bearer <redacted>'
      },
      query_params: {
        user_id: 'demo_user_123',
        limit: 5
      },
      response_status: 200,
      timestamp: '2025-03-15T14:30:01.000Z'
    }
  ];
  
  // DOM elements
  const refreshBtn = document.getElementById('demo-refresh-btn');
  const resetBtn = document.getElementById('demo-reset-btn');
  const views = document.querySelectorAll('.demo-view');
  const timelineContainer = document.getElementById('demo-timeline');
  const recommendationsContainer = document.getElementById('demo-recommendations');
  const apiLogContainer = document.getElementById('demo-api-log');
  
  // State
  let userInteractions = [];
  
  // Auto-initialize the demo
  function initializeDemo() {
    // Load timeline
    loadTimeline();
    
    // Load recommendations
    loadRecommendations();
    
    // Log API calls
    logApiCall('login_auth', 'POST', '/api/v1/oauth/token', {
      'Content-Type': 'application/json'
    }, {
      client_id: '<redacted>',
      client_secret: '<redacted>',
      grant_type: 'password',
      username: demoUser.username,
      password: '<redacted>'
    }, 200);
    
    logApiCall('api_001', 'GET', '/api/v1/timelines/home', {
      'Authorization': 'Bearer <redacted>',
      'X-Mastodon-Instance': 'mastodon.social'
    }, {
      limit: 20
    }, 200);
    
    logApiCall('api_002', 'GET', '/api/v1/recommendations', {
      'Authorization': 'Bearer <redacted>'
    }, {
      user_id: demoUser.id,
      limit: 5
    }, 200);
  }
  
  function loadTimeline() {
    timelineContainer.innerHTML = '';
    
    demoTimeline.forEach(post => {
      const postEl = createPostElement(post);
      timelineContainer.appendChild(postEl);
    });
  }
  
  function loadRecommendations() {
    recommendationsContainer.innerHTML = '';
    
    demoRecommendations.forEach(rec => {
      const recEl = createPostElement(rec, true);
      recommendationsContainer.appendChild(recEl);
    });
  }
  
  function createPostElement(post, isRecommendationView = false) {
    const postEl = document.createElement('div');
    postEl.className = 'demo-post';
    postEl.dataset.postId = post.id;
    
    if (post.is_recommendation && !isRecommendationView) {
      postEl.classList.add('is-recommendation');
    }
    
    const html = `
      <div class="post-header">
        <img class="post-avatar" src="${post.account.avatar}" alt="${post.account.display_name}">
        <div class="post-account-info">
          <div class="post-display-name">${post.account.display_name}</div>
          <div class="post-username">@${post.account.username}</div>
        </div>
      </div>
      ${post.is_recommendation || isRecommendationView ? 
        `<div class="post-recommendation-badge">${post.recommendation_reason}</div>` : ''}
      <div class="post-content">${post.content}</div>
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;">
        <div class="post-timestamp">${new Date(post.created_at).toLocaleString()}</div>
        ${post.ranking_score ? `<div class="post-ranking-score">Score: ${post.ranking_score.toFixed(2)}</div>` : ''}
      </div>
      <div class="post-actions">
        <button class="post-action-reply">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/>
          </svg>
          <span>${post.replies_count}</span>
        </button>
        <button class="post-action-reblog ${post.reblogged ? 'active' : ''}" data-post-id="${post.id}">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z"/>
          </svg>
          <span>${post.reblogs_count}</span>
        </button>
        <button class="post-action-favorite ${post.favorited ? 'active' : ''}" data-post-id="${post.id}">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
          </svg>
          <span>${post.favourites_count}</span>
        </button>
              </div>
    `;
    
    postEl.innerHTML = html;
    
    // Add event listeners
    const favoriteBtn = postEl.querySelector('.post-action-favorite');
    favoriteBtn.addEventListener('click', function() {
      const postId = this.dataset.postId;
      const post = findPostById(postId);
      
      if (post) {
        post.favorited = !post.favorited;
        if (post.favorited) {
          post.favourites_count++;
          this.classList.add('active');
          logInteraction(postId, 'favorite');
        } else {
          post.favourites_count--;
          this.classList.remove('active');
        }
        this.querySelector('span').textContent = post.favourites_count;
      }
    });
    
    const reblogBtn = postEl.querySelector('.post-action-reblog');
    reblogBtn.addEventListener('click', function() {
      const postId = this.dataset.postId;
      const post = findPostById(postId);
      
      if (post) {
        post.reblogged = !post.reblogged;
        if (post.reblogged) {
          post.reblogs_count++;
          this.classList.add('active');
          logInteraction(postId, 'reblog');
        } else {
          post.reblogs_count--;
          this.classList.remove('active');
        }
        this.querySelector('span').textContent = post.reblogs_count;
      }
    });
    
    return postEl;
  }
  
  function findPostById(postId) {
    // Look in timeline first
    let post = demoTimeline.find(p => p.id === postId);
    if (post) return post;
    
    // Then look in recommendations
    return demoRecommendations.find(p => p.id === postId);
  }
  
  function logInteraction(postId, actionType) {
    const interaction = {
      id: `int_${Date.now()}`,
      user_id: demoUser.id,
      post_id: postId,
      action_type: actionType,
      timestamp: new Date().toISOString()
    };
    
    userInteractions.push(interaction);
    
    // Log API call
    logApiCall(`int_${interaction.id}`, 'POST', '/api/v1/interactions', {
      'Authorization': 'Bearer <redacted>',
      'Content-Type': 'application/json'
    }, {
      user_alias: demoUser.id,
      post_id: postId,
      action_type: actionType,
      context: {
        source: 'demo_timeline',
        recommended: findPostById(postId).is_recommendation
      }
    }, 200);
  }
  
  function logApiCall(id, method, endpoint, headers, params, status) {
    const apiCall = {
      id: id,
      method: method,
      endpoint: endpoint,
      headers: headers,
      params: params,
      response_status: status,
      timestamp: new Date().toISOString()
    };
    
    // Clear empty message if present
    const emptyMessage = apiLogContainer.querySelector('.demo-api-empty');
    if (emptyMessage) {
      apiLogContainer.removeChild(emptyMessage);
    }
    
    // Create API call element
    const apiCallEl = document.createElement('div');
    apiCallEl.className = 'demo-api-call';
    
    const html = `
      <div class="api-call-header">
        <span class="api-call-method ${method.toLowerCase()}">${method}</span>
        <span class="api-call-endpoint">${endpoint}</span>
        <span class="api-call-status status-${Math.floor(status/100)}xx">${status}</span>
        <span class="api-call-timestamp">${new Date(apiCall.timestamp).toLocaleTimeString()}</span>
      </div>
      <div class="api-call-details">
        <div class="api-call-section">
          <div class="api-call-section-title">Headers</div>
          <pre class="api-call-code">${JSON.stringify(headers, null, 2)}</pre>
        </div>
        <div class="api-call-section">
          <div class="api-call-section-title">${method === 'GET' ? 'Query Params' : 'Request Body'}</div>
          <pre class="api-call-code">${JSON.stringify(params, null, 2)}</pre>
        </div>
      </div>
    `;
    
    apiCallEl.innerHTML = html;
    
    // Add to container at the top
    apiLogContainer.insertBefore(apiCallEl, apiLogContainer.firstChild);
  }
  
  function refreshTimeline() {
    console.log("Refreshing timeline...");
    
    // Display a temporary loading indicator
    timelineContainer.innerHTML = `
      <div class="demo-loading">
        <div class="demo-loading-icon">
          <svg class="spin" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 4V2A10 10 0 0 0 2 12h2a8 8 0 0 1 8-8z"/></svg>
        </div>
        <div class="demo-loading-text">Refreshing timeline...</div>
      </div>
    `;
    
    recommendationsContainer.innerHTML = `
      <div class="demo-loading">
        <div class="demo-loading-icon">
          <svg class="spin" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 4V2A10 10 0 0 0 2 12h2a8 8 0 0 1 8-8z"/></svg>
        </div>
        <div class="demo-loading-text">Updating recommendations...</div>
      </div>
    `;
    
    // If there are interactions, modify recommendations based on them
    if (userInteractions.length > 0) {
      // Simulate algorithm updating recommendations based on interactions
      updateRecommendations();
    }
    
    // Simulate a short delay for realism
    setTimeout(() => {
      // Reload timeline
      loadTimeline();
      
      // Reload recommendations
      loadRecommendations();
      
      // Log API calls
      logApiCall(`refresh_${Date.now()}`, 'GET', '/api/v1/timelines/home', {
        'Authorization': 'Bearer <redacted>',
        'X-Mastodon-Instance': 'mastodon.social'
      }, {
        limit: 20
      }, 200);
      
      logApiCall(`recommendations_${Date.now()}`, 'GET', '/api/v1/recommendations', {
        'Authorization': 'Bearer <redacted>'
      }, {
        user_id: demoUser.id,
        limit: 5
      }, 200);
    }, 500);
  }
  
  function updateRecommendations() {
    // Get favorite and reblog interactions
    const favoriteInteractions = userInteractions.filter(i => i.action_type === 'favorite');
    const reblogInteractions = userInteractions.filter(i => i.action_type === 'reblog');
    
    // Always make some changes to demonstrate refresh is working
    // Shuffle recommendations to simulate changes
    demoRecommendations.sort(() => Math.random() - 0.5);
    
    // Slightly boost scores
    demoRecommendations.forEach(rec => {
      // Reset if too high
      if (rec.ranking_score > 0.92) {
        rec.ranking_score = Math.max(0.65, rec.ranking_score - 0.15);
      } else {
        // Otherwise increase
        rec.ranking_score = Math.min(0.95, rec.ranking_score + 0.03);
      }
    });
    
    if (favoriteInteractions.length > 0 || reblogInteractions.length > 0) {
      // Update recommendation reasons
      if (favoriteInteractions.length > reblogInteractions.length) {
        demoRecommendations[0].recommendation_reason = 'Based on posts you favorited';
        demoRecommendations[1].recommendation_reason = 'Similar to content you liked';
      } else if (reblogInteractions.length > 0) {
        demoRecommendations[0].recommendation_reason = 'Similar to posts you boosted';
        demoRecommendations[1].recommendation_reason = 'Matches your sharing pattern';
      }
      
      // Also update timeline recommendations
      const timelineRecs = demoTimeline.filter(p => p.is_recommendation);
      if (timelineRecs.length > 0) {
        // Update reasons
        if (favoriteInteractions.length > 0) {
          timelineRecs[0].recommendation_reason = 'Based on posts you favorited';
          if (timelineRecs.length > 1) {
            timelineRecs[1].recommendation_reason = 'Matches your recent interests';
          }
        } else if (reblogInteractions.length > 0) {
          timelineRecs[0].recommendation_reason = 'Similar to posts you boosted';
          if (timelineRecs.length > 1) {
            timelineRecs[1].recommendation_reason = 'Content your network might like';
          }
        }
      }
    }
    
    // Shuffle timeline slightly to show a refresh happened
    demoTimeline.sort(() => Math.random() - 0.3);
  }
  
  function resetDemo() {
    userInteractions = [];
    
    // Reset timeline
    timelineContainer.innerHTML = `
      <div class="demo-loading">
        <div class="demo-loading-icon">
          <svg class="spin" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 4V2A10 10 0 0 0 2 12h2a8 8 0 0 1 8-8z"/></svg>
        </div>
        <div class="demo-loading-text">Loading timeline...</div>
      </div>
    `;
    
    // Reset recommendations
    recommendationsContainer.innerHTML = `
      <div class="demo-loading">
        <div class="demo-loading-icon">
          <svg class="spin" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 4V2A10 10 0 0 0 2 12h2a8 8 0 0 1 8-8z"/></svg>
        </div>
        <div class="demo-loading-text">Loading recommendations...</div>
      </div>
    `;
    
    // Reset API log
    apiLogContainer.innerHTML = `
      <div class="demo-api-empty">No API calls logged yet</div>
    `;
    
    // Reset post state
    demoTimeline.forEach(post => {
      post.favorited = false;
      post.reblogged = false;
      // Reset counts to original values
      if (post.id === 'post_001') {
        post.favourites_count = 43;
        post.reblogs_count = 28;
      } else if (post.id === 'post_002') {
        post.favourites_count = 62;
        post.reblogs_count = 41;
      } else if (post.id === 'post_003') {
        post.favourites_count = 124;
        post.reblogs_count = 76;
      } else if (post.id === 'post_004') {
        post.favourites_count = 87;
        post.reblogs_count = 32;
      } else if (post.id === 'post_005') {
        post.favourites_count = 98;
        post.reblogs_count = 24;
      }
    });
    
    demoRecommendations.forEach(rec => {
      rec.favorited = false;
      rec.reblogged = false;
      // Reset ranking scores
      if (rec.id === 'rec_001') {
        rec.ranking_score = 0.89;
      } else if (rec.id === 'rec_002') {
        rec.ranking_score = 0.85;
      } else if (rec.id === 'rec_003') {
        rec.ranking_score = 0.81;
      } else if (rec.id === 'rec_004') {
        rec.ranking_score = 0.78;
      } else if (rec.id === 'rec_005') {
        rec.ranking_score = 0.75;
      }
    });
    
    // Reload the demo
    setTimeout(initializeDemo, 500);
  }
  
  // Event listeners
  refreshBtn.addEventListener('click', function() {
    refreshTimeline();
  });
  resetBtn.addEventListener('click', resetDemo);
  
  // Initialize demo on page load
  initializeDemo();
  
  // Update for tabs instead of nav items
  const tabItems = document.querySelectorAll('.demo-tab');
  
  tabItems.forEach(tabItem => {
    tabItem.addEventListener('click', function() {
      // Remove active class from all tabs
      tabItems.forEach(item => item.classList.remove('active'));
      // Add active class to clicked tab
      this.classList.add('active');
      
      // Hide all views
      views.forEach(view => view.classList.add('hidden'));
      
      // Show selected view
      const viewName = this.dataset.view;
      document.getElementById(`demo-${viewName}-view`).classList.remove('hidden');
    });
  });
});
</script>