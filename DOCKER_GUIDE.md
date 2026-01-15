# Docker Setup Guide

This guide explains how to containerize and run the **USASpending MCP Server** using Docker. The server provides access to federal spending data and FAR regulations through the Model Context Protocol (MCP).

## What is USASpending MCP Server?

A FastMCP-based server that provides **32 tools** organized across 6 modules:
- **Award Discovery** (6 tools) - Search and analyze federal awards
- **Spending Analysis** (8 tools) - Analyze spending patterns and trends
- **Classification Analysis** (5 tools) - Industry, product type, and budget analysis
- **Vendor & Agency Profiles** (4 tools) - Detailed profiles and analytics
- **Conversation Management** (4 tools) - Track and analyze interaction history
- **FAR Regulations** (5 tools) - Federal Acquisition Regulation lookup and analysis

The refactored 2024 architecture organizes all tools into focused modules for maintainability and ease of development.

## Prerequisites

- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)
- Git (for cloning the repository)
- ~512MB RAM available (container default limit)

## Quick Reference Commands

```bash
# Build and start the server
docker compose up --build -d

# Start (after already built)
docker compose up -d

# Stop the server
docker compose down

# View live logs
docker compose logs -f

# Full rebuild with clean volumes
docker compose down -v && docker compose up --build -d

# Execute command in running container (using service name)
docker compose exec usaspending-mcp bash

# Or using container name directly
docker exec -it usaspending-mcp-server bash
```


## Files Added

Four new files have been created for Docker support:

1. **Dockerfile** - Multi-stage Docker build configuration with proper host binding
2. **docker compose.yml** - Docker Compose configuration for easy management
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
docker compose down
```

To view logs:

```bash
docker compose logs -f usaspending-mcp
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

You can set environment variables in the `docker compose.yml` file:

```yaml
environment:
  PYTHONUNBUFFERED: "1"
  PYTHONDONTWRITEBYTECODE: "1"
  # Add other environment variables here
```

### Port Mapping

By default, the server runs on port 3002. If you need to use a different port, modify the `docker compose.yml`:

```yaml
ports:
  - "YOUR_PORT:3002"
```

Or when using `docker run`:

```bash
docker run -p YOUR_PORT:3002 usaspending-mcp:latest
```

### Resource Limits

The docker compose.yml includes resource limits. Adjust as needed:

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
   docker compose up --build
   ```
4. The server will appear in the Containers list with status **Running**

### Monitoring

In Docker Desktop:
- Click the container to see **Logs**
- View **Inspect** tab for detailed container information
- Use the **Stats** tab to monitor CPU and memory usage

### Stopping

- In Docker Desktop, click the stop button on the container
- Or use: `docker compose down`

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
docker compose logs -f usaspending-mcp

# Or with docker CLI
docker logs -f usaspending-mcp
```

To actually test the MCP tools, you'll need an MCP client configured to connect to the server.

## Troubleshooting

### Container Won't Start

1. Check logs: `docker compose logs usaspending-mcp`
2. Verify port 3002 is not in use: `lsof -i :3002`
3. If port is busy, either:
   - Kill the process: `kill -9 <PID>`
   - Change the port in docker compose.yml

### Health Check Failing

The container health check verifies the server is responding on port 3002. If it fails:

1. Check logs: `docker compose logs usaspending-mcp`
2. Wait longer - the server may still be starting (10 second grace period)
3. Verify the server is accessible:
   ```bash
   curl -v http://localhost:3002/
   ```
4. If port 3002 is not accessible from your host, ensure:
   - Docker Desktop is running
   - Port 3002 is not blocked by a firewall
   - Port mapping is correct in docker compose.yml

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

### Server Architecture

The USASpending MCP Server follows a **refactored modular architecture** (2024):

```
server.py (199 lines)
    ↓ (imports and registers)
tools/__init__.py (register_all_tools coordinator)
    ├── awards.py (6 tools)
    ├── spending.py (8 tools)
    ├── classifications.py (5 tools)
    ├── profiles.py (4 tools)
    ├── conversations.py (4 tools)
    └── far.py (5 tools)
```

Key improvements:
- **Server file reduced from 4,515 → 199 lines** (95.6% reduction!)
- **Modular tool registration** - Each category in its own module
- **Shared utilities** in `tools/helpers.py` for all modules
- **Dependency injection via closures** - Clean, testable architecture

### The Entrypoint Script

The `docker-entrypoint.sh` script is necessary because the server code binds to `127.0.0.1` (localhost). In Docker, this means the server would only be accessible from within the container, not from your host machine.

The entrypoint script:
1. Starts the server with proper binding to `0.0.0.0` instead
2. Makes the server accessible from outside the container (port 3002)
3. Enables the health check to work correctly

The modular architecture doesn't change this requirement—tools still register through the same mechanism, just organized across modules now.

If you modify `src/usaspending_mcp/server.py` to bind to `0.0.0.0` instead of `127.0.0.1`, you can remove this script and go back to using `CMD ["python", "-m", "usaspending_mcp.server"]` in the Dockerfile.

### Understanding the Modular Tools Architecture

The server runs 32 tools organized into 6 focused modules:

**In the container**, the tools are loaded and registered as follows:

```
Container Startup
    ↓
server.py initializes:
    - FastMCP app
    - HTTP client
    - Rate limiter
    - Agency/award type mappings
    ↓
Calls register_all_tools() from tools/__init__.py
    ↓
    ├─→ awards.register_tools()     # 6 award discovery tools
    ├─→ spending.register_tools()   # 8 spending analysis tools
    ├─→ classifications.register_tools() # 5 classification tools
    ├─→ profiles.register_tools()   # 4 profile tools
    ├─→ conversations.register_tools()  # 4 conversation tools
    └─→ far.register_tools()        # 5 FAR regulation tools
    ↓
All 32 tools available on http://localhost:3002
```

Each tool module uses **dependency injection via closures**:
- Tools are defined inside `register_tools()` function
- They automatically access `http_client`, `rate_limiter`, `logger` from outer scope
- This keeps tool signatures clean and dependencies centralized

This modular design makes the container:
- ✅ **Easier to maintain** - Each category in its own file
- ✅ **Easier to test** - Can mock dependencies per module
- ✅ **Easier to extend** - Add tools without touching server.py or __init__.py
- ✅ **More organized** - 199-line server.py instead of 4,515 lines

## Development Workflow

### Local Development (Recommended)

For active development, use the local setup to avoid Docker overhead:

```bash
# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run the server locally
python -m usaspending_mcp.server

# Or use stdio mode for testing
python -m usaspending_mcp.server --stdio
```

### Docker Development with Live Code Reloading

If you prefer Docker development, mount source code for hot reloading:

```yaml
# In docker compose.yml
volumes:
  - ./src:/app/src              # Live reload Python source
  - ./docs:/app/docs            # Documentation
  - mcp-logs:/app/logs          # Log persistence
```

Then rebuild and restart:

```bash
docker compose down
docker compose up --build -d
```

### Adding New Tools in Development

Since the refactored architecture organizes tools into modules:

1. **Edit the appropriate module file:**
   - `src/usaspending_mcp/tools/awards.py` - For award discovery tools
   - `src/usaspending_mcp/tools/spending.py` - For spending analysis tools
   - `src/usaspending_mcp/tools/classifications.py` - For classification tools
   - `src/usaspending_mcp/tools/profiles.py` - For profile tools
   - `src/usaspending_mcp/tools/conversations.py` - For conversation tools
   - `src/usaspending_mcp/tools/far.py` - For FAR regulation tools

2. **Add your tool inside the `register_tools()` function:**
   ```python
   @app.tool(name="my_new_tool", description="...")
   async def my_new_tool(param: str) -> TextContent:
       # Your implementation
       await rate_limiter.wait_if_needed("default")
       response = await http_client.get(f"{base_url}/endpoint")
       return TextContent(type="text", text=result)
   ```

3. **No changes needed to server.py or tools/__init__.py!**
   The tool is automatically registered by the existing registration flow.

4. **Restart the server:**
   - **Local:** Server auto-restarts (with live reload)
   - **Docker:** `docker compose restart usaspending-mcp`

For detailed tool development guide, see `docs/guides/QUICKSTART.md` or `docs/archived/JUNIOR_DEVELOPER_GUIDE.md`.

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

4. **Logging**: Docker logs are captured automatically. Configure log drivers in docker compose.yml:
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
docker compose down

# Remove the image
docker rmi usaspending-mcp:latest

# Remove all unused Docker resources
docker system prune -a
```

## Next Steps

After the container is running, you can:

### 1. Configure Claude Desktop Integration

**IMPORTANT:** Claude Desktop connects to the Docker container via `docker exec`, not HTTP.

#### Configuration Steps

1. **Ensure the container is running:**
   ```bash
   docker ps | grep usaspending-mcp-server
   ```

2. **Locate your Claude Desktop config file:**
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux:** `~/.config/Claude/claude_desktop_config.json`

3. **Add this configuration:**
   ```json
   {
     "mcpServers": {
       "usaspending": {
         "command": "docker",
         "args": [
           "exec",
           "-i",
           "usaspending-mcp-server",
           "python",
           "-m",
           "usaspending_mcp.server",
           "--stdio"
         ]
       }
     }
   }
   ```

4. **Restart Claude Desktop:**
   - **macOS:** Cmd+Q to quit, then reopen
   - **Windows:** File → Exit, then reopen

5. **Verify it's working:**
   - Start a new conversation in Claude Desktop
   - Ask: "What MCP tools do you have access to?"
   - Claude should list all 32 USASpending tools

#### Troubleshooting Claude Desktop Connection

**Check Claude Desktop logs:**
```bash
# macOS
tail -f ~/Library/Logs/Claude/mcp-server-usaspending.log

# Windows
type %LOCALAPPDATA%\Claude\logs\mcp-server-usaspending.log

# Linux
tail -f ~/.config/Claude/logs/mcp-server-usaspending.log
```

**Common issues:**
- **"No such container"** - Wrong container name. Use `usaspending-mcp-server` (not `usaspending-mcp`)
- **"Docker not found"** - Docker Desktop not running or docker command not in PATH
- **"Permission denied"** - Docker Desktop needs to be running as your user

All 32 tools will be available in Claude conversations once connected

### 2. Development & Extension

The refactored modular architecture makes it easy to:

- **Add new tools** - Edit the appropriate module in `tools/`
- **Modify existing tools** - Find the tool in its category module
- **Understand the codebase** - Refer to:
  - `docs/archived/HIGH_SCHOOL_GUIDE.md` - Educational guide on architecture
  - `docs/archived/JUNIOR_DEVELOPER_GUIDE.md` - Professional development guide
  - `CLAUDE.md` - Quick reference for Claude Code integration

### 3. Monitoring & Logging

```bash
# View all logs
docker compose logs -f

# View only server logs
docker compose logs -f usaspending-mcp

# Tail last 100 lines
docker compose logs --tail=100

# Save logs to file
docker compose logs > server.log
```

### 4. Production Considerations

- **Security**: Server runs as non-root user (appuser)
- **Health checks**: Automatically configured in docker compose.yml
- **Resource limits**: Default 1 CPU, 512MB RAM (adjust in docker compose.yml)
- **Restart policy**: Set to `unless-stopped` (restart on failure)
- **Log rotation**: Configure in docker compose.yml to prevent disk overflow

### 5. Scaling

For scaling the service:

```bash
# Use multiple container instances
docker compose up -d --scale usaspending-mcp=3

# Or use Kubernetes/Docker Swarm for orchestration
# See production deployment documentation
```

## Resources

**Architecture & Design:**
- [CLAUDE.md](CLAUDE.md) - Project overview and architecture
- [docs/archived/HIGH_SCHOOL_GUIDE.md](docs/archived/HIGH_SCHOOL_GUIDE.md) - Educational architecture guide
- [docs/archived/JUNIOR_DEVELOPER_GUIDE.md](docs/archived/JUNIOR_DEVELOPER_GUIDE.md) - Developer reference

**Tool Documentation:**
- [docs/guides/QUICKSTART.md](docs/guides/QUICKSTART.md) - Getting started with tools
- [docs/API_RESOURCES.md](docs/API_RESOURCES.md) - API reference
- [docs/IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md) - Recent implementations

**Docker Resources:**
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Python Docker Best Practices](https://docs.docker.com/language/python/)
