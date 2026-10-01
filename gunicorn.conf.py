"""
Gunicorn configuration for NatLangChain.

    gunicorn -c gunicorn.conf.py wsgi:app

The ledger, pending queue, rate limiter and validator state live in process
memory, so the service must run as exactly one worker process. Concurrency
comes from threads. The on_starting hook refuses to boot with more workers so
a copy-pasted `--workers 4` cannot silently split the chain.
"""

import os

bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '5000')}"
workers = 1
threads = int(os.getenv("GUNICORN_THREADS", "4"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.getenv("SHUTDOWN_TIMEOUT", "30"))
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()


def on_starting(server):
    """Abort startup if more than one worker process is configured."""
    allow = os.getenv("NATLANGCHAIN_ALLOW_MULTIPLE_WORKERS", "false").lower() == "true"
    if server.cfg.workers != 1 and not allow:
        raise SystemExit(
            f"NatLangChain must run with exactly one gunicorn worker (got {server.cfg.workers}). "
            "Chain state is held in process memory; multiple workers would each serve a "
            "different ledger. Use --threads for concurrency, or set "
            "NATLANGCHAIN_ALLOW_MULTIPLE_WORKERS=true if you really know what you are doing."
        )
