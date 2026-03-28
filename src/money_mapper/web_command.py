"""Web server CLI command for Money Mapper.

Provides the 'money-mapper web' command to launch the FastAPI web interface.
"""

import socket
import sys
import webbrowser

import uvicorn

from money_mapper.api import create_app


def find_available_port(start: int = 8000) -> int:
    """Find an available port starting from the given port number.

    Args:
        start: Starting port number (default: 8000)

    Returns:
        int: First available port number

    Raises:
        RuntimeError: If no ports available in reasonable range
    """
    for port in range(start, start + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue

    raise RuntimeError(f"Could not find available port between {start} and {start + 100}")


def launch_browser(url: str, no_browser: bool = False) -> None:
    """Launch browser to open the web interface.

    Args:
        url: URL to open (e.g., http://localhost:8000)
        no_browser: If True, skip browser launch

    Returns:
        None
    """
    if no_browser:
        return

    try:
        webbrowser.open(url)
    except Exception:  # noqa: B110
        # Silent fail - user can manually open browser
        pass


def start_web_server(
    host: str = "localhost",
    port: int = 8000,
    auto_port: bool = True,
    no_browser: bool = False,
) -> None:
    """Start the FastAPI web server.

    Args:
        host: Host to bind to (default: localhost)
        port: Port to bind to (default: 8000)
        auto_port: If True, find available port if default is taken
        no_browser: If True, don't auto-open browser

    Returns:
        None
    """
    # Find available port if auto_port is enabled
    if auto_port and port == 8000:
        try:
            port = find_available_port(port)
        except RuntimeError as e:
            print(f"Error: {e}")
            sys.exit(1)

    # Validate port range
    if not (1 <= port <= 65535):
        print(f"Error: Invalid port number {port}. Must be between 1 and 65535")
        sys.exit(1)

    # Create the FastAPI app
    try:
        app = create_app()
    except ImportError as e:
        print(f"Error: Could not load web interface: {e}")
        sys.exit(1)

    # Build the URL
    url = f"http://{host if host != '0.0.0.0' else 'localhost'}:{port}"

    # Display startup message
    print("=" * 60)
    print("Money Mapper Web Interface")
    print("=" * 60)
    print(f"Starting server on {url}")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)

    # Launch browser
    launch_browser(url, no_browser=no_browser)

    # Start the server
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        print("\nServer stopped")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def web_command(args) -> int:
    """Handle the 'web' command.

    Args:
        args: Parsed CLI arguments

    Returns:
        int: Exit code (0 for success)
    """
    host = args.host or "localhost"
    port = int(args.port) if args.port else 8000
    no_browser = getattr(args, "no_browser", False)

    # Validate inputs
    if not (1 <= port <= 65535):
        print(f"Error: Invalid port number {port}. Must be between 1 and 65535")
        return 1

    # Start the web server
    start_web_server(host=host, port=port, auto_port=True, no_browser=no_browser)

    return 0
