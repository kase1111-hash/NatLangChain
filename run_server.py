#!/usr/bin/env python3
"""
NatLangChain API Server Launcher
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from api import run_server

if __name__ == '__main__':
    run_server()
