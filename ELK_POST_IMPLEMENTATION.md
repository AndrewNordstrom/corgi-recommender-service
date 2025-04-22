# Elk Post Component Implementation Guide

This guide explains how to integrate the updated post components with Elk to properly display user profiles, avatars, and clickable usernames/display names.

## Implementations Provided

We've prepared multiple implementation options depending on your Elk setup:

1. **Vue.js Components**:
   - `elk_post_component.vue` - Full featured component
   - `elk_post_component_simple.vue` - Simplified component

2. **React Components**:
   - `elk_post_component.jsx` + `elk_post_component.css` - Full featured component
   - `elk_post_component_simple.jsx` + `PostComponentSimple.css` - Simplified component

3. **Next.js Component**:
   - We've updated the existing `timeline-post.tsx` in your frontend component library

## Implementing in Elk

### Vue.js Implementation

1. Copy the chosen Vue component file to your Elk project.
2. Register the component in your Vue application:

```js
import Post from './path/to/elk_post_component.vue';

// In your component
export default {
  components: {
    Post
  },
  // rest of your component...
}
```

3. Use the component in your templates:

```vue
<template>
  <div>
    <Post 
      v-for="post in timeline"
      :key="post.id"
      :post="post"
    />
  </div>
</template>
```

### React Implementation

1. Copy the chosen React component and CSS files to your Elk project.
2. Import the component:

```jsx
import PostComponent from './path/to/elk_post_component';
// CSS is imported in the component itself

function Timeline({ posts }) {
  return (
    <div className="timeline">
      {posts.map(post => (
        <PostComponent key={post.id} post={post} />
      ))}
    </div>
  );
}
```

## Key Features

All implementations include:

1. **Clickable Avatar**: Links to the user's profile page
2. **Clickable Display Name**: The user's display name links to their profile
3. **Clickable Username**: The username (@username) links to their profile
4. **Dark Theme Support**: Components adjust to dark theme using CSS variables or media queries
5. **Responsive Design**: Looks good on all screen sizes

## URL Format

All links use the `post.account.url` field which is already included in your post data. This should point to the user's profile on their home instance.

For example: `https://mastodon.social/@username`

## Styling Customization

All components use CSS variables for theming. You can customize them by overriding these variables in your CSS:

```css
:root {
  --border-color: #e6e6e6;
  --text-color: #000;
  --secondary-text-color: #6e767d;
  --link-color: #1d9bf0;
  --recommendation-bg: rgba(29, 155, 240, 0.1);
  --primary-color: #1d9bf0;
  --like-color: #e0245e;
  --tag-bg: #f2f2f2;
  
  /* Dark theme variables */
  --dark-border-color: #2f3336;
  --dark-text-color: #e7e9ea;
  --dark-secondary-text-color: #71767b;
  --dark-tag-bg: #2f3336;
}
```

## Testing

After implementation, verify that:

1. Clicking on avatars navigates to the user's profile
2. Clicking on display names navigates to the user's profile
3. Clicking on usernames navigates to the user's profile
4. The component displays properly in both light and dark themes
5. The design is responsive on mobile devices