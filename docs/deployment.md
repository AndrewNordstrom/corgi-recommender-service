# Deployment Guide

This guide explains how to deploy Corgi Recommender Service in various environments.

## Local Deployment

### Prerequisites

- Python 3.8+ (3.10+ recommended)
- SQLite database
- OpenSSL (optional, for HTTPS)

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/corgi-recommender-service.git
   cd corgi-recommender-service
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the service:
   ```bash
   ./scripts/start_corgi.sh
   ```

The service will be available at `https://localhost:5004` by default.

## Docker Deployment

### Prerequisites

- Docker Engine 20.10+
- Docker Compose (optional)

### Using Docker Directly

1. Build the Docker image:
   ```bash
   docker build -t corgi-recommender-service .
   ```

2. Run the container:
   ```bash
   docker run -d \
     --name corgi-server \
     -p 5004:5004 \
     -e PORT=5004 \
     -e HOST=0.0.0.0 \
     --restart unless-stopped \
     corgi-recommender-service
   ```

### Using Our Docker Script

We provide a convenient script for Docker deployment:

```bash
./scripts/docker_start_corgi.sh --port 5004
```

This script handles:
- Checking if Docker is installed and running
- Building the image if needed
- Running the container with proper configuration
- Handling existing containers

### Using Docker Compose

1. Create a `docker-compose.yml` file:
   ```yaml
   version: '3.8'
   
   services:
     corgi:
       build: .
       ports:
         - "5004:5004"
       environment:
         - PORT=5004
         - HOST=0.0.0.0
       restart: unless-stopped
       volumes:
         - ./data:/app/data
   ```

2. Start the service:
   ```bash
   docker-compose up -d
   ```

## Cloud Deployment

### Deploying to Fly.io

1. Install the Fly CLI: https://fly.io/docs/hands-on/install-flyctl/

2. Log in to Fly:
   ```bash
   fly auth login
   ```

3. Create a new app:
   ```bash
   fly launch
   ```

4. Deploy the app:
   ```bash
   fly deploy
   ```

### Deploying to Render

1. Fork this repository to your GitHub account.

2. Create a new Web Service on Render.com:
   - Connect your GitHub repository
   - Set build command: `pip install -r requirements.txt`
   - Set start command: `python special_proxy_fixed.py --port 10000 --host 0.0.0.0 --no-https`

3. Add environment variables as needed.

## Production Considerations

### HTTPS Configuration

For production environments, you should use proper SSL certificates:

1. Obtain certificates from a trusted CA (e.g., Let's Encrypt)

2. Configure Corgi to use them:
   ```bash
   ./scripts/start_corgi.sh --cert /path/to/cert.pem --key /path/to/key.pem
   ```

### Reverse Proxy Configuration

For production deployments, we recommend using a reverse proxy:

#### Nginx Example

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass https://localhost:5004;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Monitoring

For production deployments, consider setting up monitoring:

1. Set up Prometheus and Grafana for metrics collection
2. Configure log aggregation with tools like ELK Stack
3. Set up uptime monitoring with services like Uptime Robot

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Host to bind to | `0.0.0.0` |
| `PORT` | Port to listen on | `5004` |
| `DEBUG` | Enable debug mode | `False` |
| `USE_HTTPS` | Use HTTPS | `True` |
| `SSL_CERT_PATH` | Path to SSL certificate | `certs/cert.pem` |
| `SSL_KEY_PATH` | Path to SSL key | `certs/key.pem` |
| `DB_FILE` | Path to SQLite database | `corgi_demo.db` |

## Troubleshooting

### Common Deployment Issues

1. **Port conflicts**: If the port is already in use, try:
   - Using a different port with `--port`
   - Stopping the existing process with `./scripts/stop_corgi.sh`
   - Checking for running processes with `lsof -i :5004`

2. **Certificate issues**: If HTTPS isn't working, check:
   - Certificate and key paths
   - File permissions
   - Certificate validity

3. **Database errors**: If you see SQLite errors:
   - Ensure the database file exists
   - Check file permissions
   - Run setup scripts if needed