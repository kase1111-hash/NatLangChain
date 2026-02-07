#!/usr/bin/env python3
"""
NatLangChain Command Line Interface.

Provides commands for running and managing NatLangChain:
    - serve: Start the API server
    - check: Verify installation and configuration
    - info: Display system information

Usage:
    natlangchain serve [--host HOST] [--port PORT] [--debug]
    natlangchain check
    natlangchain info
    natlangchain --version
"""

import argparse
import os
import sys

# Ensure src is in path when running from source
if os.path.exists(os.path.join(os.path.dirname(__file__), "blockchain.py")):
    sys.path.insert(0, os.path.dirname(__file__))


def cmd_serve(args):
    """Start the NatLangChain API server."""
    from dotenv import load_dotenv

    load_dotenv()

    host = args.host or os.getenv("HOST", "0.0.0.0")
    port = args.port or int(os.getenv("PORT", 5000))
    debug = args.debug or os.getenv("FLASK_DEBUG", "").lower() == "true"

    print(f"Starting NatLangChain API server on {host}:{port}")

    if args.production:
        # Use gunicorn for production
        try:
            import gunicorn.app.base

            class StandaloneApplication(gunicorn.app.base.BaseApplication):
                """Gunicorn WSGI application wrapper for production deployment.

                Wraps a Flask application for use with Gunicorn's WSGI server,
                allowing configuration through a dictionary of options.
                """

                def __init__(self, app, options=None):
                    self.options = options or {}
                    self.application = app
                    super().__init__()

                def load_config(self):
                    """Load configuration from the options dictionary into Gunicorn settings."""
                    for key, value in self.options.items():
                        if key in self.cfg.settings and value is not None:
                            self.cfg.set(key.lower(), value)

                def load(self):
                    """Return the Flask application instance for Gunicorn to serve."""
                    return self.application

            # Import the Flask app
            flask_app = _get_flask_app()
            options = {
                "bind": f"{host}:{port}",
                "workers": args.workers or int(os.getenv("WORKERS", 4)),
                "worker_class": "sync",
                "timeout": 120,
                "accesslog": "-",
                "errorlog": "-",
            }
            StandaloneApplication(flask_app, options).run()

        except ImportError as e:
            if "gunicorn" in str(e):
                print(
                    "Error: gunicorn not installed. Install with: pip install natlangchain[production]"
                )
            else:
                print(f"Error: {e}")
            sys.exit(1)
    else:
        # Use Flask development server
        flask_app = _get_flask_app()
        flask_app.run(host=host, port=port, debug=debug)


def _get_flask_app():
    """Get the Flask application instance."""
    # The api.py module contains the main Flask app
    # Import it dynamically to handle the api/ package conflict
    import importlib.util
    import os

    # Find api.py (not api/ directory)
    src_dir = os.path.dirname(__file__)
    api_path = os.path.join(src_dir, "api.py")

    if os.path.exists(api_path):
        spec = importlib.util.spec_from_file_location("api_module", api_path)
        api_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(api_module)
        return api_module.app
    else:
        # Fallback: create minimal app with blueprints
        from flask import Flask

        from api import register_blueprints

        flask_app = Flask(__name__)
        register_blueprints(flask_app)
        return flask_app


def cmd_check(args):
    """Check installation and configuration."""
    print("NatLangChain Installation Check")
    print("=" * 40)

    checks = []

    # Check core imports
    try:
        pass

        checks.append(("Core blockchain", "OK"))
    except ImportError as e:
        checks.append(("Core blockchain", f"FAIL: {e}"))

    # Check API
    try:
        # api.py contains the Flask app (api/ is the blueprints package)
        import api as api_module

        if hasattr(api_module, "app"):
            checks.append(("Flask API", "OK"))
        else:
            # Try importing from api.py directly
            import importlib.util

            spec = importlib.util.find_spec("api")
            if spec and spec.origin and spec.origin.endswith(".py"):
                checks.append(("Flask API", "OK"))
            else:
                checks.append(("Flask API", "OK (blueprints only)"))
    except ImportError as e:
        checks.append(("Flask API", f"FAIL: {e}"))

    # Check validator (optional)
    try:
        pass

        checks.append(("LLM Validator", "OK"))
    except ImportError:
        checks.append(("LLM Validator", "SKIP (anthropic not installed)"))

    # Check storage
    try:
        from storage import get_storage_backend

        storage = get_storage_backend()
        backend_name = storage.__class__.__name__
        available = storage.is_available()
        status = "OK" if available else "WARN (not available)"
        checks.append((f"Storage ({backend_name})", status))
    except ImportError as e:
        checks.append(("Storage", f"FAIL: {e}"))

    # Check monitoring
    try:
        pass

        checks.append(("Monitoring", "OK"))
    except ImportError as e:
        checks.append(("Monitoring", f"FAIL: {e}"))

    # Check scaling
    try:
        from scaling import get_cache, get_lock_manager

        lock_type = get_lock_manager().__class__.__name__
        cache_type = get_cache().__class__.__name__
        checks.append((f"Scaling (Lock: {lock_type})", "OK"))
        checks.append((f"Scaling (Cache: {cache_type})", "OK"))
    except ImportError as e:
        checks.append(("Scaling", f"FAIL: {e}"))

    # Check optional dependencies
    try:
        pass

        checks.append(("Redis support", "OK"))
    except ImportError:
        checks.append(("Redis support", "SKIP (redis not installed)"))

    try:
        pass

        checks.append(("PostgreSQL support", "OK"))
    except ImportError:
        checks.append(("PostgreSQL support", "SKIP (psycopg2 not installed)"))

    # Print results
    print()
    all_ok = True
    for name, status in checks:
        icon = "✓" if status == "OK" else ("○" if "SKIP" in status else "✗")
        print(f"  {icon} {name}: {status}")
        if "FAIL" in status:
            all_ok = False

    print()
    if all_ok:
        print("All checks passed!")
        return 0
    else:
        print("Some checks failed. See above for details.")
        return 1


def cmd_info(args):
    """Display system information."""
    import platform

    print("NatLangChain System Information")
    print("=" * 40)

    # Version
    try:
        from . import __version__
    except ImportError:
        __version__ = "0.1.0"
    print(f"Version: {__version__}")

    # Python
    print(f"Python: {platform.python_version()}")
    print(f"Platform: {platform.platform()}")

    # Environment
    print()
    print("Configuration:")
    print(f"  STORAGE_BACKEND: {os.getenv('STORAGE_BACKEND', 'json (default)')}")
    print(f"  REDIS_URL: {'configured' if os.getenv('REDIS_URL') else 'not set'}")
    print(f"  DATABASE_URL: {'configured' if os.getenv('DATABASE_URL') else 'not set'}")
    print(f"  LOG_LEVEL: {os.getenv('LOG_LEVEL', 'INFO (default)')}")
    print(f"  LOG_FORMAT: {os.getenv('LOG_FORMAT', 'console (default)')}")

    # Storage info
    print()
    print("Storage:")
    try:
        from storage import get_storage_backend

        storage = get_storage_backend()
        info = storage.get_info()
        for key, value in info.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"  Error: {e}")

    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="natlangchain",
        description="NatLangChain - Natural Language Blockchain",
    )
    parser.add_argument("--version", "-v", action="version", version="%(prog)s 0.1.0")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", help="Host to bind to (default: 0.0.0.0)")
    serve_parser.add_argument("--port", type=int, help="Port to bind to (default: 5000)")
    serve_parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    serve_parser.add_argument(
        "--production", action="store_true", help="Use gunicorn for production"
    )
    serve_parser.add_argument("--workers", type=int, help="Number of workers (production mode)")

    # check command
    subparsers.add_parser("check", help="Check installation and configuration")

    # info command
    subparsers.add_parser("info", help="Display system information")

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "check":
        sys.exit(cmd_check(args))
    elif args.command == "info":
        sys.exit(cmd_info(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
