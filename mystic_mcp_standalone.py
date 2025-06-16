#!/usr/bin/env python3
"""
Standalone Gnosis Mystic MCP Server

This is a self-contained version that can be run without installing the package.
Place this file anywhere and point Claude Desktop to it.
"""

import os
import sys
import json
import logging
import requests
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import argparse

# MCP imports - these should be available in Claude's environment
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: mcp package not found. Please install it with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("gnosis_mystic_mcp")

# Initialize MCP server
mcp = FastMCP("gnosis-mystic")

# Configuration
MYSTIC_HOST = "localhost"
MYSTIC_PORT = 8899


def ensure_project_in_path(project_root: Path):
    """Add project root to Python path."""
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def check_server_running() -> bool:
    """Check if Mystic server is running."""
    try:
        response = requests.get(f"http://{MYSTIC_HOST}:{MYSTIC_PORT}/health", timeout=1)
        return response.status_code == 200
    except:
        return False


@mcp.tool()
async def discover_functions(module_filter: str = "", include_private: bool = False) -> Dict[str, Any]:
    """
    Discover Python functions in the current project.
    
    Args:
        module_filter: Filter functions by module name prefix (e.g., "utils.helpers")
        include_private: Include private functions (starting with _)
        
    Returns:
        List of discovered functions with their signatures and locations
    """
    project_root = Path.cwd()
    
    logger.info(f"Discovering functions in {project_root}")
    ensure_project_in_path(project_root)
    
    try:
        discovered = []
        
        # Find Python files
        for py_file in project_root.rglob("*.py"):
            # Skip common directories
            if any(part in py_file.parts for part in ['.venv', 'venv', '__pycache__', '.git']):
                continue
            
            try:
                # Convert to module path
                relative = py_file.relative_to(project_root)
                module_name = str(relative.with_suffix('')).replace(os.sep, '.')
                
                # Apply filter
                if module_filter and not module_name.startswith(module_filter):
                    continue
                
                # Parse the file directly instead of importing
                import ast
                import inspect
                
                with open(py_file, 'r', encoding='utf-8') as f:
                    try:
                        tree = ast.parse(f.read(), filename=str(py_file))
                    except:
                        continue
                
                # Find function definitions (both sync and async)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        func_name = node.name
                        
                        # Skip private functions unless requested
                        if func_name.startswith('_') and not include_private:
                            continue
                        
                        # Get docstring
                        docstring = ast.get_docstring(node) or "No documentation"
                        
                        # Build signature
                        args = []
                        for arg in node.args.args:
                            args.append(arg.arg)
                        signature = f"({', '.join(args)})"
                        
                        # Add async prefix if needed
                        if isinstance(node, ast.AsyncFunctionDef):
                            signature = f"async {signature}"
                        
                        discovered.append({
                            "name": func_name,
                            "module": module_name,
                            "full_name": f"{module_name}.{func_name}",
                            "signature": signature,
                            "docstring": docstring,
                            "file": str(py_file),
                            "line": node.lineno,
                            "is_async": isinstance(node, ast.AsyncFunctionDef)
                        })
            except Exception as e:
                logger.debug(f"Error processing {py_file}: {e}")
                continue
        
        return {
            "success": True,
            "count": len(discovered),
            "functions": discovered
        }
        
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def hijack_function(
    function_name: str,
    strategy: str = "analyze",
    duration: str = "1h",
    mock_value: Any = None,
    block_message: str = "Function blocked by Mystic"
) -> Dict[str, Any]:
    """
    Hijack a function with a specific strategy.
    
    Args:
        function_name: Full function name (e.g., "module.submodule.function")
        strategy: Hijacking strategy - "cache", "mock", "block", "analyze", "redirect"
        duration: Cache duration (for cache strategy) - "30m", "1h", "1d"
        mock_value: Return value for mock strategy
        block_message: Message for block strategy
        
    Returns:
        Hijacking status and details
    """
    if not check_server_running():
        return {
            "success": False,
            "error": "Mystic server not running. Please run 'mystic serve' in your project directory."
        }
    
    logger.info(f"Hijacking {function_name} with {strategy} strategy")
    
    try:
        payload = {
            "function": function_name,
            "strategy": strategy,
            "options": {}
        }
        
        # Strategy-specific options
        if strategy == "cache":
            payload["options"]["duration"] = duration
        elif strategy == "mock":
            payload["options"]["mock_data"] = mock_value
        elif strategy == "block":
            payload["options"]["message"] = block_message
        
        response = requests.post(
            f"http://{MYSTIC_HOST}:{MYSTIC_PORT}/api/functions/hijack",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "message": f"Successfully hijacked {function_name}",
                "details": result
            }
        else:
            return {
                "success": False,
                "error": f"Server returned {response.status_code}",
                "details": response.text
            }
            
    except Exception as e:
        logger.error(f"Hijacking failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def unhijack_function(function_name: str) -> Dict[str, Any]:
    """
    Remove hijacking from a function.
    
    Args:
        function_name: Full function name to unhijack
        
    Returns:
        Unhijacking status and final metrics
    """
    if not check_server_running():
        return {
            "success": False,
            "error": "Mystic server not running. Please run 'mystic serve' in your project directory."
        }
    
    logger.info(f"Unhijacking {function_name}")
    
    try:
        response = requests.post(
            f"http://{MYSTIC_HOST}:{MYSTIC_PORT}/api/functions/unhijack",
            params={"function_name": function_name},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "message": f"Successfully unhijacked {function_name}",
                "metrics": result.get("metrics", {})
            }
        else:
            return {
                "success": False,
                "error": f"Server returned {response.status_code}",
                "details": response.text
            }
            
    except Exception as e:
        logger.error(f"Unhijacking failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def inspect_function(
    function_name: str,
    include_source: bool = True,
    include_dependencies: bool = True
) -> Dict[str, Any]:
    """
    Inspect a function to get detailed information.
    
    Args:
        function_name: Full function name to inspect
        include_source: Include source code in response
        include_dependencies: Include dependency analysis
        
    Returns:
        Detailed function information including signature, docs, and analysis
    """
    if not check_server_running():
        # Try local inspection
        try:
            parts = function_name.split('.')
            module_name = '.'.join(parts[:-1])
            func_name = parts[-1]
            
            module = __import__(module_name, fromlist=[func_name])
            func = getattr(module, func_name)
            
            import inspect
            return {
                "success": True,
                "function": function_name,
                "inspection": {
                    "signature": str(inspect.signature(func)),
                    "docstring": inspect.getdoc(func) or "No documentation",
                    "file": inspect.getfile(func),
                    "line": inspect.getsourcelines(func)[1],
                    "source": inspect.getsource(func) if include_source else None
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Local inspection failed: {str(e)}. Server not running."
            }
    
    logger.info(f"Inspecting {function_name}")
    
    try:
        payload = {
            "function": function_name,
            "include_source": include_source,
            "include_dependencies": include_dependencies
        }
        
        response = requests.post(
            f"http://{MYSTIC_HOST}:{MYSTIC_PORT}/api/functions/inspect",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "function": function_name,
                "inspection": result["inspection"]
            }
        else:
            return {
                "success": False,
                "error": f"Server returned {response.status_code}",
                "details": response.text
            }
            
    except Exception as e:
        logger.error(f"Inspection failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def list_hijacked_functions() -> Dict[str, Any]:
    """
    List all currently hijacked functions.
    
    Returns:
        List of hijacked functions with their strategies and metrics
    """
    if not check_server_running():
        return {
            "success": False,
            "error": "Mystic server not running. Please run 'mystic serve' in your project directory."
        }
    
    logger.info("Listing hijacked functions")
    
    try:
        response = requests.get(
            f"http://{MYSTIC_HOST}:{MYSTIC_PORT}/api/hijacked",
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "success": False,
                "error": f"Server returned {response.status_code}",
                "details": response.text
            }
            
    except Exception as e:
        logger.error(f"Failed to list hijacked functions: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def mystic_status() -> Dict[str, Any]:
    """
    Check the status of Gnosis Mystic in the current project.
    
    Returns:
        Project status, server status, and configuration
    """
    project_root = Path.cwd()
    mystic_dir = project_root / ".mystic"
    
    status = {
        "project_root": str(project_root),
        "initialized": mystic_dir.exists(),
        "server_running": check_server_running()
    }
    
    if mystic_dir.exists():
        config_file = mystic_dir / "config.json"
        if config_file.exists():
            with open(config_file) as f:
                status["config"] = json.load(f)
    
    if status["server_running"]:
        status["server_url"] = f"http://{MYSTIC_HOST}:{MYSTIC_PORT}"
        status["message"] = "Mystic server is running"
    else:
        status["message"] = "Mystic server not running. Run 'mystic serve' to start it."
    
    return status


def main():
    """Main entry point for the standalone MCP server."""
    parser = argparse.ArgumentParser(description="Gnosis Mystic Standalone MCP Server")
    parser.add_argument("--project-root", type=str, help="Project root directory")
    parser.add_argument("--host", default="localhost", help="Mystic server host")
    parser.add_argument("--port", type=int, default=8899, help="Mystic server port")
    
    args = parser.parse_args()
    
    # Set working directory if specified
    if args.project_root:
        os.chdir(args.project_root)
        logger.info(f"Changed to project root: {args.project_root}")
    
    # Update server location if specified
    global MYSTIC_HOST, MYSTIC_PORT
    MYSTIC_HOST = args.host
    MYSTIC_PORT = args.port
    
    logger.info(f"Gnosis Mystic Standalone MCP Server starting...")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Mystic server expected at: {MYSTIC_HOST}:{MYSTIC_PORT}")
    
    # Run MCP server
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()