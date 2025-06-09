# Corgi Recommender Service - Docker Setup

This Docker setup provides a production-quality, flexible environment for the Corgi Recommender Service that solves port conflicts and zombie process issues while maintaining client agnosticism.

## Overview

The setup supports two primary modes:

1. **Standalone Mode**: Run only the Corgi API and its dependencies (PostgreSQL, Redis)
   - Perfect for third-party client developers
   - Minimal resource usage
   - Client-agnostic API access

2. **Demo Mode**: Run the complete stack including the ELK client
   - Ideal for testing and demonstrations
   - Includes the full user interface
   - Seamless integration between frontend and backend

## Architecture

```
┌─────────────────────┐     ┌─────────────────────┐
│   Standalone Mode   │     │     Demo Mode       │
├─────────────────────┤     ├─────────────────────┤
│                     │     │    ELK Client       │
│                     │     │    (Port 3000)      │
│                     │     ├─────────────────────┤
│    Corgi API        │     │    Corgi API        │
│    (Port 5002)      │     │    (Port 5002)      │
├─────────────────────┤     ├─────────────────────┤
│    PostgreSQL       │     │    PostgreSQL       │
│    (Port 5432)      │     │    (Port 5432)      │
├─────────────────────┤     ├─────────────────────┤
│    Redis            │     │    Redis            │
│    (Port 6379)      │     │    (Port 6379)      │
└─────────────────────┘     └─────────────────────┘
```

## Quick Start

### 1. Copy Environment Configuration

```bash
cp env.example .env
```

Edit `.env` to configure ports and credentials as needed.

### 2. Start Services

**For API Development (Standalone Mode):**
```bash
./run-dev.sh standalone
```

**For Full Demo:**
```bash
./run-dev.sh demo
```

### 3. Access Services

- **Corgi API**: http://localhost:5002
- **ELK Client** (demo mode only): http://localhost:3000
- **API Documentation**: http://localhost:5002/docs

### 4. Stop Services

```bash
./run-dev.sh stop
```

## Features

### Clean Startup
- Automatically removes zombie containers and networks before starting
- Ensures a fresh environment every time
- No more "port already in use" errors

### Health Checks
- All services include health checks
- Automatic restart on failure
- Dependencies wait for services to be healthy

### Security
- Non-root users in containers
- Minimal base images
- Production-ready configurations

### Development Tools
- Hot reload for code changes
- Centralized logging
- Easy database access

## Command Reference

### Basic Commands

```bash
# Start API only (for client developers)
./run-dev.sh standalone

# Start full demo stack
./run-dev.sh demo

# Stop all services
./run-dev.sh stop

# Check service status
./run-dev.sh status
```

### Debugging Commands

```bash
# View logs for all services
./run-dev.sh logs

# View logs for specific service
./run-dev.sh logs corgi-api

# Access container shell
./run-dev.sh exec corgi-api bash

# Connect to database
./run-dev.sh exec postgres psql -U corgi -d corgi_db

# Run database migrations
./run-dev.sh migrate
```

### Service Names

- `postgres` - PostgreSQL database
- `redis` - Redis cache
- `corgi-api` - Corgi API service
- `elk-client` - ELK frontend (demo mode only)

## Environment Variables

Key variables in `.env`:

```bash
# Database
POSTGRES_USER=corgi
POSTGRES_PASSWORD=corgi123
POSTGRES_DB=corgi_db

# Service Ports
CORGI_API_HOST_PORT=5002
ELK_CLIENT_HOST_PORT=3000
POSTGRES_HOST_PORT=5432
REDIS_HOST_PORT=6379

# API Configuration
CORGI_ENV=development
CORS_ORIGINS=*
```

## Troubleshooting

### Port Conflicts

The setup automatically cleans up before starting, but if you still have issues:

```bash
# Force cleanup
docker-compose down -v --remove-orphans
docker system prune -f

# Then restart
./run-dev.sh standalone
```

### Database Issues

```bash
# Reset database
./run-dev.sh stop
rm -rf postgres_data/
./run-dev.sh standalone
./run-dev.sh migrate
```

### Container Won't Start

Check logs:
```bash
./run-dev.sh logs corgi-api
```

Rebuild images:
```bash
docker-compose build --no-cache
./run-dev.sh standalone
```

## Development Workflow

### Making API Changes

1. Edit Python files
2. Changes auto-reload in container
3. Test via API endpoints

### Making Frontend Changes

1. Ensure demo mode is running
2. Edit frontend files
3. Rebuild if necessary:
   ```bash
   docker-compose build elk-client
   ./run-dev.sh demo
   ```

### Database Migrations

```bash
# Create migration
./run-dev.sh exec corgi-api flask db migrate -m "Description"

# Apply migration
./run-dev.sh migrate
```

## API Client Examples

### Using curl

```bash
# Health check
curl http://localhost:5002/health

# Get recommendations
curl http://localhost:5002/api/v1/recommendations

# Post interaction
curl -X POST http://localhost:5002/api/v1/interactions \
  -H "Content-Type: application/json" \
  -d '{"post_id": "123", "action": "like"}'
```

### Using Python

```python
import requests

# Configure API base URL
API_BASE = "http://localhost:5002"

# Get recommendations
response = requests.get(f"{API_BASE}/api/v1/recommendations")
recommendations = response.json()
```

### Using JavaScript

```javascript
// Configure API base URL
const API_BASE = "http://localhost:5002";

// Get recommendations
fetch(`${API_BASE}/api/v1/recommendations`)
  .then(res => res.json())
  .then(data => console.log(data));
```

## Production Considerations

### Security

1. Change default passwords in `.env`
2. Use specific CORS origins instead of `*`
3. Enable HTTPS with proper certificates
4. Use secrets management for sensitive data

### Performance

1. Adjust worker counts in Dockerfiles
2. Configure PostgreSQL for production workloads
3. Set up Redis persistence appropriately
4. Use a reverse proxy (nginx) in front

### Monitoring

1. Export metrics to Prometheus
2. Set up log aggregation
3. Configure alerts for health check failures
4. Monitor resource usage

## File Structure

```
.
├── docker-compose.yml      # Service orchestration
├── corgi-api.Dockerfile    # API container definition
├── elk-client.Dockerfile   # Frontend container definition
├── env.example            # Environment template
├── run-dev.sh            # Control script
└── DOCKER_README.md      # This file
```

## Contributing

When adding new services:

1. Add service definition to `docker-compose.yml`
2. Assign to appropriate profile(s)
3. Include health checks
4. Update `run-dev.sh` if needed
5. Document in this README

## Support

For issues:
1. Check troubleshooting section
2. Review service logs
3. Ensure `.env` is configured correctly
4. Verify Docker is running 