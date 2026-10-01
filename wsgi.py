"""
WSGI entry point for production servers.

Example:
    gunicorn --workers 1 --threads 4 --bind 0.0.0.0:5000 wsgi:app

Run exactly one worker process: the ledger, pending queue and rate-limit state
are held in process memory, so multiple workers would each serve a different
chain. Use threads for concurrency. For local development use
``python run_server.py`` instead.
"""

import os
import sys

# Allow `import api` without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from dotenv import load_dotenv

load_dotenv()

from api import create_app  # noqa: E402

app = create_app()
