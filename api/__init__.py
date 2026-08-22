"""
API module for Antigenic Video Editor.

RESTful API endpoints for video editing operations.
"""

from .server import create_app, run_server

__version__ = "1.0.0"
__all__ = ["create_app", "run_server"]
