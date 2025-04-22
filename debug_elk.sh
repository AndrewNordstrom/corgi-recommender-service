#!/bin/bash

echo "Creating simplified versions of the component files..."

# Create a simplified RecommendationBadge component
cat > /Users/andrewnordstrom/elk-clean-repo/elk/components/status/RecommendationBadge.vue << 'EOF'
<script setup lang="ts">
import type { mastodon } from 'masto'

defineProps<{
  status: mastodon.v1.Status
}>()
</script>

<template>
  <div
    v-if="status.is_recommendation"
    class="absolute top-2 right-2 z-10 flex gap-1 items-center rounded-full bg-primary bg-opacity-10 dark:bg-opacity-20 text-primary text-xs font-medium px-2 py-1"
  >
    <div class="i-ri:star-fill" />
    <span v-if="status.recommendation_reason">{{ status.recommendation_reason }}</span>
    <span v-else>{{ $t('status.recommended') }}</span>
  </div>
</template>
EOF

# Create a simplified StatusAccountHeader component
cat > /Users/andrewnordstrom/elk-clean-repo/elk/components/status/StatusAccountHeader.vue << 'EOF'
<script setup lang="ts">
import type { mastodon } from 'masto'

defineProps<{
  account: mastodon.v1.Account
}>()

const userSettings = useUserSettings()
</script>

<template>
  <div class="flex gap-3 items-center mb-2">
    <AccountHoverWrapper :account="account">
      <NuxtLink :to="getAccountRoute(account)" class="rounded-full">
        <AccountBigAvatar :account="account" />
      </NuxtLink>
    </AccountHoverWrapper>
    
    <div class="flex flex-col min-w-0">
      <AccountHoverWrapper :account="account">
        <NuxtLink :to="getAccountRoute(account)" class="hover:underline">
          <AccountDisplayName 
            :account="account" 
            :hide-emojis="getPreferences(userSettings, 'hideUsernameEmojis')" 
          />
        </NuxtLink>
      </AccountHoverWrapper>
      
      <AccountHoverWrapper :account="account">
        <NuxtLink :to="getAccountRoute(account)" class="hover:underline">
          <AccountHandle :account="account" />
        </NuxtLink>
      </AccountHoverWrapper>
    </div>
  </div>
</template>
EOF

echo "Making minimal changes to StatusCard.vue..."

# Create patch for StatusCard.vue
cat > /tmp/statuscard.patch << 'EOF'
--- StatusCard.vue	2025-04-21 20:26:45
+++ StatusCard.new.vue	2025-04-21 20:27:53
@@ -72,6 +72,11 @@
 
 <template>
   <StatusLink :status="status" :hover="hover" relative>
+    <!-- Recommendation Badge (if applicable) -->
+    <RecommendationBadge 
+      v-if="status.is_recommendation" 
+      :status="status" 
+    />
 
     <slot name="meta">
       <!-- Pinned status -->
@@ -145,6 +150,9 @@
           </div>
         </div>
       </template>
+      
+      <!-- User Account Header -->
+      <StatusAccountHeader v-else :account="status.account" />
 
       <!-- Main -->
       <div flex="~ col 1" min-w-0">
EOF

# Apply the patch (this is just to add our components without changing the original structure)
patch /Users/andrewnordstrom/elk-clean-repo/elk/components/status/StatusCard.vue /tmp/statuscard.patch || true

echo "Adding user content to elk-data directory..."

# Create elk-data directory if it doesn't exist
mkdir -p /Users/andrewnordstrom/elk-clean-repo/elk-data

echo "Updating translation files..."

# Make sure recommended string exists in en.json
if ! grep -q '"recommended":' /Users/andrewnordstrom/elk-clean-repo/elk/locales/en.json; then
  # Add the recommended string to en.json after "pinned"
  sed -i '' 's/"pinned": "Pinned post",/"pinned": "Pinned post",\n    "recommended": "Recommended for you",/g' /Users/andrewnordstrom/elk-clean-repo/elk/locales/en.json
fi

echo "Creating debug version of .env file..."

# Create a minimal .env file
cat > /Users/andrewnordstrom/elk-clean-repo/elk/.env << 'EOF'
# Connect to Corgi backend
NUXT_PUBLIC_DEFAULT_SERVER=localhost:5004
NUXT_PUBLIC_DEFAULT_INSTANCE=mastodon.social
NUXT_PUBLIC_DISABLE_SERVER_SIDE_AUTH=true
NUXT_PUBLIC_PREFER_WSS=false
DEBUG=true
EOF

echo "Setup complete. Now run the following command to start the Elk client:"
echo "cd /Users/andrewnordstrom/elk-clean-repo/elk && npm run dev -- --port 3013"
echo ""
echo "Visit http://localhost:3013 in your browser to see the results."
echo "If you still see errors, check the browser console and let me know the specific error messages."