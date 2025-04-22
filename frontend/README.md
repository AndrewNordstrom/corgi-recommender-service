# Corgi Recommender Service Frontend

A unified frontend interface for the Corgi Recommender System, hosted on Vercel, that integrates documentation, API explorer, timeline visualizer, and dashboard functionality.

## Features

- **Documentation Hub**: Embedded MkDocs Material documentation
- **API Explorer**: Interactive Swagger UI and ReDoc API documentation
- **Timeline Debugger**: Visual JSON timeline explorer with injection controls
- **Dashboard**: Login and account management interface with API key generation
- **Metrics**: Embedded Grafana dashboards for monitoring

## Tech Stack

- **Framework**: Next.js 14
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: Custom UI components matching Material for MkDocs design
- **Authentication**: NextAuth.js with GitHub, Google, and Mastodon options
- **Animations**: Framer Motion
- **Icons**: Lucide React
- **Deployment**: Vercel

## Getting Started

1. Clone the repository
2. Install dependencies:

```bash
cd frontend
npm install
```

3. Set up environment variables by copying `.env.example` to `.env.local` and filling in values

4. Run the development server:

```bash
npm run dev
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser

## Project Structure

- `/src/app`: Next.js 13+ App Router pages
- `/src/components`: Reusable UI components 
- `/src/lib`: Utility functions and API clients
- `/src/styles`: Global CSS and Tailwind config

## Key Pages

- `/`: Home/landing page
- `/docs`: Documentation (embedded MkDocs)
- `/api`: API explorer with Swagger UI and ReDoc
- `/explore`: Timeline visualizer
- `/dashboard`: User dashboard and API key management
- `/metrics`: Grafana metrics dashboard

## Integration with Backend

The frontend connects to the Corgi Recommender Service backend API, providing a unified interface for configuration, visualization, and management.

## Deployment

Deploy to Vercel by connecting your GitHub repository and setting the appropriate environment variables.

```bash
npm run build
```

## License

See the project root repository for license information.