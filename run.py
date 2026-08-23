#!/usr/bin/env python3
"""
Main entry point for Antigenic Video Editor.

Run this script to start the web server with the chat agent interface.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.server import create_app, run_server


def main():
    """Run the video editor web server."""
    print("Starting Antigenic Video Editor...")
    print("Access the chat interface at: http://localhost:5000")
    print("Workspace interface also available at: http://localhost:5000/workspace")
    
    run_server(host='0.0.0.0', port=5000, debug=True)


if __name__ == '__main__':
    main()
