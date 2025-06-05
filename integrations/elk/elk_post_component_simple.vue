<!-- A simplified Vue component for Elk that focuses on the profile elements -->
<template>
  <div class="status">
    <!-- User profile section -->
    <div class="status__profile">
      <!-- Avatar with link to profile -->
      <a 
        :href="status.account.url" 
        target="_blank" 
        rel="noopener noreferrer"
        class="status__avatar-link"
      >
        <img 
          :src="status.account.avatar" 
          :alt="status.account.display_name" 
          class="status__avatar" 
        />
      </a>
      
      <!-- User info section -->
      <div class="status__user-info">
        <!-- Display name with link to profile -->
        <a 
          :href="status.account.url" 
          target="_blank" 
          rel="noopener noreferrer"
          class="status__display-name"
        >
          <span class="status__name">{{ status.account.display_name }}</span>
        </a>
        
        <!-- Username with link to profile -->
        <a 
          :href="status.account.url" 
          target="_blank" 
          rel="noopener noreferrer"
          class="status__username"
        >
          @{{ status.account.username }}
        </a>
      </div>
    </div>
    
    <!-- Status content (keep your existing content rendering) -->
    <div 
      class="status__content" 
      v-html="status.content"
    ></div>
    
    <!-- Your existing status interactions -->
  </div>
</template>

<script>
export default {
  props: {
    status: {
      type: Object,
      required: true
    }
  }
}
</script>

<style>
.status {
  padding: 15px;
  border-bottom: 1px solid var(--border-color);
}

.status__profile {
  display: flex;
  margin-bottom: 10px;
}

.status__avatar-link {
  margin-right: 10px;
  text-decoration: none;
}

.status__avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  object-fit: cover;
}

.status__user-info {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.status__display-name {
  text-decoration: none;
  color: var(--text-color);
  font-weight: bold;
  margin-bottom: 2px;
}

.status__display-name:hover {
  text-decoration: underline;
}

.status__username {
  text-decoration: none;
  color: var(--text-muted);
  font-size: 14px;
}

.status__username:hover {
  text-decoration: underline;
}

.status__content {
  margin-left: 58px; /* Align with the content after avatar */
}

/* Dark theme support */
:root {
  --border-color: #ddd;
  --text-color: #000;
  --text-muted: #666;
}

@media (prefers-color-scheme: dark) {
  :root {
    --border-color: #333;
    --text-color: #fff;
    --text-muted: #aaa;
  }
}
</style>