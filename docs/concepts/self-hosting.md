# Self-Hosting Corgi

This guide explains how to self-host Corgi on your own infrastructure, allowing you to have full control over your recommendation engine and data.

## Requirements

- Docker and Docker Compose
- 2GB+ RAM
- 20GB+ storage space
- Public-facing domain with SSL certificate

## Quick Start with Docker

The fastest way to get Corgi running is with our official Docker image:

```bash
docker run -p 5000:5000 \
  -e DATABASE_URL=postgresql://user:password@localhost/corgi \
  -e SECRET_KEY=your-secret-key \
  -e DEFAULT_MASTODON_INSTANCE=mastodon.social \
  corgi/recommender-service:latest
```

## Using Docker Compose

For a more complete setup with a database and proper configuration, use Docker Compose:

1. Create a `.env` file with your configuration:

```
DATABASE_URL=postgresql://postgres:postgres@db/corgi
SECRET_KEY=your-secret-key-here
DEFAULT_MASTODON_INSTANCE=mastodon.social
RECOMMENDATION_BLEND_RATIO=0.3
```

2. Use our sample `docker-compose.yml`:

```yaml
version: '3'

services:
  corgi:
    image: corgi/recommender-service:latest
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
      - DEFAULT_MASTODON_INSTANCE=${DEFAULT_MASTODON_INSTANCE}
      - RECOMMENDATION_BLEND_RATIO=${RECOMMENDATION_BLEND_RATIO}
    depends_on:
      - db
    restart: unless-stopped
    
  db:
    image: postgres:14
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_USER=postgres
      - POSTGRES_DB=corgi
    restart: unless-stopped

volumes:
  postgres_data:
```

3. Start the services:

```bash
docker-compose up -d
```

## From Source Code

If you prefer to run Corgi from source:

1. Clone the repository:

```bash
git clone https://github.com/andrewnordstrom/corgi-recommender-service.git
cd corgi-recommender-service
```

2. Install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Set up the database:

```bash
./setup_db.sh
```

4. Run the server:

```bash
python run_server.py
```

## Configuration Options

You can configure Corgi through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost/corgi` |
| `SECRET_KEY` | Secret key for session security | - |
| `DEFAULT_MASTODON_INSTANCE` | Default Mastodon instance | `mastodon.social` |
| `RECOMMENDATION_BLEND_RATIO` | Ratio of recommendations to include (0-1) | `0.3` |
| `PROXY_TIMEOUT` | Timeout for proxy requests in seconds | `10` |
| `DEBUG` | Enable debug mode | `false` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

## Connecting to Mastodon

For Corgi to function as a middleware, it needs to connect to one or more Mastodon instances:

1. Create an application on your Mastodon instance to get API credentials
2. Configure your Mastodon client to use your Corgi instance as the API endpoint
3. Link accounts through the Corgi API

See the [Proxy Architecture](proxy.md) documentation for more details.

## Scaling Considerations

### Memory Usage

Corgi's memory usage depends mainly on:

- Number of active users
- Complexity of user interest profiles
- Size of the recommendation corpus

For production, we recommend at least:
- 2GB RAM for up to 100 users
- 4GB RAM for up to 500 users
- 8GB+ RAM for 1000+ users

### Database Scaling

The recommendation engine relies heavily on database performance. For larger deployments:

- Use a dedicated PostgreSQL server
- Ensure adequate disk I/O
- Consider read replicas for analytics

## Securing Your Instance

1. **Always use HTTPS** - Run Corgi behind a reverse proxy like Nginx with SSL
2. **Set a strong SECRET_KEY** - Don't use the default or example values
3. **Implement rate limiting** - Protect your API endpoints from abuse
4. **Regular backups** - Back up your database regularly
5. **Update frequently** - Keep your Corgi instance updated with security patches

## Monitoring

We recommend monitoring:

- Server metrics (CPU, memory, disk)
- Application logs for errors
- Database performance
- Request latency

Prometheus and Grafana work well for monitoring Corgi deployments.

## Example Nginx Configuration

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

Common issues and solutions:

1. **Database connection errors**
   - Check your DATABASE_URL format
   - Ensure the PostgreSQL server is running and accessible
   - Verify database user permissions

2. **High memory usage**
   - Consider reducing the recommendation corpus size
   - Adjust the `RECOMMENDATION_BATCH_SIZE` environment variable
   - Increase server resources

3. **Slow response times**
   - Check Mastodon instance connectivity
   - Increase `PROXY_TIMEOUT` if needed
   - Monitor database query performance
   - Consider caching frequently accessed data

## Community Support

If you're self-hosting Corgi and need help:

- Check our [GitHub Issues](https://github.com/andrewnordstrom/corgi-recommender-service/issues)
- Join our [Mastodon community](https://mastodon.social/@corgi)
- Contribute improvements back to the project