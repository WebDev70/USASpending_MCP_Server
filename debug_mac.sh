#!/bin/bash
# Debug script for Mac
# Run: bash debug_mac.sh

echo "🔍 USASpending MCP Server Debug Information"
echo "=========================================="
echo ""

echo "System Information:"
echo "  OS: $(sw_vers -productName) $(sw_vers -productVersion)"
echo "  User: $(whoami)"
echo "  Home: $HOME"
echo ""

echo "Python Information:"
if command -v python3 &> /dev/null; then
    echo "  ✓ Python 3: $(which python3)"
    echo "  ✓ Version: $(python3 --version)"
else
    echo "  ❌ Python 3 not found"
fi
echo ""

PROJECT_DIR="$HOME/usaspending-mcp"

echo "Project Directory:"
if [ -d "$PROJECT_DIR" ]; then
    echo "  ✓ Directory exists: $PROJECT_DIR"
    
    if [ -d "$PROJECT_DIR/venv" ]; then
        echo "  ✓ Virtual environment exists"
        
        if [ -f "$PROJECT_DIR/venv/bin/python" ]; then
            echo "  ✓ Python in venv: $PROJECT_DIR/venv/bin/python"
            echo "  ✓ Version: $($PROJECT_DIR/venv/bin/python --version)"
        else
            echo "  ❌ Python not found in venv"
        fi
    else
        echo "  ❌ Virtual environment not found"
    fi
    
    if [ -f "$PROJECT_DIR/usaspending_mcp_server.py" ]; then
        echo "  ✓ Server file exists"
        if [ -x "$PROJECT_DIR/usaspending_mcp_server.py" ]; then
            echo "  ✓ Server file is executable"
        else
            echo "  ⚠️  Server file is not executable"
            echo "     Run: chmod +x $PROJECT_DIR/usaspending_mcp_server.py"
        fi
    else
        echo "  ❌ Server file not found"
    fi
else
    echo "  ❌ Project directory not found: $PROJECT_DIR"
fi
echo ""

echo "Claude Desktop Configuration:"
CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ -f "$CONFIG_FILE" ]; then
    echo "  ✓ Config file exists"
    echo "  Content:"
    cat "$CONFIG_FILE" | python3 -m json.tool 2>&1 | sed 's/^/    /'
else
    echo "  ❌ Config file not found: $CONFIG_FILE"
fi
echo ""

echo "Testing API Connection:"
cd "$PROJECT_DIR"
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    python3 -c "
import httpx
import asyncio

async def test():
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get('https://api.usaspending.gov/api/v2/')
            print('  ✓ USASpending API is reachable')
            return True
    except Exception as e:
        print(f'  ❌ API Error: {e}')
        return False

asyncio.run(test())
"
fi
echo ""

echo "Installed Packages:"
if [ -f "$PROJECT_DIR/venv/bin/pip" ]; then
    $PROJECT_DIR/venv/bin/pip list 2>/dev/null | grep -E "mcp|httpx|pydantic" | sed 's/^/  /'
fi
echo ""

echo "Recent Claude Logs:"
LOG_DIR="$HOME/Library/Logs/Claude"
if [ -d "$LOG_DIR" ]; then
    echo "  Log directory: $LOG_DIR"
    echo "  Recent log files:"
    ls -lt "$LOG_DIR" | head -5 | sed 's/^/    /'
else
    echo "  ⚠️  Log directory not found"
fi
echo ""

echo "=========================================="
echo "Debug information collected!"
echo ""
echo "If you're still having issues, share this output."