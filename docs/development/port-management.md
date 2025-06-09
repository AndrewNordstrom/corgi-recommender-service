# Service Port Management

The `manage_server_port.sh` script is a comprehensive tool for managing development services and preventing port conflicts in the Corgi Recommender Service project.

## Overview

This POSIX-compliant script provides intelligent port management with:
- Automatic service discovery from `.env` configuration
- Color-coded status display
- Interactive conflict resolution
- Graceful and forced shutdown options
- Cross-platform compatibility

## Installation

The script is already executable and ready to use:

```bash
./manage_server_port.sh help
```

## Commands

### Status Command

Display the current status of all configured services:

```bash
./manage_server_port.sh status
```

Output shows:
- Service name
- Configured port
- Status (GREEN = FREE, RED = IN-USE)
- Process ID (PID) if running
- Command/process info

### Start Command

Start a service with intelligent port conflict handling:

```bash
./manage_server_port.sh start api
```

If the port is already in use, you'll get an interactive menu:
- **(K)ill** - Kill the existing process
- **(F)ind** - Find the next available port
- **(A)bort** - Cancel the operation

### Stop Command

Gracefully stop a service (SIGTERM, then SIGKILL if needed):

```bash
./manage_server_port.sh stop frontend
```

### Kill Command

Force kill a service immediately (SIGKILL):

```bash
./manage_server_port.sh kill proxy
```

## Supported Services

| Service | Environment Variable | Default Port | Start Command |
|---------|---------------------|--------------|---------------|
| api | CORGI_PORT | 5002 | `python3 app.py` |
| proxy | CORGI_PROXY_PORT | 5003 | `python3 special_proxy.py` |
| frontend | FRONTEND_PORT | 3000 | `cd frontend && npm run dev` |
| elk | ELK_PORT | 5314 | `docker-compose up elk` |
| flower | CELERY_FLOWER_PORT | 5555 | `celery flower` |
| redis | REDIS_PORT | 6379 | `redis-server` |
| postgres | DB_PORT | 5432 | `postgres` |

## Configuration

### Environment Variables

Create a `.env` file in the project root to customize ports:

```bash
# API Configuration
CORGI_PORT=5002
CORGI_PROXY_PORT=5003

# Frontend
FRONTEND_PORT=3000

# Services
ELK_PORT=5314
CELERY_FLOWER_PORT=5555
REDIS_PORT=6379
DB_PORT=5432
```

The script automatically strips quotes from values and handles various formats.

### Port Scanning

When finding a free port, the script:
1. Starts from the next port number
2. Scans up to 10 ports by default
3. Prompts for confirmation before using the found port

## Examples

### Example 1: Starting API with Port Conflict

```bash
$ ./manage_server_port.sh start api
[INFO] Checking port 5002 for service api...
[WARN] Port 5002 is already in use!
PID: 12345
Process: python3 app.py

What would you like to do?
  (K)ill the existing process
  (F)ind next available port
  (A)bort
Choice [K/F/A]: f
[INFO] Searching for next available port...
[SUCCESS] Found free port: 5003
Start api on port 5003? [Y/n]: y
[INFO] Starting api on port 5003...
[SUCCESS] api started successfully (PID: 12346)
```

### Example 2: Checking All Services

```bash
$ ./manage_server_port.sh status

Service Port Status
SERVICE         PORT            STATUS     PID        COMMAND
-------         ----            ------     ---        -------
api             5002            IN-USE     12345      python3 app.py
proxy           5003            FREE       -          -
frontend        3000            IN-USE     23456      node
elk             5314            FREE       -          -
flower          5555            FREE       -          -
redis           6379            IN-USE     34567      redis-server
postgres        5432            IN-USE     45678      postgres
```

### Example 3: Graceful Shutdown

```bash
$ ./manage_server_port.sh stop api
[INFO] Stopping api (PID: 12345) gracefully...
....
[SUCCESS] Service api stopped
```

## Troubleshooting

### Missing Dependencies

The script requires at least one of:
- `lsof` (recommended, most accurate)
- `netstat`
- `ss`

Install on macOS:
```bash
# lsof is usually pre-installed
# If needed:
brew install lsof
```

Install on Linux:
```bash
# Debian/Ubuntu
sudo apt-get install lsof

# RHEL/CentOS
sudo yum install lsof
```

### Permission Issues

Some operations may require elevated privileges:

```bash
# If you get "Permission denied" errors
sudo ./manage_server_port.sh kill postgres
```

### Port Detection Issues

If port detection isn't working:
1. Ensure at least one detection tool is installed
2. Check firewall settings
3. Verify the service is actually binding to the expected port

## Integration with Development Workflow

### Use with make dev

The script complements the automated development workflow:

```bash
# Start full automated workflow
make dev

# Check individual service status
./manage_server_port.sh status

# Restart a specific service
./manage_server_port.sh stop api
./manage_server_port.sh start api
```

### Debugging Port Conflicts

When encountering "Address already in use" errors:

1. Check what's using the port:
   ```bash
   ./manage_server_port.sh status
   ```

2. Kill the conflicting process:
   ```bash
   ./manage_server_port.sh kill api
   ```

3. Or find an alternative port:
   ```bash
   ./manage_server_port.sh start api
   # Choose (F) when prompted
   ```

## Best Practices

1. **Always check status first**: Before starting services, run `status` to see what's already running
2. **Use graceful shutdown**: Prefer `stop` over `kill` to allow services to clean up
3. **Document port changes**: If you use non-default ports, update your `.env` file
4. **Handle conflicts interactively**: Let the script guide you through port conflicts

## Script Internals

The script uses:
- POSIX shell syntax for maximum compatibility
- Multiple fallback methods for port detection
- Color-coded output for better readability
- Interactive prompts for user-friendly operation
- Proper signal handling for service management

## Extending the Script

To add a new service:

1. Add it to the `DEFAULT_SERVICES` variable:
   ```bash
   newservice:NEW_SERVICE_PORT:8080:python3 newservice.py
   ```

2. Optionally, add custom port handling in the `start_service` function

3. Document the new service in this guide 