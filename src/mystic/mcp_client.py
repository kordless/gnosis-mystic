"""
Gnosis Mystic MCP Client for Claude Desktop

This client exposes Mystic functionality as MCP tools that Claude Desktop can use.
It automatically connects to a local Mystic server or starts one if needed.
"""

import sys
import os
import json
import logging
import subprocess
import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
import argparse

# MCP imports
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

# Global state
PROJECT_ROOT = None
MYSTIC_HOST = "localhost"
MYSTIC_PORT = 8899
SERVER_PROCESS = None


def ensure_server_running():
    """Ensure the Mystic server is running, start it if not."""
    global SERVER_PROCESS
    
    # Check if server is already running
    try:
        response = requests.get(f"http://{MYSTIC_HOST}:{MYSTIC_PORT}/health", timeout=1)
        if response.status_code == 200:
            logger.info("Mystic server already running")
            return True
    except:
        pass
    
    # Start the server
    logger.info("Starting Mystic server...")
    try:
        # Add project root to PYTHONPATH
        env = os.environ.copy()
        if PROJECT_ROOT:
            env['PYTHONPATH'] = str(PROJECT_ROOT)
            env['MYSTIC_PROJECT_ROOT'] = str(PROJECT_ROOT)
        
        # Start server as subprocess
        SERVER_PROCESS = subprocess.Popen(
            [sys.executable, "-m", "mystic.mcp.server"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        for _ in range(30):  # 30 second timeout
            try:
                response = requests.get(f"http://{MYSTIC_HOST}:{MYSTIC_PORT}/health", timeout=1)
                if response.status_code == 200:
                    logger.info("Mystic server started successfully")
                    return True
            except:
                time.sleep(1)
        
        logger.error("Failed to start Mystic server")
        return False
        
    except Exception as e:
        logger.error(f"Error starting server: {e}")
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
    if not PROJECT_ROOT:
        return {
            "success": False,
            "error": "Project root not set. Please run from a project directory."
        }
    
    logger.info(f"Discovering functions in {PROJECT_ROOT}")
    
    try:
        # Add project root to path
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        
        discovered = []
        
        # Find Python files
        for py_file in Path(PROJECT_ROOT).rglob("*.py"):
            # Skip common directories
            if any(part in py_file.parts for part in ['.venv', 'venv', '__pycache__', '.git']):
                continue
            
            try:
                # Convert to module path
                relative = py_file.relative_to(PROJECT_ROOT)
                module_name = str(relative.with_suffix('')).replace(os.sep, '.')
                
                # Apply filter
                if module_filter and not module_name.startswith(module_filter):
                    continue
                
                # Import module
                module = __import__(module_name, fromlist=[''])
                
                # Find functions
                import inspect
                for name, obj in inspect.getmembers(module, inspect.isfunction):
                    # Skip private functions unless requested
                    if name.startswith('_') and not include_private:
                        continue
                    
                    # Only functions defined in this module
                    if obj.__module__ == module_name:
                        discovered.append({
                            "name": name,
                            "module": module_name,
                            "full_name": f"{module_name}.{name}",
                            "signature": str(inspect.signature(obj)),
                            "docstring": inspect.getdoc(obj) or "No documentation",
                            "file": str(py_file),
                            "line": inspect.getsourcelines(obj)[1]
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
    ensure_server_running()
    
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
    ensure_server_running()
    
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
    ensure_server_running()
    
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
async def get_function_metrics(function_name: str = None) -> Dict[str, Any]:
    """
    Get performance metrics for functions.
    
    Args:
        function_name: Specific function name, or None for all functions
        
    Returns:
        Performance metrics including call count, execution times, and errors
    """
    ensure_server_running()
    
    logger.info(f"Getting metrics for {function_name or 'all functions'}")
    
    try:
        if function_name:
            url = f"http://{MYSTIC_HOST}:{MYSTIC_PORT}/api/metrics/{function_name}"
        else:
            url = f"http://{MYSTIC_HOST}:{MYSTIC_PORT}/api/metrics"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "success": False,
                "error": f"Server returned {response.status_code}",
                "details": response.text
            }
            
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def get_state_snapshots(
    function_name: str = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get state snapshots for time-travel debugging.
    
    Args:
        function_name: Filter snapshots by function name
        limit: Maximum number of snapshots to return
        
    Returns:
        List of state snapshots with timeline information
    """
    ensure_server_running()
    
    logger.info(f"Getting state snapshots")
    
    try:
        payload = {
            "function_name": function_name,
            "limit": limit
        }
        
        response = requests.post(
            f"http://{MYSTIC_HOST}:{MYSTIC_PORT}/api/state/snapshots",
            json=payload,
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
        logger.error(f"Failed to get snapshots: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def get_function_logs(
    function_name: str = None,
    correlation_id: str = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get function execution logs.
    
    Args:
        function_name: Filter logs by function name
        correlation_id: Filter logs by correlation ID
        limit: Maximum number of logs to return
        
    Returns:
        Function execution logs with timing and arguments
    """
    ensure_server_running()
    
    logger.info(f"Getting function logs")
    
    try:
        payload = {
            "function_name": function_name,
            "correlation_id": correlation_id,
            "limit": limit
        }
        
        response = requests.post(
            f"http://{MYSTIC_HOST}:{MYSTIC_PORT}/api/logs",
            json=payload,
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
        logger.error(f"Failed to get logs: {e}")
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
    ensure_server_running()
    
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
async def create_performance_dashboard(
    functions: List[str] = None,
    timeframe: str = "1h"
) -> Dict[str, Any]:
    """
    Create a performance dashboard for specified functions.
    
    Args:
        functions: List of function names to include (None for all)
        timeframe: Time range for metrics - "15m", "1h", "24h", "7d"
        
    Returns:
        Dashboard data ready for visualization
    """
    ensure_server_running()
    
    logger.info("Creating performance dashboard")
    
    try:
        # Get metrics
        metrics_response = await get_function_metrics()
        if not metrics_response.get("success", True):
            return metrics_response
        
        # Filter functions if specified
        all_functions = metrics_response.get("functions", [])
        if functions:
            filtered = [f for f in all_functions if f["name"] in functions]
        else:
            filtered = all_functions
        
        # Sort by various criteria
        by_calls = sorted(filtered, key=lambda x: x["call_count"], reverse=True)[:10]
        by_time = sorted(filtered, key=lambda x: x["total_time"], reverse=True)[:10]
        by_errors = sorted([f for f in filtered if f["exceptions"] > 0], 
                          key=lambda x: x["exceptions"], reverse=True)[:10]
        
        dashboard = {
            "success": True,
            "timeframe": timeframe,
            "summary": metrics_response.get("summary", {}),
            "top_by_calls": by_calls,
            "top_by_time": by_time,
            "top_by_errors": by_errors,
            "overhead": metrics_response.get("overhead", {}),
            "visualization_hint": "Use this data to create charts showing performance metrics"
        }
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Failed to create dashboard: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def main():
    """Main entry point for the MCP client."""
    global PROJECT_ROOT
    
    parser = argparse.ArgumentParser(description="Gnosis Mystic MCP Client")
    parser.add_argument("--project-root", type=str, help="Project root directory")
    parser.add_argument("--host", default="localhost", help="Mystic server host")
    parser.add_argument("--port", type=int, default=8899, help="Mystic server port")
    
    args = parser.parse_args()
    
    # Set project root
    if args.project_root:
        PROJECT_ROOT = Path(args.project_root)
    else:
        PROJECT_ROOT = Path.cwd()
    
    # Set server location
    global MYSTIC_HOST, MYSTIC_PORT
    MYSTIC_HOST = args.host
    MYSTIC_PORT = args.port
    
    logger.info(f"Gnosis Mystic MCP Client starting...")
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info(f"Server: {MYSTIC_HOST}:{MYSTIC_PORT}")
    
    # Run MCP server
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()