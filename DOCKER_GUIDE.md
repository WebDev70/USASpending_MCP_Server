# Docker Setup Guide

This guide explains how to containerize and run the USASpending MCP Server using Docker Desktop.

## Prerequisites

- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)
- Git (for cloning the repository)


#  docker build -t nginx-b .
#  docker run -d -p 8094:80 nginx-b
#  docker run --name=nginx-b -d -p 8094:80 nginx-b

# Usage commands:
# 0. docker-compose up --build -d
# 1. Start: docker-compose up -d
# 2. Stop: docker-compose down
# 3. Logs: docker-compose logs -f
# 4. Rebuild: docker-compose down -v ; docker-compose up --build -d
# 5. docker compose exec 'name_of_image' bash


## Files Added

Four new files have been created for Docker support:

1. **Dockerfile** - Multi-stage Docker build configuration with proper host binding
2. **docker-compose.yml** - Docker Compose configuration for easy management
3. **docker-entrypoint.sh** - Entrypoint script that binds the server to 0.0.0.0 (required for Docker)
4. **.dockerignore** - Excludes unnecessary files from the Docker build context

## Quick Start

### Using Docker Compose (Recommended)

The easiest way to run the server with Docker Desktop:

```bash
# From the project root directory
docker compose up --build
```

This will:
- Build the Docker image
- Start the USASpending MCP Server container
- Expose the server on `http://localhost:3002`
- Automatically restart on failure
- Include health checks

To stop the server:

```bash
docker-compose down
```

To view logs:

```bash
docker-compose logs -f usaspending-mcp
```

### Using Docker CLI Directly

If you prefer not to use Docker Compose:

```bash
# Build the image
docker build -t usaspending-mcp:latest .

# Run the container
docker run -d \
  --name usaspending-mcp \
  -p 3002:3002 \
  --restart unless-stopped \
  usaspending-mcp:latest

# View logs
docker logs -f usaspending-mcp

# Stop the container
docker stop usaspending-mcp

# Remove the container
docker rm usaspending-mcp
```

## Configuration

### Environment Variables

You can set environment variables in the `docker-compose.yml` file:

```yaml
environment:
  PYTHONUNBUFFERED: "1"
  PYTHONDONTWRITEBYTECODE: "1"
  # Add other environment variables here
```

### Port Mapping

By default, the server runs on port 3002. If you need to use a different port, modify the `docker-compose.yml`:

```yaml
ports:
  - "YOUR_PORT:3002"
```

Or when using `docker run`:

```bash
docker run -p YOUR_PORT:3002 usaspending-mcp:latest
```

### Resource Limits

The docker-compose.yml includes resource limits. Adjust as needed:

```yaml
deploy:
  resources:
    limits:
      cpus: '1'        # Maximum CPU usage
      memory: 512M     # Maximum memory usage
```

### Volume Mounts

To persist logs, the configuration includes a named volume:

```yaml
volumes:
  - mcp-logs:/app/logs
```

To mount a local directory instead:

```yaml
volumes:
  - ./logs:/app/logs
```

## Docker Desktop Usage

### Starting the Server

1. Open **Docker Desktop**
2. Go to **Containers**
3. Navigate to the project directory:
   ```bash
   cd /path/to/usaspending-mcp
   docker-compose up --build
   ```
4. The server will appear in the Containers list with status **Running**

### Monitoring

In Docker Desktop:
- Click the container to see **Logs**
- View **Inspect** tab for detailed container information
- Use the **Stats** tab to monitor CPU and memory usage

### Stopping

- In Docker Desktop, click the stop button on the container
- Or use: `docker-compose down`

## Accessing the Server

Once the container is running:

- **Server URL**: `http://localhost:3002`
- **Health Check**: Automatically verified by Docker health check

The server implements the Model Context Protocol (MCP) and is accessible to MCP clients on port 3002.

### Testing the Server

```bash
# Test that the server is running and accessible
curl http://localhost:3002/

# View container logs (includes server startup info)
docker-compose logs -f usaspending-mcp

# Or with docker CLI
docker logs -f usaspending-mcp
```

To actually test the MCP tools, you'll need an MCP client configured to connect to the server.

## Troubleshooting

### Container Won't Start

1. Check logs: `docker-compose logs usaspending-mcp`
2. Verify port 3002 is not in use: `lsof -i :3002`
3. If port is busy, either:
   - Kill the process: `kill -9 <PID>`
   - Change the port in docker-compose.yml

### Health Check Failing

The container health check verifies the server is responding on port 3002. If it fails:

1. Check logs: `docker-compose logs usaspending-mcp`
2. Wait longer - the server may still be starting (10 second grace period)
3. Verify the server is accessible:
   ```bash
   curl -v http://localhost:3002/
   ```
4. If port 3002 is not accessible from your host, ensure:
   - Docker Desktop is running
   - Port 3002 is not blocked by a firewall
   - Port mapping is correct in docker-compose.yml

### Docker Build Fails

If you see credential errors during build:

1. This is a Docker Desktop configuration issue, not a Dockerfile problem
2. Try signing out/in to Docker Desktop
3. Or build without using Docker Desktop's credentials cache:
   ```bash
   docker build --no-cache -t usaspending-mcp:latest .
   ```

### Permissions Issues

The Dockerfile runs the application as a non-root user (`appuser`) for security. If you need root access for development, create a development Dockerfile.

## How It Works

### The Entrypoint Script

The `docker-entrypoint.sh` script is necessary because the server code hardcodes binding to `127.0.0.1` (localhost). In Docker, this means the server would only be accessible from within the container, not from your host machine.

The entrypoint script:
1. Starts the server with proper binding to `0.0.0.0` instead
2. Makes the server accessible from outside the container
3. Enables the health check to work correctly

If you modify `src/usaspending_mcp/server.py` to bind to `0.0.0.0` instead of `127.0.0.1`, you can remove this script and go back to using `CMD ["python", "-m", "usaspending_mcp.server"]` in the Dockerfile.

## Development Workflow

For development with live code reloading:

1. Use the local setup instead (avoid Docker):
   ```bash
   source .venv/bin/activate
   python -m usaspending_mcp.server
   ```

2. Or mount source code in docker-compose.yml for hot reloading:
   ```yaml
   volumes:
     - ./src:/app/src
     - ./docs:/app/docs
     - mcp-logs:/app/logs
   ```
   Then rebuild and restart the container.

## Production Deployment

For production use:

1. **Image Registry**: Push the image to a registry:
   ```bash
   docker tag usaspending-mcp:latest your-registry/usaspending-mcp:latest
   docker push your-registry/usaspending-mcp:latest
   ```

2. **Security**:
   - The Dockerfile runs as non-root user
   - Uses minimal base image (python:3.12-slim)
   - Includes health checks

3. **Scaling**: Use Kubernetes or Docker Swarm for orchestration

4. **Logging**: Docker logs are captured automatically. Configure log drivers in docker-compose.yml:
   ```yaml
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

## Clean Up

Remove unused Docker resources:

```bash
# Stop and remove all containers
docker-compose down

# Remove the image
docker rmi usaspending-mcp:latest

# Remove all unused Docker resources
docker system prune -a
```

## Next Steps

After the container is running, you can:

1. Configure it for Claude Desktop integration
2. Set up log aggregation
3. Configure backup and persistence strategies
4. Deploy to a cloud provider

For more information, see:
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
