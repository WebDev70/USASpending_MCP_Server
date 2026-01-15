# Gemini Code Assistant Context

This document provides context for the Gemini Code Assistant to understand the `usaspending-mcp` project.

## Project Overview

The `usaspending-mcp` project is a Python-based server that provides access to USASpending.gov federal spending data and Federal Acquisition Regulation (FAR) lookup tools through the Model Context Protocol (MCP). It allows users to query federal spending data using natural language and to look up FAR regulations.

The project is built using the `fastmcp` framework and uses `httpx` for making HTTP requests to the USASpending.gov API. The server can be run in either stdio or HTTP mode.

The project is well-structured, with a modular design that separates the server, tools, and data loaders into different modules. It also includes a comprehensive test suite that uses `pytest` and `unittest.mock`.

## Building and Running

### Prerequisites

*   Python 3.10+
*   pip

### Installation

1.  Create a virtual environment:
    ```bash
    python3 -m venv .venv
    ```
2.  Activate the virtual environment:
    ```bash
    source .venv/bin/activate
    ```
3.  Install the dependencies:
    ```bash
    pip install -e ".[dev]"
    ```

### Running the Server

The server can be run in two modes:

*   **stdio mode:**
    ```bash
    python3 src/usaspending_mcp/server.py --stdio
    ```
*   **HTTP mode:**
    ```bash
    python3 src/usaspending_mcp/server.py
    ```
The HTTP server runs on `http://localhost:3002`.

### Running the Tests

To run the tests, use the following command:
```bash
pytest
```

## Development Conventions

*   **Code Style:** The project uses `black` for code formatting and `isort` for import sorting.
*   **Linting:** The project uses `flake8` for linting.
*   **Type Checking:** The project uses `mypy` for static type checking.
*   **Testing:** The project uses `pytest` for testing. Tests are located in the `tests` directory and are organized into `unit` and `integration` subdirectories. Test files are named `test_*.py`.
*   **Modularity:** The project is organized into modules, with each module having a specific responsibility. The main server file (`src/usaspending_mcp/server.py`) is responsible for registering the tools and running the server. The tools are located in the `src/usaspending_mcp/tools` directory, and the data loaders are located in the `src/usaspending_mcp/loaders` directory.
