# Corgi Recommender Service - Frontend Plan

## Project Structure

```
/frontend
├── .env.example           # Environment variables example
├── .gitignore             # Git ignore file
├── next.config.js         # Next.js configuration
├── package.json           # Dependencies
├── postcss.config.js      # PostCSS configuration for Tailwind
├── tailwind.config.js     # Tailwind CSS configuration
├── tsconfig.json          # TypeScript configuration
├── public/                # Static assets
│   ├── favicon/           # Favicon assets (copied from original)
│   ├── logo-icon.png      # Logo assets
│   └── assets/            # Other static assets
└── src/                   # Source code
    ├── app/               # Next.js 13+ App Router 
    │   ├── page.tsx       # Home page (landing)
    │   ├── layout.tsx     # Root layout with navigation
    │   ├── docs/          # Documentation pages
    │   │   └── [[...slug]]/page.tsx # Catch-all for docs
    │   ├── api/           # API documentation pages
    │   │   ├── page.tsx   # API landing page
    │   │   ├── swagger/page.tsx # Swagger UI
    │   │   └── redoc/page.tsx # ReDoc UI
    │   ├── explore/       # Timeline explorer
    │   │   └── page.tsx   # Timeline visualization
    │   ├── dashboard/     # User dashboard
    │   │   ├── page.tsx   # Dashboard home
    │   │   ├── login/page.tsx   # Login page
    │   │   └── profile/page.tsx # Profile management
    │   └── metrics/       # Metrics/analytics
    │       └── page.tsx   # Grafana embedding
    ├── components/        # Reusable components
    │   ├── ui/            # Base UI components
    │   │   ├── button.tsx
    │   │   ├── card.tsx
    │   │   ├── input.tsx
    │   │   └── ...
    │   ├── layout/        # Layout components
    │   │   ├── sidebar.tsx
    │   │   ├── header.tsx
    │   │   ├── footer.tsx
    │   │   └── ...
    │   ├── docs/          # Documentation-specific components
    │   ├── api/           # API documentation components
    │   ├── explore/       # Timeline explorer components
    │   └── dashboard/     # Dashboard components
    ├── lib/               # Utility functions and hooks
    │   ├── api.ts         # API client
    │   ├── auth.ts        # Authentication utilities
    │   └── ...
    └── styles/            # Global styles
        └── globals.css    # Global styles including Tailwind
```

## Technology Stack

- **Framework**: Next.js 14
- **Language**: TypeScript
- **Styling**: Tailwind CSS + CSS Modules
- **UI Components**: Custom components matching Material for MkDocs design
- **Icons**: Lucide React
- **Authentication**: NextAuth.js with GitHub, Google, and custom Mastodon provider
- **API Integration**: React Query
- **Animation**: Framer Motion for subtle transitions
- **Code Syntax Highlighting**: Prism or Shiki
- **State Management**: React Context + hooks
- **Deployment**: Vercel

## Design System

### Colors

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#ffb300', // amber
          light: '#ffd54f',
          dark: '#ff8f00',
        },
        accent: {
          DEFAULT: '#ff5722', // deep orange
          light: '#ff8a65',
          dark: '#e64a19',
        },
        background: {
          light: '#fffbf5',
          dark: '#1a1a1a',
        },
        navy: '#1a237e',
        neutral: {
          50: '#faf6f1',
          100: '#f5efe8',
          200: '#e8e0d5',
          300: '#d5c9ba',
          400: '#b3a799',
          500: '#8c7b6a',
          600: '#6f5f4d',
          700: '#564a3c',
          800: '#423931',
          900: '#342c23',
        }
      },
    },
  },
};
```

### Typography

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
};
```

### Component Design

- Match the Material for MkDocs design:
  - Cards with 8px border-radius and subtle shadows
  - Buttons with amber background and hover effects
  - API blocks with consistent styling
  - Custom callouts and admonitions
  - Tabs with understated design
  - Code blocks with syntax highlighting and copy button

## Page Implementations

### Home Page
- Hero section with corgi mascot
- Feature cards in a grid layout
- Getting started links
- Animated elements (subtle)

### Documentation
- Two options:
  1. Embed the existing MkDocs site in an iframe
  2. Recreate the documentation using Markdown processing (more work but better integration)
- Use Next.js catch-all routes to handle documentation structure

### API Documentation
- Tabbed interface with:
  - Overview
  - Swagger UI
  - ReDoc
- Embedded from existing endpoints with styling wrappers

### Timeline Explorer
- JSON timeline visualization
- Post rendering with proper styling
- Injection strategy selection
- Debug view of raw response
- Interactive testing of timeline parameters

### Dashboard
- Authentication with NextAuth.js
- API key management
- User profile settings
- Integration settings
- Usage statistics

### Metrics
- Embedded Grafana dashboard
- Local metrics summary
- System status overview

## Authentication Flow

1. User visits `/dashboard`
2. If not authenticated, redirect to `/dashboard/login`
3. Login options:
   - GitHub OAuth
   - Google OAuth
   - Email magic link
   - Mastodon OAuth (for existing users)
4. After authentication, user can:
   - Generate API keys
   - View usage statistics
   - Manage profile settings
   - Configure integration preferences

## API Integration

- Create a client library for interacting with the Corgi API
- Use React Query for data fetching and caching
- Include authentication header management
- Provide hooks for common operations:
  - `useTimeline`
  - `useRecommendations`
  - `useInteractions`
  - `useProfile`

## Implementation Strategy

1. **Phase 1: Basic Structure**
   - Set up Next.js project with Tailwind CSS
   - Implement core layout components
   - Create basic routing structure
   - Implement design system

2. **Phase 2: Landing and Documentation**
   - Implement home page with branding
   - Set up documentation section
   - Implement API documentation embedding
   - Basic styles and components

3. **Phase 3: Timeline Explorer**
   - Implement timeline visualization
   - Add interactive controls
   - Create JSON viewer
   - Connect to API endpoints

4. **Phase 4: Authentication and Dashboard**
   - Set up NextAuth.js
   - Implement login flow
   - Create dashboard UI
   - Implement API key management

5. **Phase 5: Metrics and Polish**
   - Set up Grafana embedding
   - Add final UI refinements
   - Implement animations
   - Cross-browser testing

## Deployment

- Deploy to Vercel
- Configure environment variables
- Set up authentication providers
- Configure custom domain
- Set up analytics and monitoring