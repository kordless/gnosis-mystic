"""
MCP Server module entry point

This allows running the server with: python -m mystic.mcp.server
"""

from .server import run_server
import argparse
import os
import sys
from pathlib import Path


def main():
    """Main entry point for running the MCP server directly."""
    parser = argparse.ArgumentParser(description="Gnosis Mystic MCP Server")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8899, help="Server port")
    parser.add_argument("--project-root", type=Path, help="Project root directory")
    
    args = parser.parse_args()
    
    # Set project root
    if args.project_root:
        os.environ['MYSTIC_PROJECT_ROOT'] = str(args.project_root)
        if str(args.project_root) not in sys.path:
            sys.path.insert(0, str(args.project_root))
    else:
        # Use current directory
        os.environ['MYSTIC_PROJECT_ROOT'] = str(Path.cwd())
        if str(Path.cwd()) not in sys.path:
            sys.path.insert(0, str(Path.cwd()))
    
    print(f"Starting Gnosis Mystic MCP Server on http://{args.host}:{args.port}")
    print(f"Project root: {os.environ.get('MYSTIC_PROJECT_ROOT')}")
    print("Press Ctrl+C to stop")
    
    try:
        run_server(host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\nServer stopped")


if __name__ == "__main__":
    main()