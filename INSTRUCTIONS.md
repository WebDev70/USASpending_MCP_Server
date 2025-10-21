# Running Instructions

## 🚀 Running the USASpending MCP Server

### **Option 1: Quick Test (Recommended for First Time)**

Run this single command to test everything:

```bash
./test_mcp_client.sh
```

**What it does:**
- Automatically starts the server in stdio mode
- Connects with the MCP client
- Lists available tools
- Prompts you for a search query
- Displays results
- Shuts down cleanly when done

**Example session:**
```bash
./test_mcp_client.sh
# Enter keyword: software development
# Enter results: 5
# (Shows results)
```

---

### **Option 2: Run HTTP Server for Claude Desktop**

If you want to use the server with Claude Desktop:

```bash
# Step 1: Start the HTTP server
./start_mcp_server.sh

# The server is now running on http://localhost:3002/mcp
# Keep this terminal open while using Claude Desktop

# Step 2: Configure Claude Desktop (one-time setup)
# Add to Claude Desktop config:
# macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
# Windows: %APPDATA%\Claude\claude_desktop_config.json

# Step 3: Use Claude Desktop
# Ask Claude: "Find software development contracts"

# Step 4: When done, press Ctrl+C in the server terminal to stop
```

---

### **Option 3: Manual Testing (Advanced)**

If you want more control:

```bash
# Terminal 1: Start server in stdio mode (for testing)
./.venv/bin/python mcp_server.py
./.venv/bin/python mcp_client.py

# Follow the prompts to test queries
```

---

### **Quick Reference**

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `./test_mcp_client.sh` | Test the server | Development, testing, verifying it works |
| `./start_mcp_server.sh` | Start HTTP server | Using with Claude Desktop |
| `./.venv/bin/python mcp_client.py` | Manual client | Custom testing |

---

### **Troubleshooting**

**If scripts won't run:**
```bash
chmod +x test_mcp_client.sh start_mcp_server.sh
```

**If "command not found":**
```bash
# Make sure you're in the project directory
cd /path/to/usaspending-mcp

# Activate virtual environment
source .venv/bin/activate
```

**To stop the HTTP server:**
- Press `Ctrl+C` in the terminal running `start_mcp_server.sh`

---

**That's it!** For most testing, just run `./test_mcp_client.sh` and you're done! 🎉
