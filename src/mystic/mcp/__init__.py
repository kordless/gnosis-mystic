"""
Gnosis Mystic MCP (Model Context Protocol) Integration

This module provides the MCP server implementation for exposing
Mystic's functionality to AI assistants.
"""

from .server import app, run_server

__all__ = ['app', 'run_server']