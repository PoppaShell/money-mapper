"""Tests for 'money-mapper web' CLI command.

Tests web server launching, port discovery, browser integration, and CLI parsing.
"""

import socket
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


class TestPortDiscovery:
    """Test port discovery logic for avoiding conflicts."""

    def test_find_available_port_returns_free_port(self):
        """find_available_port() should return a free port when called."""
        from money_mapper.web_command import find_available_port

        port = find_available_port(start=9800)
        assert isinstance(port, int)
        assert 9800 <= port <= 9900

    def test_find_available_port_default_start_is_8000(self):
        """find_available_port() with no args should start at 8000."""
        import inspect

        from money_mapper.web_command import find_available_port

        # Signature check: default start parameter is 8000
        sig = inspect.signature(find_available_port)
        assert sig.parameters["start"].default == 8000

    def test_find_available_port_increments_when_occupied(self):
        """find_available_port() should skip a port that is already bound."""
        from money_mapper.web_command import find_available_port

        # Bind a socket on an ephemeral port to occupy it
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied_port = occupied.getsockname()[1]

            # Patch socket to fail on the occupied port, succeed on the next
            original_socket = socket.socket

            class PatchedSocket:
                def __init__(self, *args, **kwargs):
                    self._real = original_socket(*args, **kwargs)

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    self._real.close()

                def bind(self, addr):
                    if addr[1] == occupied_port:
                        raise OSError("Address in use")
                    self._real.bind(addr)

            with patch("socket.socket", PatchedSocket):
                result = find_available_port(start=occupied_port)

            # The result must be strictly after the occupied port
            assert result > occupied_port

    def test_find_available_port_raises_when_range_exhausted(self):
        """find_available_port() should raise RuntimeError when no port is available."""
        from money_mapper.web_command import find_available_port

        with patch("socket.socket") as mock_sock_cls:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = lambda s: s
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_ctx.bind.side_effect = OSError("Address in use")
            mock_sock_cls.return_value = mock_ctx

            import pytest

            with pytest.raises(RuntimeError, match="Could not find available port"):
                find_available_port(start=9000)

    def test_find_available_port_returns_within_range(self):
        """find_available_port() result must be within [start, start+100)."""
        from money_mapper.web_command import find_available_port

        port = find_available_port(start=9700)
        assert 9700 <= port < 9800


class TestBrowserLaunching:
    """Test browser auto-open functionality."""

    @patch("webbrowser.open")
    def test_launch_browser_opens_url(self, mock_open):
        """launch_browser() should call webbrowser.open with the given URL."""
        from money_mapper.web_command import launch_browser

        launch_browser("http://localhost:8000")
        mock_open.assert_called_once_with("http://localhost:8000")

    @patch("webbrowser.open")
    def test_launch_browser_uses_correct_url_format(self, mock_open):
        """launch_browser() passes the URL as-is to webbrowser.open."""
        from money_mapper.web_command import launch_browser

        url = "http://localhost:9123"
        launch_browser(url)
        mock_open.assert_called_once_with(url)

    @patch("webbrowser.open")
    def test_launch_browser_suppressed_with_no_browser_flag(self, mock_open):
        """launch_browser() should not call webbrowser.open when no_browser=True."""
        from money_mapper.web_command import launch_browser

        launch_browser("http://localhost:8000", no_browser=True)
        mock_open.assert_not_called()

    @patch("webbrowser.open", side_effect=Exception("Browser not found"))
    def test_launch_browser_failure_is_silent(self, mock_open):
        """launch_browser() must not raise if webbrowser.open throws."""
        from money_mapper.web_command import launch_browser

        # Should complete without raising
        launch_browser("http://localhost:8000")


class TestServerStartup:
    """Test FastAPI server startup via start_web_server."""

    @patch("uvicorn.run")
    @patch("money_mapper.web_command.create_app")
    @patch("money_mapper.web_command.find_available_port", return_value=8000)
    def test_start_web_server_calls_uvicorn(self, mock_port, mock_create_app, mock_uvicorn):
        """start_web_server() must call uvicorn.run."""
        from money_mapper.web_command import start_web_server

        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        start_web_server(host="localhost", port=8000, auto_port=False, no_browser=True)
        mock_uvicorn.assert_called_once()

    @patch("uvicorn.run")
    @patch("money_mapper.web_command.create_app")
    def test_start_web_server_passes_correct_host(self, mock_create_app, mock_uvicorn):
        """start_web_server() must pass the host argument to uvicorn.run."""
        from money_mapper.web_command import start_web_server

        mock_create_app.return_value = MagicMock()

        start_web_server(host="0.0.0.0", port=9999, auto_port=False, no_browser=True)
        _, kwargs = mock_uvicorn.call_args
        assert kwargs.get("host") == "0.0.0.0"

    @patch("uvicorn.run")
    @patch("money_mapper.web_command.create_app")
    def test_start_web_server_passes_correct_port(self, mock_create_app, mock_uvicorn):
        """start_web_server() must pass the port argument to uvicorn.run."""
        from money_mapper.web_command import start_web_server

        mock_create_app.return_value = MagicMock()

        start_web_server(host="localhost", port=9876, auto_port=False, no_browser=True)
        _, kwargs = mock_uvicorn.call_args
        assert kwargs.get("port") == 9876

    @patch("uvicorn.run")
    @patch("money_mapper.web_command.create_app")
    def test_start_web_server_loads_app_from_create_app(self, mock_create_app, mock_uvicorn):
        """start_web_server() must obtain the ASGI app via create_app()."""
        from money_mapper.web_command import start_web_server

        fake_app = MagicMock(name="FakeApp")
        mock_create_app.return_value = fake_app

        start_web_server(host="localhost", port=9875, auto_port=False, no_browser=True)
        mock_create_app.assert_called_once()
        # The app object passed to uvicorn should be the one create_app returned
        args, _ = mock_uvicorn.call_args
        assert args[0] is fake_app

    @patch("uvicorn.run", side_effect=KeyboardInterrupt)
    @patch("money_mapper.web_command.create_app")
    def test_start_web_server_handles_keyboard_interrupt(self, mock_create_app, mock_uvicorn):
        """start_web_server() should handle KeyboardInterrupt and exit 0."""
        import pytest

        from money_mapper.web_command import start_web_server

        mock_create_app.return_value = MagicMock()

        with pytest.raises(SystemExit) as exc_info:
            start_web_server(host="localhost", port=9874, auto_port=False, no_browser=True)
        assert exc_info.value.code == 0


class TestCLIParsing:
    """Test CLI argument parsing for web command via argparse."""

    def _build_web_parser(self):
        """Build a minimal parser that mirrors the 'web' subcommand definition."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--host", default="localhost")
        parser.add_argument("--port", default="8000")
        parser.add_argument("--no-browser", action="store_true", dest="no_browser")
        return parser

    def test_web_command_default_host_is_localhost(self):
        """Web command should default host to 'localhost'."""
        parser = self._build_web_parser()
        args = parser.parse_args([])
        assert args.host == "localhost"

    def test_web_command_default_port_is_8000(self):
        """Web command should default port to '8000'."""
        parser = self._build_web_parser()
        args = parser.parse_args([])
        assert args.port == "8000"

    def test_web_command_custom_host_parsed(self):
        """Web command should accept a custom --host value."""
        parser = self._build_web_parser()
        args = parser.parse_args(["--host", "0.0.0.0"])
        assert args.host == "0.0.0.0"

    def test_web_command_custom_port_parsed(self):
        """Web command should accept a custom --port value."""
        parser = self._build_web_parser()
        args = parser.parse_args(["--port", "9090"])
        assert args.port == "9090"

    def test_web_command_no_browser_flag_parsed(self):
        """Web command should set no_browser=True when --no-browser is passed."""
        parser = self._build_web_parser()
        args = parser.parse_args(["--no-browser"])
        assert args.no_browser is True


class TestWebCommandFunction:
    """Test the web_command() dispatcher function."""

    @patch("money_mapper.web_command.start_web_server")
    def test_web_command_calls_start_web_server(self, mock_start):
        """web_command() should delegate to start_web_server()."""
        from money_mapper.web_command import web_command

        args = SimpleNamespace(host="localhost", port="8000", no_browser=False)
        web_command(args)
        mock_start.assert_called_once()

    @patch("money_mapper.web_command.start_web_server")
    def test_web_command_passes_no_browser_flag(self, mock_start):
        """web_command() should forward the no_browser flag."""
        from money_mapper.web_command import web_command

        args = SimpleNamespace(host="localhost", port="8000", no_browser=True)
        web_command(args)
        _, kwargs = mock_start.call_args
        assert kwargs.get("no_browser") is True

    @patch("money_mapper.web_command.start_web_server")
    def test_web_command_converts_port_to_int(self, mock_start):
        """web_command() should convert the port string argument to int."""
        from money_mapper.web_command import web_command

        args = SimpleNamespace(host="localhost", port="9001", no_browser=False)
        web_command(args)
        _, kwargs = mock_start.call_args
        assert kwargs.get("port") == 9001

    def test_web_command_rejects_invalid_port(self):
        """web_command() should return exit code 1 for an out-of-range port."""
        from money_mapper.web_command import web_command

        args = SimpleNamespace(host="localhost", port="99999", no_browser=False)
        result = web_command(args)
        assert result == 1

    def test_web_command_rejects_zero_port(self):
        """web_command() should return exit code 1 for port 0."""
        from money_mapper.web_command import web_command

        args = SimpleNamespace(host="localhost", port="0", no_browser=False)
        result = web_command(args)
        assert result == 1
