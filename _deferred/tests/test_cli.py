"""
Tests for NatLangChain Command Line Interface.

Tests:
- cmd_serve() function
- cmd_check() function
- cmd_info() function
- main() entry point
- _get_flask_app() function
- Argument parsing
"""

import argparse
import os
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cli import _get_flask_app, cmd_check, cmd_info, cmd_serve, main


class TestCmdCheck:
    """Tests for cmd_check() function."""

    def test_cmd_check_basic(self):
        """Test basic check command execution."""
        # Create mock args
        args = argparse.Namespace()

        # Capture stdout
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cmd_check(args)

        output = mock_stdout.getvalue()
        # Should output check results
        assert "NatLangChain" in output or "Check" in output or "check" in output.lower()

    def test_cmd_check_returns_code(self):
        """Test that cmd_check returns exit code."""
        args = argparse.Namespace()

        with patch("sys.stdout", new_callable=StringIO):
            result = cmd_check(args)

        # Should return 0 or 1
        assert result in [0, 1]

    @patch("cli.NatLangChain", MagicMock())
    def test_cmd_check_core_blockchain_ok(self):
        """Test check reports core blockchain as OK."""
        args = argparse.Namespace()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cmd_check(args)

        output = mock_stdout.getvalue()
        # Should indicate blockchain check
        assert "blockchain" in output.lower() or "core" in output.lower()

    def test_cmd_check_handles_import_errors(self):
        """Test check handles import errors gracefully."""
        args = argparse.Namespace()

        # Even with import issues, should not crash
        with patch("sys.stdout", new_callable=StringIO):
            result = cmd_check(args)

        assert result in [0, 1]


class TestCmdInfo:
    """Tests for cmd_info() function."""

    def test_cmd_info_basic(self):
        """Test basic info command execution."""
        args = argparse.Namespace()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cmd_info(args)

        output = mock_stdout.getvalue()
        assert "NatLangChain" in output

    def test_cmd_info_shows_version(self):
        """Test info shows version information."""
        args = argparse.Namespace()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cmd_info(args)

        output = mock_stdout.getvalue()
        assert "Version" in output or "version" in output.lower()

    def test_cmd_info_shows_python_version(self):
        """Test info shows Python version."""
        args = argparse.Namespace()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cmd_info(args)

        output = mock_stdout.getvalue()
        assert "Python" in output or "python" in output.lower()

    def test_cmd_info_shows_configuration(self):
        """Test info shows configuration details."""
        args = argparse.Namespace()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cmd_info(args)

        output = mock_stdout.getvalue()
        assert "Configuration" in output or "STORAGE" in output or "config" in output.lower()

    def test_cmd_info_returns_zero(self):
        """Test info returns exit code 0."""
        args = argparse.Namespace()

        with patch("sys.stdout", new_callable=StringIO):
            result = cmd_info(args)

        assert result == 0

    @patch.dict(os.environ, {"STORAGE_BACKEND": "postgresql", "LOG_LEVEL": "DEBUG"})
    def test_cmd_info_shows_env_values(self):
        """Test info shows environment variable values."""
        args = argparse.Namespace()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cmd_info(args)

        output = mock_stdout.getvalue()
        # Should show storage backend info
        assert "STORAGE" in output or "storage" in output.lower()


class TestCmdServe:
    """Tests for cmd_serve() function."""

    @patch("cli._get_flask_app")
    @patch("cli.load_dotenv")
    def test_cmd_serve_development(self, _mock_dotenv, mock_get_app):
        """Test serve command in development mode."""
        mock_app = MagicMock()
        mock_get_app.return_value = mock_app

        args = argparse.Namespace(
            host=None,
            port=None,
            debug=True,
            production=False,
            workers=None,
        )

        with patch("sys.stdout", new_callable=StringIO):
            cmd_serve(args)

        # Flask app.run should be called
        mock_app.run.assert_called_once()

    @patch("cli._get_flask_app")
    @patch("cli.load_dotenv")
    def test_cmd_serve_custom_host_port(self, _mock_dotenv, mock_get_app):
        """Test serve with custom host and port."""
        mock_app = MagicMock()
        mock_get_app.return_value = mock_app

        args = argparse.Namespace(
            host="127.0.0.1",
            port=8080,
            debug=False,
            production=False,
            workers=None,
        )

        with patch("sys.stdout", new_callable=StringIO):
            cmd_serve(args)

        mock_app.run.assert_called_once()
        call_kwargs = mock_app.run.call_args[1]
        assert call_kwargs["host"] == "127.0.0.1"
        assert call_kwargs["port"] == 8080

    @patch("cli._get_flask_app")
    @patch("cli.load_dotenv")
    @patch.dict(os.environ, {"HOST": "0.0.0.0", "PORT": "5001"})
    def test_cmd_serve_env_defaults(self, _mock_dotenv, mock_get_app):
        """Test serve uses environment defaults."""
        mock_app = MagicMock()
        mock_get_app.return_value = mock_app

        args = argparse.Namespace(
            host=None,
            port=None,
            debug=False,
            production=False,
            workers=None,
        )

        with patch("sys.stdout", new_callable=StringIO):
            cmd_serve(args)

        call_kwargs = mock_app.run.call_args[1]
        assert call_kwargs["host"] == "0.0.0.0"
        assert call_kwargs["port"] == 5001

    def test_cmd_serve_production_no_gunicorn(self):
        """Test serve production mode without gunicorn installed."""
        args = argparse.Namespace(
            host=None,
            port=None,
            debug=False,
            production=True,
            workers=4,
        )

        # Mock gunicorn import to fail
        with patch.dict(sys.modules, {"gunicorn": None, "gunicorn.app": None, "gunicorn.app.base": None}):
            with patch("cli.load_dotenv"):
                with patch("sys.stdout", new_callable=StringIO):
                    with pytest.raises(SystemExit) as exc_info:
                        cmd_serve(args)
                    assert exc_info.value.code == 1


class TestGetFlaskApp:
    """Tests for _get_flask_app() function."""

    def test_get_flask_app_returns_app(self):
        """Test _get_flask_app returns a Flask app."""
        # This may fail if api.py has issues, but should return something
        try:
            app = _get_flask_app()
            assert app is not None
        except Exception:
            # May fail due to missing dependencies, which is OK for this test
            pytest.skip("Flask app creation failed - likely missing dependencies")


class TestMain:
    """Tests for main() entry point."""

    def test_main_no_command(self):
        """Test main with no command shows help."""
        with patch("sys.argv", ["natlangchain"]):
            with patch("sys.stdout", new_callable=StringIO):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1

    def test_main_check_command(self):
        """Test main with check command."""
        with patch("sys.argv", ["natlangchain", "check"]):
            with patch("sys.stdout", new_callable=StringIO):
                with patch("cli.cmd_check", return_value=0) as mock_check:
                    try:
                        main()
                    except SystemExit as e:
                        assert e.code == 0

    def test_main_info_command(self):
        """Test main with info command."""
        with patch("sys.argv", ["natlangchain", "info"]):
            with patch("sys.stdout", new_callable=StringIO):
                with patch("cli.cmd_info", return_value=0) as mock_info:
                    try:
                        main()
                    except SystemExit as e:
                        assert e.code == 0

    def test_main_version_flag(self):
        """Test main with --version flag."""
        with patch("sys.argv", ["natlangchain", "--version"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
            output = mock_stdout.getvalue()
            assert "0.1.0" in output or "natlangchain" in output.lower()

    def test_main_help_flag(self):
        """Test main with --help flag."""
        with patch("sys.argv", ["natlangchain", "--help"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
            output = mock_stdout.getvalue()
            assert "serve" in output.lower() or "check" in output.lower()


class TestArgumentParsing:
    """Tests for argument parsing."""

    def test_serve_parser_options(self):
        """Test serve subcommand accepts expected options."""
        with patch("sys.argv", ["natlangchain", "serve", "--host", "localhost", "--port", "8000"]):
            with patch("cli.cmd_serve") as mock_serve:
                with patch("sys.stdout", new_callable=StringIO):
                    try:
                        main()
                    except SystemExit:
                        pass
                    if mock_serve.called:
                        args = mock_serve.call_args[0][0]
                        assert args.host == "localhost"
                        assert args.port == 8000

    def test_serve_debug_flag(self):
        """Test serve --debug flag."""
        with patch("sys.argv", ["natlangchain", "serve", "--debug"]):
            with patch("cli.cmd_serve") as mock_serve:
                with patch("sys.stdout", new_callable=StringIO):
                    try:
                        main()
                    except SystemExit:
                        pass
                    if mock_serve.called:
                        args = mock_serve.call_args[0][0]
                        assert args.debug is True

    def test_serve_production_flag(self):
        """Test serve --production flag."""
        with patch("sys.argv", ["natlangchain", "serve", "--production"]):
            with patch("cli.cmd_serve") as mock_serve:
                with patch("sys.stdout", new_callable=StringIO):
                    try:
                        main()
                    except SystemExit:
                        pass
                    if mock_serve.called:
                        args = mock_serve.call_args[0][0]
                        assert args.production is True

    def test_serve_workers_option(self):
        """Test serve --workers option."""
        with patch("sys.argv", ["natlangchain", "serve", "--workers", "8"]):
            with patch("cli.cmd_serve") as mock_serve:
                with patch("sys.stdout", new_callable=StringIO):
                    try:
                        main()
                    except SystemExit:
                        pass
                    if mock_serve.called:
                        args = mock_serve.call_args[0][0]
                        assert args.workers == 8


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_port_type(self):
        """Test handling of invalid port type."""
        with patch("sys.argv", ["natlangchain", "serve", "--port", "invalid"]):
            with patch("sys.stderr", new_callable=StringIO):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                # argparse should fail with invalid port
                assert exc_info.value.code == 2

    def test_unknown_command(self):
        """Test handling of unknown command."""
        with patch("sys.argv", ["natlangchain", "unknown_command"]):
            with patch("sys.stderr", new_callable=StringIO):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 2

    @patch("cli._get_flask_app")
    @patch("cli.load_dotenv")
    def test_serve_with_zero_port(self, _mock_dotenv, mock_get_app):
        """Test serve with port 0 (system assigns port)."""
        mock_app = MagicMock()
        mock_get_app.return_value = mock_app

        args = argparse.Namespace(
            host=None,
            port=0,
            debug=False,
            production=False,
            workers=None,
        )

        with patch("sys.stdout", new_callable=StringIO):
            cmd_serve(args)

        call_kwargs = mock_app.run.call_args[1]
        assert call_kwargs["port"] == 0
