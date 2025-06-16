"""
Gnosis Mystic MCP Server

HTTP server that exposes core Mystic functionality via REST API
for integration with AI assistants through the Model Context Protocol.
"""

import asyncio
import json
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mystic.core.function_hijacker import (
    CallHijacker, CacheStrategy, MockStrategy, BlockStrategy,
    RedirectStrategy, AnalysisStrategy, HijackRegistry
)
from mystic.core.function_inspector import FunctionInspector
from mystic.core.function_logger import FunctionLogger, LogFormat
from mystic.core.performance_tracker import PerformanceTracker, get_global_tracker
from mystic.core.state_manager import StateManager, get_global_state_manager
from mystic.config import Config

# Configure logging
logger = logging.getLogger("mystic.mcp.server")

# Initialize core components
inspector = FunctionInspector()
global_logger = FunctionLogger(
    name="mystic.global",
    format=LogFormat.JSON_RPC,
    filter_sensitive=True,
    include_performance=True
)
perf_tracker = get_global_tracker()
state_manager = get_global_state_manager()
hijack_registry = HijackRegistry()

# Create FastAPI app
app = FastAPI(
    title="Gnosis Mystic MCP Server",
    description="Advanced Python function debugging and introspection via MCP",
    version="0.1.0"
)

# Add CORS middleware for browser-based clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response validation
class HijackRequest(BaseModel):
    function: str = Field(..., description="Full function name (module.function)")
    strategy: str = Field("cache", description="Hijacking strategy")
    options: Dict[str, Any] = Field(default_factory=dict, description="Strategy options")


class InspectRequest(BaseModel):
    function: str = Field(..., description="Full function name to inspect")
    include_source: bool = Field(True, description="Include source code")
    include_dependencies: bool = Field(True, description="Include dependency analysis")


class MetricsQuery(BaseModel):
    function_name: Optional[str] = Field(None, description="Specific function or all")
    timeframe: Optional[str] = Field("1h", description="Time range for metrics")


class StateSnapshotRequest(BaseModel):
    function_name: Optional[str] = Field(None, description="Filter by function")
    limit: int = Field(10, description="Number of snapshots to return")


class LogQuery(BaseModel):
    function_name: Optional[str] = Field(None, description="Filter by function")
    correlation_id: Optional[str] = Field(None, description="Filter by correlation ID")
    limit: int = Field(100, description="Number of logs to return")


# Helper functions
def import_function(function_path: str):
    """Import a function from its module path."""
    try:
        parts = function_path.split('.')
        module_path = '.'.join(parts[:-1])
        function_name = parts[-1]
        
        module = __import__(module_path, fromlist=[function_name])
        return getattr(module, function_name)
    except Exception as e:
        raise ValueError(f"Failed to import {function_path}: {str(e)}")


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": [
            "/api/functions/hijack",
            "/api/functions/inspect", 
            "/api/metrics",
            "/api/state/snapshots",
            "/api/logs"
        ],
        "components": {
            "hijacker": "ready",
            "inspector": "ready",
            "logger": "ready",
            "performance_tracker": "ready",
            "state_manager": "ready"
        }
    }


@app.post("/api/functions/hijack")
async def hijack_function(request: HijackRequest):
    """Hijack a function with specified strategy."""
    try:
        # Import the target function
        func = import_function(request.function)
        
        # Create strategy based on request
        strategy = None
        options = request.options
        
        if request.strategy == "cache":
            strategy = CacheStrategy(
                duration=options.get("duration", "1h"),
                max_size=options.get("max_size", 1000)
            )
        elif request.strategy == "mock":
            strategy = MockStrategy(
                mock_data=options.get("mock_data", {"mocked": True}),
                environments=options.get("environments", ["dev", "test"])
            )
        elif request.strategy == "block":
            strategy = BlockStrategy(
                return_value=options.get("return_value"),
                raise_error=options.get("raise_error"),
                message=options.get("message", "Function blocked")
            )
        elif request.strategy == "redirect":
            target_func = import_function(options.get("target", request.function))
            strategy = RedirectStrategy(target_func=target_func)
        elif request.strategy == "analyze":
            strategy = AnalysisStrategy(
                track_performance=options.get("track_performance", True),
                track_memory=options.get("track_memory", True),
                callback=lambda ctx, res: logger.info(f"Analysis: {ctx.function.__name__}")
            )
        else:
            raise ValueError(f"Unknown strategy: {request.strategy}")
        
        # Create hijacker
        hijacker = CallHijacker(func, [strategy])
        
        # Register the hijacker
        hijack_registry.register(request.function, hijacker)
        
        # Replace the original function in its module
        module = sys.modules[func.__module__]
        setattr(module, func.__name__, hijacker)
        
        return {
            "success": True,
            "function": request.function,
            "strategy": request.strategy,
            "status": "hijacked",
            "details": {
                "function_name": func.__name__,
                "module": func.__module__,
                "strategies": [s.__class__.__name__ for s in hijacker.strategies],
                "call_count": hijacker.call_count
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to hijack function: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/functions/unhijack")
async def unhijack_function(function_name: str):
    """Remove hijacking from a function."""
    try:
        hijacker = hijack_registry.get(function_name)
        if not hijacker:
            raise ValueError(f"Function {function_name} is not hijacked")
        
        # Restore original function
        module = sys.modules[hijacker.func.__module__]
        setattr(module, hijacker.func.__name__, hijacker.func)
        
        # Unregister
        hijack_registry.unregister(function_name)
        
        return {
            "success": True,
            "function": function_name,
            "status": "unhijacked",
            "metrics": hijacker.get_metrics()
        }
        
    except Exception as e:
        logger.error(f"Failed to unhijack function: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/functions/inspect")
async def inspect_function(request: InspectRequest):
    """Inspect a function and return detailed information."""
    try:
        # Import the function
        func = import_function(request.function)
        
        # Get inspection data
        info = inspector.inspect_function(func)
        
        result = {
            "success": True,
            "function": request.function,
            "inspection": {
                "signature": info.signature.to_dict(),
                "metadata": info.metadata.to_dict(),
                "json_schema": info.schema,
                "mcp_tool": info.mcp_tool_definition
            }
        }
        
        if request.include_dependencies:
            result["inspection"]["dependencies"] = info.dependencies.to_dict()
        
        if request.include_source:
            result["inspection"]["source"] = info.metadata.source_code
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to inspect function: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/metrics")
async def get_all_metrics():
    """Get performance metrics for all tracked functions."""
    try:
        metrics = perf_tracker.get_metrics()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "functions": [
                {
                    "name": name,
                    "call_count": m.call_count,
                    "total_time": m.total_time,
                    "avg_time": m.avg_time,
                    "min_time": m.min_time,
                    "max_time": m.max_time,
                    "exceptions": m.exceptions,
                    "last_called": m.last_called.isoformat() if m.last_called else None
                }
                for name, m in metrics.items()
            ],
            "summary": {
                "total_functions": len(metrics),
                "total_calls": sum(m.call_count for m in metrics.values()),
                "total_time": sum(m.total_time for m in metrics.values()),
                "total_exceptions": sum(m.exceptions for m in metrics.values())
            },
            "overhead": perf_tracker.get_overhead()
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/{function_name}")
async def get_function_metrics(function_name: str):
    """Get performance metrics for a specific function."""
    try:
        metrics = perf_tracker.get_metrics(function_name)
        if not metrics or metrics.call_count == 0:
            raise ValueError(f"No metrics found for {function_name}")
        
        return {
            "success": True,
            "function": function_name,
            "metrics": {
                "call_count": metrics.call_count,
                "total_time": metrics.total_time,
                "avg_time": metrics.avg_time,
                "min_time": metrics.min_time,
                "max_time": metrics.max_time,
                "exceptions": metrics.exceptions,
                "last_called": metrics.last_called.isoformat() if metrics.last_called else None,
                "total_memory": metrics.total_memory,
                "peak_memory": metrics.peak_memory
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get function metrics: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/state/snapshots")
async def get_state_snapshots(request: StateSnapshotRequest):
    """Get state snapshots with optional filtering."""
    try:
        snapshots = state_manager.get_snapshots(
            function_name=request.function_name,
            limit=request.limit
        )
        
        return {
            "success": True,
            "snapshots": [
                {
                    "id": s.id,
                    "timestamp": s.timestamp.isoformat(),
                    "function_name": s.function_name,
                    "state_type": s.state_type.value,
                    "data": s.data,
                    "metadata": s.metadata
                }
                for s in snapshots
            ],
            "timeline": state_manager.get_timeline_summary()
        }
        
    except Exception as e:
        logger.error(f"Failed to get snapshots: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/state/timeline")
async def get_timeline_summary():
    """Get state timeline summary."""
    try:
        return {
            "success": True,
            "timeline": state_manager.get_timeline_summary()
        }
    except Exception as e:
        logger.error(f"Failed to get timeline: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/logs")
async def get_logs(query: LogQuery):
    """Get function logs with optional filtering."""
    try:
        # Get logs from the global logger's stream manager
        logs = global_logger._stream_manager.get_recent_logs(query.limit)
        
        # Filter if needed
        if query.function_name:
            logs = [l for l in logs if query.function_name in l.get("function", "")]
        
        if query.correlation_id:
            logs = [l for l in logs if l.get("correlation_id") == query.correlation_id]
        
        return {
            "success": True,
            "logs": logs,
            "count": len(logs)
        }
        
    except Exception as e:
        logger.error(f"Failed to get logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/hijacked")
async def list_hijacked_functions():
    """List all currently hijacked functions."""
    try:
        hijacked = []
        for func_name, hijacker in hijack_registry._registry.items():
            hijacked.append({
                "function": func_name,
                "strategies": [s.__class__.__name__ for s in hijacker.strategies],
                "call_count": hijacker.call_count,
                "metrics": hijacker.get_metrics()
            })
        
        return {
            "success": True,
            "hijacked_functions": hijacked,
            "count": len(hijacked)
        }
        
    except Exception as e:
        logger.error(f"Failed to list hijacked functions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "type": type(exc).__name__
        }
    )


# Server startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize server on startup."""
    logger.info("Gnosis Mystic MCP Server starting up...")
    logger.info(f"Server version: 0.1.0")
    logger.info(f"Python version: {sys.version}")
    

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Gnosis Mystic MCP Server shutting down...")
    # Could add cleanup logic here if needed


def run_server(host: str = "0.0.0.0", port: int = 8899):
    """Run the MCP server."""
    logger.info(f"Starting Gnosis Mystic MCP Server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the server
    run_server()