#!/usr/bin/env python
"""
Start the Gnosis Mystic MCP Server

Usage:
    python start_server.py [--host HOST] [--port PORT]
"""

import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mystic.mcp.server import run_server


def main():
    parser = argparse.ArgumentParser(description="Start Gnosis Mystic MCP Server")
    parser.add_argument("--host", default="localhost", help="Server host (default: localhost)")
    parser.add_argument("--port", type=int, default=8899, help="Server port (default: 8899)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Start server
    print(f"Starting Gnosis Mystic MCP Server on http://{args.host}:{args.port}")
    print(f"Health check: http://{args.host}:{args.port}/health")
    print(f"API docs: http://{args.host}:{args.port}/docs")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        run_server(host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\nServer stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()