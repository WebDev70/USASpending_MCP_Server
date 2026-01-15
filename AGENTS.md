# Repository Guidelines

## Project Structure & Module Organization
- `src/usaspending_mcp/` contains the FastMCP server, tools, loaders, and runtime data.
- `tests/` holds unit tests (`tests/unit/`) and scripts (`tests/scripts/`); `tests/integration/` is reserved for networked tests.
- `docs/` contains user guides, reference data, and developer docs (architecture, testing, monitoring).
- Root scripts like `start_mcp_server.sh` and `tests/scripts/run_tests.sh` provide common workflows.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: create/activate the local venv.
- `pip install -e ".[dev]"`: install runtime and developer dependencies.
- `PYTHONPATH=src python -m usaspending_mcp.server --stdio`: run stdio mode for local testing.
- `./start_mcp_server.sh`: start the HTTP server for Claude Desktop (`http://127.0.0.1:3002/mcp`).
- `./tests/scripts/run_tests.sh`: interactive test runner menu.
- `pytest tests/unit -v`: run unit tests directly.

## Coding Style & Naming Conventions
- Python formatting uses Black and isort; line length is 100 (`pyproject.toml`).
- Linting uses Flake8 with `max-line-length=100` and ignores `E203,W503` (`.flake8`).
- Use `snake_case` for functions/modules, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants.

## Testing Guidelines
- Frameworks: `pytest`, `pytest-asyncio`, and `pytest-cov`.
- Test discovery follows `test_*.py` and `Test*` conventions (`pytest.ini`).
- Markers include `unit`, `integration`, `slow`, and `critical`.
- Logs write to `logs/test.log`; coverage output goes to `htmlcov/`.

## Commit & Pull Request Guidelines
- Commits are short, imperative, and often use a category prefix (e.g., `Fix:`, `Refactor:`, `Added`).
- PRs should describe the change, include relevant commands run (e.g., `pytest tests/unit -v`), and link issues if applicable.
- If behavior changes or new tools are added, update the relevant docs in `docs/` or `README.md`.

## Security & Configuration Tips
- The server calls the public USASpending.gov API; no API key is required.
- Use a local `.env` for optional runtime configuration (loaded via `python-dotenv`).
