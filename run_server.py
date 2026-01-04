#!/usr/bin/env python3
"""
NatLangChain API Server Launcher

Usage:
    python run_server.py

This script starts the NatLangChain API server. Make sure you have:
1. Installed dependencies: pip install -r requirements.txt
2. Configured .env file (optional, see .env.example)
"""

import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

try:
    # Import the main api module (api.py, not api/ package)
    # We use importlib to avoid confusion with the api/ package
    import importlib.util
    spec = importlib.util.spec_from_file_location("api_main", os.path.join(src_path, "api.py"))
    api_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api_module)
    run_server = api_module.run_server
except ImportError as e:
    print(f"\n❌ Import error: {e}")
    print("\nTroubleshooting:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Run from project root directory")
    print("  3. Check that src/api.py exists")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Failed to load API module: {e}")
    print("\nThis might be a dependency issue. Try:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

if __name__ == '__main__':
    run_server()
