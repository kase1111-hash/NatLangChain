#!/usr/bin/env python3
"""
NatLangChain API Server Launcher

Usage:
    python run_server.py

This script starts the NatLangChain API server. Make sure you have:
1. Installed dependencies: pip install -r requirements.txt
2. Configured .env file (optional, see .env.example)
"""

import atexit
import logging
import os
import signal
import sys
import time

# Add src to path for imports
src_path = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, src_path)

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Shutdown configuration
_shutdown_timeout = int(os.getenv("SHUTDOWN_TIMEOUT", "30"))


def _graceful_shutdown(signum, _frame):
    """Handle SIGTERM/SIGINT for graceful server shutdown."""
    from api import state

    signal_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
    logger.info(f"Received {signal_name} - initiating graceful shutdown...")
    print(f"\n[SHUTDOWN] Received {signal_name} - initiating graceful shutdown...")

    # Signal that we're shutting down
    state.set_shutting_down()

    # Wait for in-flight requests to complete
    waited = 0
    while waited < _shutdown_timeout:
        current = state.get_in_flight_count()
        if current == 0:
            logger.info("All in-flight requests completed")
            print("[SHUTDOWN] All in-flight requests completed")
            break

        logger.info(
            f"Waiting for {current} in-flight request(s)... ({waited}s/{_shutdown_timeout}s)"
        )
        print(
            f"[SHUTDOWN] Waiting for {current} in-flight request(s)... "
            f"({waited}s/{_shutdown_timeout}s)"
        )
        time.sleep(1)
        waited += 1

    if waited >= _shutdown_timeout:
        remaining = state.get_in_flight_count()
        logger.warning(f"Shutdown timeout reached with {remaining} request(s) still in flight")
        print(f"[SHUTDOWN] Timeout reached with {remaining} request(s) still in flight")

    # Flush pending data to storage
    try:
        logger.info("Saving blockchain state...")
        print("[SHUTDOWN] Saving blockchain state...")
        state.save_chain()
        logger.info("Blockchain state saved successfully")
        print("[SHUTDOWN] Blockchain state saved successfully")
    except Exception as e:
        logger.error(f"Failed to save blockchain state: {e}")
        print(f"[SHUTDOWN] WARNING: Failed to save blockchain state: {e}")

    logger.info("Graceful shutdown complete")
    print("[SHUTDOWN] Graceful shutdown complete")
    sys.exit(0)


def _cleanup_on_exit():
    """Cleanup handler called on process exit."""
    from api import state

    if not state.is_shutting_down():
        try:
            state.save_chain()
        except Exception:
            pass  # Best effort on exit


def run_server():
    """Run the Flask development server with graceful shutdown support."""
    from api import create_app, state
    from api.utils import managers

    app = create_app()

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # Register graceful shutdown handlers
    signal.signal(signal.SIGTERM, _graceful_shutdown)
    signal.signal(signal.SIGINT, _graceful_shutdown)
    atexit.register(_cleanup_on_exit)

    api_key_required = os.getenv("NATLANGCHAIN_REQUIRE_AUTH", "true").lower() == "true"
    rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    print(f"\n{'=' * 60}")
    print("NatLangChain API Server")
    print(f"{'=' * 60}")
    print(f"Listening on: http://{host}:{port}")
    print(f"Debug Mode: {'ENABLED (not for production!)' if debug else 'Disabled'}")
    print(f"Auth Required: {'Yes' if api_key_required else 'No'}")
    print(f"Rate Limit: {rate_limit_requests} req/{rate_limit_window}s")
    print(f"LLM Validation: {'Enabled' if managers.llm_validator else 'Disabled'}")
    print(f"Blockchain: {len(state.blockchain.chain)} blocks loaded")
    print(f"Graceful Shutdown: Enabled (timeout: {_shutdown_timeout}s)")
    print(f"{'=' * 60}\n")

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server()
