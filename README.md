# USASpending MCP Server with FAR Regulatory Tools

printf "test\n1\n" | ./test_mcp_client.sh 2>/dev/null | tail -15;

A FastMCP server that provides access to USASpending.gov federal spending data and FAR (Federal Acquisition Regulation) lookup tools through the Model Context Protocol (MCP). Query contracts, grants, loans, and other federal awards using natural language, and reference procurement regulations instantly.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🔍 **Natural language queries** for federal spending data
- ⚖️ **Multi-part FAR lookup tools** for procurement professionals (Parts 14, 15, 16, 19)
  - `lookup_far_section` - Direct section lookup by number (auto-detects part)
  - `search_far` - Cross-part keyword search with relevance scoring
  - `list_far_sections` - Complete FAR index (210 sections across all parts)
- 🚀 **FastMCP integration** for modern MCP protocol support
- 🔌 **Dual transport modes**: stdio (testing) and HTTP (Claude Desktop)
- 📊 **Real-time data** from USASpending.gov API
- 💰 **Smart currency formatting** (B/M/K notations)
- 🛠️ **Easy testing** with included MCP client

## Quick Start

### 1. Setup

```bash
# Clone the repository
git clone https://github.com/WebDev70/USASpending_MCP_Server.git
cd usaspending-mcp

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Test the Server

```bash
# Run the test client (recommended)
./test_mcp_client.sh

# Or run directly
./.venv/bin/python mcp_client.py
```

**Example queries:**
- "space" - Find space-related contracts
- "software development" - Search for software contracts
- "construction" - Find construction projects

### 3. Use with Claude Desktop

```bash
# Start the HTTP server
./start_mcp_server.sh
```

Then configure Claude Desktop to connect to `http://localhost:3002/mcp`

## Project Structure

```
usaspending-mcp/
├── mcp_server.py           # FastMCP server (main application)
├── mcp_client.py           # MCP test client
├── requirements.txt        # Python dependencies
├── README.md               # This file (main entry point)
├── docs/                   # Documentation
│   ├── QUICKSTART.md       # Quick start guide
│   ├── INSTRUCTIONS.md     # Complete user guide
│   ├── TROUBLESHOOTING_GUIDE.md
│   ├── QUERY_PATTERNS_COOKBOOK.md
│   ├── api/                # API reference docs
│   │   ├── MCP_API_REFERENCE.md
│   │   ├── USASPENDING_API_V2_SEARCH_ENDPOINTS.md
│   │   └── USASPENDING_API_V2_EXAMPLES_AND_APPENDIX.md
│   └── dev/                # Developer documentation
│       ├── ARCHITECTURE_GUIDE.md
│       ├── TESTING_GUIDE.md
│       ├── SERVER_MANAGER_GUIDE.md
│       └── PRODUCTION_MONITORING_GUIDE.md
├── start_mcp_server.sh     # Start HTTP server for Claude Desktop
├── test_mcp_client.sh      # Test script (recommended)
└── LICENSE                 # MIT License
```

## Usage

### Testing Mode (stdio)

The server supports stdio transport for testing and development:

```bash
# Using the test script
./test_mcp_client.sh

# Or run the client directly
./.venv/bin/python mcp_client.py
```

When prompted:
1. Enter a keyword (e.g., "space", "software", "construction")
2. Enter number of results to display (default: 3)

**Example output:**
```
Found 146647 total matches (showing 3):

1. ROLLS-ROYCE PLC
   Award ID: Z69Z
   Amount: $1.34M
   Type: Contract
   Description: SPACER ASSEMBLY
```

### Production Mode (HTTP for Claude Desktop)

Start the HTTP server for Claude Desktop integration:

```bash
./start_mcp_server.sh
```

The server will start on `http://127.0.0.1:3002/mcp`

## Claude Desktop Integration

### Configuration

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "usaspending": {
      "command": "/path/to/usaspending-mcp/.venv/bin/python",
      "args": [
        "/path/to/usaspending-mcp/mcp_server.py",
        "--stdio"
      ]
    }
  }
}
```

**Or use HTTP transport:**

```json
{
  "mcpServers": {
    "usaspending": {
      "url": "http://localhost:3002/mcp"
    }
  }
}
```

### Using with Claude

Once configured, you can ask Claude:
- "Find recent software development contracts"
- "Show me construction grants over $1M"
- "Search for space technology awards"

## Available Tools

### search_federal_awards

Search federal spending data from USASpending.gov.

**Parameters:**
- `query` (string, required): Keywords to search for
- `max_results` (integer, optional): Number of results (default: 5, max: 100)

**Returns:** Formatted list of federal awards with:
- Recipient name
- Award ID
- Amount (formatted: $1.5B, $250M, $75K)
- Award type
- Description

**Example:**
```python
{
  "query": "artificial intelligence",
  "max_results": 10
}
```

## Development

### Running Tests

```bash
# Quick test
./test_mcp_client.sh

# Manual testing
./.venv/bin/python mcp_client.py
```

### Server Modes

The server supports two modes:

**1. stdio Mode (for MCP clients and testing)**
```bash
python mcp_server.py --stdio
```

**2. HTTP Mode (for Claude Desktop)**
```bash
python mcp_server.py
# Starts on http://127.0.0.1:3002/mcp
```

### Code Structure

**mcp_server.py:**
- FastMCP server initialization
- Tool definitions (`@app.tool` decorator)
- USASpending.gov API integration
- Dual transport support (stdio/HTTP)

**mcp_client.py:**
- MCP protocol client
- stdio transport
- Testing and validation

## API Details

### USASpending.gov API

The server queries the official USASpending.gov API v2:
- Endpoint: `https://api.usaspending.gov/api/v2`
- Documentation: https://api.usaspending.gov/
- No API key required

### Search Features

- **Keyword search**: Searches award descriptions, recipient names
- **Award types**: Contracts (A, B, C, D)
- **Time period**: Last 6 years (configurable)
- **Smart filtering**: Removes common stop words
- **Result formatting**: Human-readable currency and descriptions

## Troubleshooting

### "Module not found" errors
```bash
# Ensure you're in the virtual environment
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### "Permission denied" on scripts
```bash
chmod +x test_mcp_client.sh
chmod +x start_mcp_server.sh
```

### "Connection refused" errors
- Ensure the server is running
- Check firewall settings
- Verify port 3002 is available

### Claude Desktop can't connect
- Verify the config file path
- Check server is running
- Look at Claude Desktop logs for details

## Requirements

- Python 3.10+
- Internet connection (for USASpending.gov API)
- macOS, Linux, or Windows

### Python Dependencies

- `fastmcp>=1.0.0` - FastMCP framework
- `mcp>=1.18.0` - MCP protocol library
- `httpx>=0.27.0` - HTTP client
- `uvicorn[standard]>=0.15.0` - ASGI server
- `pydantic>=2.0.0` - Data validation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Data provided by [USASpending.gov](https://www.usaspending.gov/)
- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- Model Context Protocol by [Anthropic](https://www.anthropic.com/)

## Support

- 📧 Issues: https://github.com/WebDev70/USASpending_MCP_Server/issues
- 📚 MCP Documentation: https://modelcontextprotocol.io/
- 🌐 USASpending API Docs: https://api.usaspending.gov/

## Changelog

### v2.0.0 (Current)
- ✅ Migrated to FastMCP framework
- ✅ Added dual transport support (stdio/HTTP)
- ✅ Improved MCP protocol compliance
- ✅ Added dedicated MCP test client
- ✅ Cleaned up deprecated code
- ✅ Enhanced documentation

### v1.0.0
- Initial release with manual MCP implementation
