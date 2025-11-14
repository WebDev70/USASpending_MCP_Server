# Gemini Code Assistant Context

This document provides context for the Gemini Code Assistant to understand the USASpending MCP Server project.

## Project Overview

This project is a Python-based Model Context Protocol (MCP) server that provides tools to query federal spending data from USASpending.gov and to look up Federal Acquisition Regulation (FAR) sections. The server is built using the FastMCP framework and can be used with clients like Claude Desktop or the included command-line client.

The server provides a comprehensive set of tools for searching, analyzing, and retrieving data about federal awards, recipients, and agencies. It also includes a set of tools for working with FAR regulations, including searching for sections, retrieving full text, and checking for compliance.

The project is well-documented, with a comprehensive set of user guides, API references, and architectural documents. It also includes a full suite of tests.

## Building and Running

### Prerequisites

- Python 3.10+
- `pip` and `venv`

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/WebDev70/USASpending_MCP_Server.git
    cd usaspending-mcp
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Server

The server can be run in two modes:

-   **HTTP Mode (for Claude Desktop):**
    ```bash
    ./start_mcp_server.sh
    ```
    The server will be available at `http://localhost:3002/mcp`.

-   **Stdio Mode (for testing):**
    ```bash
    PYTHONPATH=src ./.venv/bin/python -m usaspending_mcp.server --stdio
    ```

### Running the Test Client

A command-line client is provided for testing the server:

```bash
./test_mcp_client.sh
```

## Development Conventions

### Code Style

The project uses `black` for code formatting and `isort` for import sorting. Configuration for these tools can be found in `pyproject.toml`.

### Testing

The project uses `pytest` for testing. The tests are located in the `tests/` directory. To run the tests, use the following command:

```bash
pytest
```

### Architecture

The project follows a monolithic architecture, with all tools and server logic contained in a single server process. The architecture is designed to be simple, maintainable, and performant. For more details, see `docs/dev/ARCHITECTURE_GUIDE.md`.

### Logging

The server uses structured logging to provide detailed information about server activity, errors, and search analytics. Logs are written to the `logs/` directory. For more information, see `docs/guides/STRUCTURED_LOGGING_GUIDE.md`.
