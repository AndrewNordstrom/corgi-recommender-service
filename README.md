# Corgi Recommender Service

A modular recommendation engine that enhances social media timelines with personalized content. It can be used standalone or integrated with frontends like Elk.

## Key Features

- **Mastodon API Compatibility**: Acts as a transparent proxy for Mastodon API requests
- **Enhanced Timeline Recommendations**: Injects recommended posts into user timelines
- **Profile-Rich Display**: Provides detailed user profile information with avatar URLs
- **Cold Start Support**: Delivers quality content for new users
- **Modular Architecture**: Works standalone or with various frontends

## Project Structure

The project is organized to maintain clean separation between components:

- **`/scripts`**: Command-line tools for starting and managing services
- **`/integrations`**: Optional integrations with frontends and tools
  - **`/integrations/elk`**: Elk-specific integration files
  - **`/integrations/browser_injection`**: Browser scripts for UI enhancements
- **`/docs`**: Documentation, including compatibility information
- **`/utils`**: Core utility functions
- **`/routes`**: API endpoints and route handlers

## Getting Started with Corgi

### Prerequisites

1. Python 3.8+
2. SQLite (for development) or PostgreSQL (for production)
3. Node.js and npm (if using frontend features)

### Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and update values as needed
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Initialize the database:
   ```bash
   ./setup_db.sh
   ```

### Standalone Usage

To run Corgi as a standalone service:

```bash
# Start the Corgi service
./scripts/start_corgi.sh

# To stop the service
./scripts/stop_corgi.sh
```

The service will be available at:
- HTTPS: `https://localhost:5004`
- HTTP: `http://localhost:5004` (if started with `--no-https`)

Test the API directly:

```bash
curl -k "https://localhost:5004/api/v1/proxy/status"
curl -k -H "Authorization: Bearer YOUR_TOKEN" "https://localhost:5004/api/v1/timelines/home"
```

### Docker Deployment

For containerized deployment:

```bash
# Start Corgi in a Docker container
./scripts/docker_start_corgi.sh
```

See [Deployment Documentation](docs/deployment.md) for complete setup instructions.

## Frontend Integration Options

### Elk Integration

Corgi can enhance the [Elk](https://github.com/elk-zone/elk) Mastodon client with recommendation features:

```bash
# Start Elk configured to use Corgi (starts Corgi if needed)
./scripts/start_elk_with_corgi.sh --with-corgi
```

This will:
1. Start Corgi if it's not already running
2. Configure Elk to use Corgi as its backend
3. Launch the Elk development server

See [Elk Integration Guide](docs/elk_integration.md) for more details.

### Browser Injection

For quick testing without modifying Elk's codebase, we provide browser-side scripts:

1. Start Elk with Corgi backend
2. Open your browser console
3. Paste the script from `/integrations/browser_injection/simple_elk_integration.js`

See [Browser Injection README](integrations/browser_injection/README.md) for details.

### Vue Component Integration

For a more permanent solution, you can use our custom Vue components:

- `StatusAccountHeader.vue` - Enhanced user profile display
- `RecommendationBadge.vue` - Visual indicator for recommendations

## 🚀 Cold Start Logic

Corgi addresses the "cold start problem" by providing a curated timeline for new users who don't yet follow anyone on the Fediverse:

- **What It Does**: Serves diverse curated posts across categories (tech, art, science, etc.) to engage new users
- **How It's Triggered**: Automatically activates when a user follows no accounts, for anonymous users, or manually with `cold_start=true` parameter
- **Testing Locally**: Access via `/api/v1/timelines/home?cold_start=true` to simulate the new user experience

[See full Cold Start Strategy documentation →](docs/cold_start_strategy.md)

## ✅ Middleware Proxy Integration

The service includes a production-grade transparent proxy layer that allows Mastodon clients to connect through Corgi instead of directly to a Mastodon instance:

- Seamless injection of recommendations into standard Mastodon timelines
- No client-side changes needed for existing Mastodon clients
- Privacy-aware personalization based on user preferences
- Comprehensive logging and metrics collection

### Proxy Diagnostics

```bash
# Command-line diagnostics tool
./tools/proxy_diagnostics.py --instance mastodon.social --show-headers

# API metrics endpoint
curl http://localhost:5004/api/v1/proxy/metrics
```

See [Proxy Documentation](docs/proxy.md) for complete details.

## Server Configuration Options

The service offers flexible configuration through command-line options:

```bash
# Run with HTTPS disabled (development mode)
./scripts/start_corgi.sh --no-https

# Specify a custom port
./scripts/start_corgi.sh --port 5002

# See all options
./scripts/start_corgi.sh --help
```

## Compatibility

For detailed compatibility information including:
- Supported Elk versions
- Script dependencies
- Browser compatibility
- Environment requirements

See the [Compatibility Matrix](docs/COMPATIBILITY.md).

## License

This project is licensed under the MIT License - see the [LICENSE](licenses/LICENSE) file for details.

## Acknowledgments

- [Elk](https://github.com/elk-zone/elk) - Mastodon web client
- [Mastodon API](https://docs.joinmastodon.org/api/) - API reference and standards