"""
Server Manager - Handles automatic server startup with port cleanup

Provides utilities to detect and kill existing processes on port 3002,
then start the MCP server with automatic error recovery.
"""

import subprocess
import time
import socket
import sys
from pathlib import Path


def is_port_open(port: int = 3002, timeout: int = 1) -> bool:
    """
    Check if a port is open and responding

    Args:
        port: Port number to check
        timeout: Timeout in seconds

    Returns:
        True if port is open, False otherwise
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex(('127.0.0.1', port))
        return result == 0
    except Exception:
        return False
    finally:
        sock.close()


def get_process_on_port(port: int = 3002) -> list:
    """
    Get PIDs of processes listening on a port

    Args:
        port: Port number to check

    Returns:
        List of PIDs
    """
    try:
        # Try lsof (macOS/Linux)
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.stdout:
            pids = [int(pid) for pid in result.stdout.strip().split('\n') if pid]
            return pids
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    try:
        # Try netstat (fallback)
        result = subprocess.run(
            ["netstat", "-tlnp"],
            capture_output=True,
            text=True,
            timeout=5
        )
        pids = []
        for line in result.stdout.split('\n'):
            if f":{port}" in line:
                parts = line.split()
                if len(parts) >= 7:
                    pid_info = parts[-1]
                    if '/' in pid_info:
                        try:
                            pid = int(pid_info.split('/')[0])
                            pids.append(pid)
                        except ValueError:
                            pass
        return pids
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return []


def kill_process_on_port(port: int = 3002, force: bool = True) -> bool:
    """
    Kill processes listening on a port

    Args:
        port: Port number
        force: Use SIGKILL instead of SIGTERM

    Returns:
        True if successful or no process found, False if failed
    """
    pids = get_process_on_port(port)

    if not pids:
        return True

    signal = "-9" if force else "-15"

    for pid in pids:
        try:
            print(f"  Killing process {pid} on port {port}...")
            subprocess.run(
                ["kill", signal, str(pid)],
                timeout=5,
                check=True
            )
        except subprocess.CalledProcessError:
            print(f"  Failed to kill process {pid}")
            return False
        except Exception as e:
            print(f"  Error killing process {pid}: {e}")
            return False

    # Wait for port to be released
    print(f"  Waiting for port {port} to be released...")
    for i in range(10):
        if not get_process_on_port(port):
            print(f"  ✓ Port {port} is now available")
            return True
        time.sleep(0.5)

    print(f"  Warning: Port {port} may still be in use")
    return True


def start_mcp_server(venv_path: str = ".venv", verbose: bool = True) -> subprocess.Popen:
    """
    Start the MCP server with automatic port cleanup

    Args:
        venv_path: Path to virtual environment
        verbose: Print status messages

    Returns:
        Popen process object

    Raises:
        RuntimeError: If server fails to start
    """
    port = 3002

    if verbose:
        print("=" * 80)
        print("MCP SERVER STARTUP")
        print("=" * 80)

    # Step 1: Check and kill existing processes
    if verbose:
        print(f"\n1. Checking for existing processes on port {port}...")

    existing_pids = get_process_on_port(port)
    if existing_pids:
        if verbose:
            print(f"   Found {len(existing_pids)} process(es) on port {port}")
        if not kill_process_on_port(port):
            raise RuntimeError(f"Failed to kill process on port {port}")
    else:
        if verbose:
            print(f"   ✓ No processes on port {port}")

    # Step 2: Verify port is open
    if verbose:
        print(f"\n2. Verifying port {port} is available...")

    if is_port_open(port):
        if verbose:
            print(f"   Warning: Port {port} still has an open connection, waiting...")
        time.sleep(2)

    if verbose:
        print(f"   ✓ Port {port} is available")

    # Step 3: Start server
    if verbose:
        print(f"\n3. Starting MCP server...")

    try:
        # Construct the command to run the MCP server as a Python module
        python_exe = Path(__file__).parent / venv_path / "bin" / "python"

        # Verify the Python executable exists
        if not python_exe.exists():
            raise FileNotFoundError(f"Python executable not found at {python_exe}")

        # Start the server using Python module execution
        # This runs: python -m usaspending_mcp.server
        process = subprocess.Popen(
            [str(python_exe), "-m", "usaspending_mcp.server"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if verbose:
            print(f"   Server process started (PID: {process.pid})")

        # Step 4: Wait for server to be ready
        if verbose:
            print(f"\n4. Waiting for server to be ready...")

        max_retries = 15
        for attempt in range(max_retries):
            time.sleep(0.5)
            if is_port_open(port):
                if verbose:
                    print(f"   ✓ Server is ready on http://127.0.0.1:{port}")
                print("\n" + "=" * 80)
                return process

        # Server didn't start properly
        raise RuntimeError(f"Server did not respond on port {port} after {max_retries} attempts")

    except Exception as e:
        raise RuntimeError(f"Failed to start MCP server: {e}")


def ensure_server_running(venv_path: str = ".venv", verbose: bool = True) -> subprocess.Popen:
    """
    Ensure MCP server is running, starting it if necessary

    Args:
        venv_path: Path to virtual environment
        verbose: Print status messages

    Returns:
        Popen process object
    """
    port = 3002

    # Check if server is already running
    if is_port_open(port):
        if verbose:
            print(f"✓ MCP server is already running on port {port}")
        return None

    # Server is not running, start it
    if verbose:
        print(f"\nMCP server is not running, starting it...")

    return start_mcp_server(venv_path, verbose)


def main():
    """
    CLI interface for server manager

    Usage:
        python server_manager.py start              # Start server, kill existing process
        python server_manager.py ensure             # Start only if not running
        python server_manager.py check [--port 3002] # Check if port is open
        python server_manager.py kill [--port 3002]  # Kill process on port
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="MCP Server Manager - Manages server startup with automatic port cleanup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python server_manager.py start              Start the MCP server
  python server_manager.py ensure             Only start if not already running
  python server_manager.py check              Check if port 3002 is available
  python server_manager.py kill               Kill any process on port 3002
  python server_manager.py start --venv .venv/custom  Use custom venv path
  python server_manager.py check --port 8000  Check different port
  python server_manager.py kill --quiet       Suppress status messages
        """
    )

    parser.add_argument(
        "command",
        choices=["start", "ensure", "check", "kill"],
        help="Command to run"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3002,
        help="Port number (default: 3002)"
    )
    parser.add_argument(
        "--venv",
        default=".venv",
        help="Virtual environment path (default: .venv)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress status messages"
    )

    args = parser.parse_args()

    try:
        if args.command == "start":
            process = start_mcp_server(venv_path=args.venv, verbose=not args.quiet)
            if not args.quiet:
                print(f"\n✓ Server started successfully!")
                print(f"  You can now connect to http://127.0.0.1:{args.port}")
                print(f"  Press Ctrl+C to stop the server")
            # Keep the process running
            if process:
                try:
                    process.wait()
                except KeyboardInterrupt:
                    if not args.quiet:
                        print("\n\nShutting down server...")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()

        elif args.command == "ensure":
            process = ensure_server_running(venv_path=args.venv, verbose=not args.quiet)
            if process:
                if not args.quiet:
                    print(f"✓ Server started successfully!")
                try:
                    process.wait()
                except KeyboardInterrupt:
                    if not args.quiet:
                        print("\n\nShutting down server...")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()

        elif args.command == "check":
            if is_port_open(args.port):
                print(f"✓ Port {args.port} is open")
                sys.exit(0)
            else:
                print(f"✗ Port {args.port} is not open")
                sys.exit(1)

        elif args.command == "kill":
            if kill_process_on_port(args.port, force=True):
                if not args.quiet:
                    print(f"✓ Killed processes on port {args.port}")
                sys.exit(0)
            else:
                print(f"✗ Failed to kill processes on port {args.port}", file=sys.stderr)
                sys.exit(1)

    except RuntimeError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n\nInterrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
