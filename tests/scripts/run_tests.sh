#!/bin/bash

# USASpending MCP Server - Test Runner Script
# Comprehensive testing for all 21 MCP tools

set -e

# Navigate to project root (two directories up from tests/scripts/)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}USASpending MCP Server - Comprehensive Test Suite${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest not found. Installing...${NC}"
    pip install pytest pytest-asyncio httpx
fi

# Menu
show_menu() {
    echo -e "${BLUE}Select test suite to run:${NC}"
    echo "  1) All tests (unit + integration)"
    echo "  2) Unit tests only (fast)"
    echo "  3) Integration tests only (slow, requires network)"
    echo "  4) Critical path tests (Giga Inc award)"
    echo "  5) Error handling tests"
    echo "  6) Performance tests"
    echo "  7) Coverage report"
    echo "  8) Run specific test by name"
    echo "  0) Exit"
    echo
}

run_all_tests() {
    echo -e "${GREEN}Running all tests...${NC}"
    pytest . -v --tb=short
}

run_unit_tests() {
    echo -e "${GREEN}Running unit tests...${NC}"
    pytest test_mcp_tools_unit.py -v --tb=short
}

run_integration_tests() {
    echo -e "${GREEN}Running integration tests (network required)...${NC}"
    pytest test_mcp_tools_integration.py -v --tb=short -s
}

run_critical_path() {
    echo -e "${GREEN}Running critical path tests (Giga Inc award)...${NC}"
    pytest test_mcp_tools_integration.py::TestCriticalPathGigaInc -v -s
}

run_error_handling() {
    echo -e "${GREEN}Running error handling tests...${NC}"
    pytest test_mcp_tools_integration.py::TestErrorHandling -v -s
}

run_performance() {
    echo -e "${GREEN}Running performance tests...${NC}"
    pytest test_mcp_tools_integration.py::TestPerformance -v -s
}

run_coverage() {
    echo -e "${GREEN}Generating coverage report...${NC}"

    if ! command -v coverage &> /dev/null; then
        echo -e "${YELLOW}Installing coverage...${NC}"
        pip install coverage pytest-cov
    fi

    pytest --cov=mcp_server --cov-report=html --cov-report=term-missing test_mcp_tools_unit.py
    echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
}

run_specific_test() {
    echo -e "${YELLOW}Enter test name or pattern (e.g., test_giga or TestCriticalPath):${NC}"
    read -p "> " test_name

    if [ -z "$test_name" ]; then
        echo -e "${RED}No test name provided${NC}"
        return
    fi

    echo -e "${GREEN}Running tests matching: $test_name${NC}"
    pytest -k "$test_name" -v -s
}

# Main loop
while true; do
    show_menu
    read -p "Enter your choice (0-8): " choice

    case $choice in
        1)
            run_all_tests
            ;;
        2)
            run_unit_tests
            ;;
        3)
            run_integration_tests
            ;;
        4)
            run_critical_path
            ;;
        5)
            run_error_handling
            ;;
        6)
            run_performance
            ;;
        7)
            run_coverage
            ;;
        8)
            run_specific_test
            ;;
        0)
            echo -e "${BLUE}Exiting test runner${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Please try again.${NC}"
            ;;
    esac

    echo
    read -p "Press Enter to continue..."
    clear
done
