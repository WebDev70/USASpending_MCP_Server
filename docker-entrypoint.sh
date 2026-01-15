#!/bin/bash
set -e

# Run the main server application
# The server.py file is now configured to listen on 0.0.0.0
# and use the PORT environment variable.
exec python3 src/usaspending_mcp/server.py
