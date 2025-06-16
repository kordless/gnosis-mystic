"""
Enhanced Function Logger for Gnosis Mystic

This module provides advanced function logging capabilities with JSON-RPC support,
MCP protocol awareness, correlation IDs, and real-time streaming to AI assistants.
"""

import functools
import json
import logging
import re
import sys
import threading
import time
import uuid
from collections import deque
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union

from ..config import Config


class LogFormat(Enum):
    """Supported log output formats."""

    CONSOLE = "console"
    FILE = "file"
    JSON_RPC = "json_rpc"
    STRUCTURED = "structured"
    MCP_DEBUG = "mcp_debug"


class LogLevel(Enum):
    """Extended log levels for fine-grained control."""

    TRACE = 5
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class SensitiveDataFilter:
    """Filter and redact sensitive data from logs."""

    # Common sensitive patterns
    DEFAULT_PATTERNS = [
        (r"\bpassword['\"]?\s*[:=]\s*['\"]?([^'\"\s,]+)['\"]?", "password=****"),
        (r"\bapi[_-]?key['\"]?\s*[:=]\s*['\"]?([^'\"\s,]+)['\"]?", "api_key=****"),
        (r"\btoken['\"]?\s*[:=]\s*['\"]?([^'\"\s,]+)['\"]?", "token=****"),
        (r"\bsecret['\"]?\s*[:=]\s*['\"]?([^'\"\s,]+)['\"]?", "secret=****"),
        (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "****-****-****-****"),  # Credit card
        (r"\b\d{3}-\d{2}-\d{4}\b", "***-**-****"),  # SSN
    ]

    def __init__(self, custom_patterns: Optional[List[tuple]] = None):
        """Initialize filter with patterns."""
        self.patterns = []
        if custom_patterns:
            self.patterns.extend(custom_patterns)
        self.patterns.extend(self.DEFAULT_PATTERNS)
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.patterns
        ]

    def filter(self, data: Any) -> Any:
        """Filter sensitive data from any value."""
        if isinstance(data, str):
            return self._filter_string(data)
        elif isinstance(data, dict):
            return {k: self.filter(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return type(data)(self.filter(item) for item in data)
        return data

    def _filter_string(self, text: str) -> str:
        """Filter sensitive patterns from string."""
        for pattern, replacement in self.compiled_patterns:
            text = pattern.sub(replacement, text)
        return text


class CorrelationIdManager:
    """Manage correlation IDs for request/response tracking."""

    def __init__(self):
        self._storage = threading.local()
        self._active_ids: Dict[str, datetime] = {}
        self._lock = threading.RLock()

    def generate_id(self) -> str:
        """Generate a new correlation ID."""
        correlation_id = str(uuid.uuid4())
        with self._lock:
            self._active_ids[correlation_id] = datetime.now()
        return correlation_id

    def set_current(self, correlation_id: str):
        """Set current correlation ID for thread."""
        self._storage.correlation_id = correlation_id

    def get_current(self) -> Optional[str]:
        """Get current correlation ID for thread."""
        return getattr(self._storage, "correlation_id", None)

    def clear_current(self):
        """Clear current correlation ID."""
        if hasattr(self._storage, "correlation_id"):
            delattr(self._storage, "correlation_id")

    def cleanup_old(self, max_age_seconds: int = 3600):
        """Clean up old correlation IDs."""
        with self._lock:
            now = datetime.now()
            to_remove = []
            for cid, timestamp in self._active_ids.items():
                if (now - timestamp).total_seconds() > max_age_seconds:
                    to_remove.append(cid)
            for cid in to_remove:
                del self._active_ids[cid]


class LogStreamManager:
    """Manage real-time log streaming to MCP clients."""

    def __init__(self, buffer_size: int = 1000):
        self.buffer = deque(maxlen=buffer_size)
        self.subscribers: Set[Callable] = set()
        self._lock = threading.RLock()

    def add_log(self, log_entry: Dict[str, Any]):
        """Add log entry and notify subscribers."""
        with self._lock:
            self.buffer.append(log_entry)
            for subscriber in self.subscribers:
                try:
                    subscriber(log_entry)
                except Exception:
                    pass

    def subscribe(self, callback: Callable):
        """Subscribe to log stream."""
        with self._lock:
            self.subscribers.add(callback)

    def unsubscribe(self, callback: Callable):
        """Unsubscribe from log stream."""
        with self._lock:
            self.subscribers.discard(callback)

    def get_recent_logs(self, count: int = 100) -> List[Dict[str, Any]]:
        """Get recent log entries."""
        with self._lock:
            return list(self.buffer)[-count:]


class FunctionLogger:
    """Enhanced function logger with MCP integration."""

    # Class-level components
    _correlation_manager = CorrelationIdManager()
    _stream_manager = LogStreamManager()
    _sensitive_filter = SensitiveDataFilter()
    _mcp_callbacks: List[Callable] = []

    def __init__(
        self,
        name: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
        format: LogFormat = LogFormat.CONSOLE,
        level: Union[int, LogLevel] = LogLevel.INFO,
        filter_sensitive: bool = True,
        include_performance: bool = True,
        max_value_length: int = 1000,
        log_file: Optional[Path] = None,
    ):
        """Initialize the enhanced function logger."""
        self.name = name or "mystic.function_logger"
        self.format = format
        self.level = level.value if isinstance(level, LogLevel) else level
        self.filter_sensitive = filter_sensitive
        self.include_performance = include_performance
        self.max_value_length = max_value_length
        self.log_file = log_file
        self.logger = logger or self._setup_logger()

        # Performance tracking
        self.call_count = 0
        self.total_time = 0.0
        self._lock = threading.RLock()

    def _setup_logger(self) -> logging.Logger:
        """Set up Python logger with appropriate handlers."""
        logger = logging.getLogger(self.name)
        logger.setLevel(self.level)

        # Remove existing handlers
        logger.handlers = []

        # Console handler
        if self.format == LogFormat.CONSOLE:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        # File handler
        elif self.format == LogFormat.FILE and self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def log_call(
        self,
        func_name: str,
        args: tuple,
        kwargs: dict,
        correlation_id: Optional[str] = None,
    ) -> str:
        """Log a function call."""
        if not correlation_id:
            correlation_id = self._correlation_manager.generate_id()
            self._correlation_manager.set_current(correlation_id)

        # Truncate large values
        args_str = self._truncate_value(repr(args))
        kwargs_str = self._truncate_value(repr(kwargs))
        
        # Filter sensitive data if enabled
        if self.filter_sensitive:
            args_str = self._sensitive_filter.filter(args_str)
            kwargs_str = self._sensitive_filter.filter(kwargs_str)

        log_entry = {
            "type": "call",
            "timestamp": datetime.now().isoformat(),
            "correlation_id": correlation_id,
            "function": func_name,
            "args": args_str,
            "kwargs": kwargs_str,
        }

        self._log_entry(log_entry)
        return correlation_id

    def log_return(
        self,
        func_name: str,
        result: Any,
        execution_time: float,
        correlation_id: Optional[str] = None,
        error: Optional[Exception] = None,
    ):
        """Log a function return or error."""
        if not correlation_id:
            correlation_id = self._correlation_manager.get_current()

        log_entry = {
            "type": "return",
            "timestamp": datetime.now().isoformat(),
            "correlation_id": correlation_id,
            "function": func_name,
            "execution_time": execution_time,
        }

        if error:
            log_entry["error"] = str(error)
            log_entry["error_type"] = type(error).__name__
        else:
            result_str = self._truncate_value(repr(result))
            # Filter sensitive data if enabled
            if self.filter_sensitive:
                result_str = self._sensitive_filter.filter(result_str)
            log_entry["result"] = result_str

        if self.include_performance:
            log_entry["performance"] = {
                "execution_time_ms": execution_time * 1000,
                "memory_usage": self._get_memory_usage(),
            }

        self._log_entry(log_entry)

        # Update stats
        with self._lock:
            self.call_count += 1
            self.total_time += execution_time

    def log_mcp_request(self, method: str, params: Any, request_id: str):
        """Log MCP request in JSON-RPC format."""
        # Filter sensitive data
        if self.filter_sensitive:
            params = self._sensitive_filter.filter(params)

        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id,
        }

        log_entry = {
            "type": "mcp_request",
            "timestamp": datetime.now().isoformat(),
            "correlation_id": request_id,
            "direction": "incoming",
            "content": request,
        }

        self._log_entry(log_entry)
        self._correlation_manager.set_current(request_id)

    def log_mcp_response(self, result: Any, request_id: str, error: Optional[Dict] = None):
        """Log MCP response in JSON-RPC format."""
        # Filter sensitive data
        if self.filter_sensitive and result is not None:
            result = self._sensitive_filter.filter(result)

        response = {"jsonrpc": "2.0", "id": request_id}

        if error:
            response["error"] = error
        else:
            response["result"] = result

        log_entry = {
            "type": "mcp_response",
            "timestamp": datetime.now().isoformat(),
            "correlation_id": request_id,
            "direction": "outgoing",
            "content": response,
        }

        self._log_entry(log_entry)

    def _log_entry(self, entry: Dict[str, Any]):
        """Log entry in appropriate format."""
        # Add to stream
        self._stream_manager.add_log(entry)

        # Format based on output type
        if self.format == LogFormat.JSON_RPC:
            message = json.dumps(entry, default=str)
        elif self.format == LogFormat.MCP_DEBUG:
            message = self._format_mcp_debug(entry)
        elif self.format == LogFormat.STRUCTURED:
            message = self._format_structured(entry)
        else:
            message = self._format_console(entry)

        # Log at appropriate level
        if entry.get("error") or entry.get("error_type"):
            self.logger.error(message)
        else:
            self.logger.log(self.level, message)

        # Notify MCP callbacks
        for callback in self._mcp_callbacks:
            try:
                callback(entry)
            except Exception:
                pass

    def _format_console(self, entry: Dict[str, Any]) -> str:
        """Format log entry for console output."""
        if entry["type"] == "call":
            return f"→ {entry['function']}({entry['args']}, {entry['kwargs']})"
        elif entry["type"] == "return":
            if "error" in entry:
                return f"← {entry['function']} ✗ {entry['error']} ({entry['execution_time']:.3f}s)"
            else:
                return f"← {entry['function']} → {entry['result']} ({entry['execution_time']:.3f}s)"
        elif entry["type"] == "mcp_request":
            return f"[MCP] → {entry['content']['method']}({entry['content'].get('params', {})})"
        elif entry["type"] == "mcp_response":
            if "error" in entry["content"]:
                return f"[MCP] ← Error: {entry['content']['error']}"
            else:
                return f"[MCP] ← {entry['content'].get('result', 'OK')}"
        return str(entry)

    def _format_structured(self, entry: Dict[str, Any]) -> str:
        """Format as structured log."""
        parts = []
        for key, value in entry.items():
            if isinstance(value, dict):
                value = json.dumps(value, default=str)
            parts.append(f"{key}={value}")
        return " ".join(parts)

    def _format_mcp_debug(self, entry: Dict[str, Any]) -> str:
        """Format like mcp-debug tool."""
        if entry["type"] in ["mcp_request", "mcp_response"]:
            direction = "→" if entry["direction"] == "incoming" else "←"
            content = json.dumps(entry["content"], indent=2, default=str)
            return f"\n{direction} {entry['timestamp']}\n{content}\n"
        return self._format_console(entry)

    def _truncate_value(self, value: str) -> str:
        """Truncate long values."""
        if len(value) > self.max_value_length:
            return value[: self.max_value_length] + "..."
        return value

    def _get_memory_usage(self) -> Optional[int]:
        """Get current memory usage in bytes."""
        try:
            import psutil

            return psutil.Process().memory_info().rss
        except Exception:
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get logger statistics."""
        with self._lock:
            avg_time = self.total_time / self.call_count if self.call_count > 0 else 0
            return {
                "call_count": self.call_count,
                "total_time": self.total_time,
                "average_time": avg_time,
                "recent_logs": self._stream_manager.get_recent_logs(10),
            }

    @classmethod
    def register_mcp_callback(cls, callback: Callable):
        """Register callback for MCP notifications."""
        cls._mcp_callbacks.append(callback)

    @classmethod
    def subscribe_to_stream(cls, callback: Callable):
        """Subscribe to log stream."""
        cls._stream_manager.subscribe(callback)

    @classmethod
    def unsubscribe_from_stream(cls, callback: Callable):
        """Unsubscribe from log stream."""
        cls._stream_manager.unsubscribe(callback)


def create_logger_decorator(
    logger: Optional[FunctionLogger] = None,
    level: Union[int, LogLevel] = LogLevel.INFO,
    include_args: bool = True,
    include_result: bool = True,
    include_performance: bool = True,
    filter_sensitive: bool = True,
    max_value_length: int = 1000,
):
    """Create a logging decorator with specified options."""

    def decorator(func: Callable) -> Callable:
        # Create logger if not provided
        nonlocal logger
        if logger is None:
            logger = FunctionLogger(
                name=f"{func.__module__}.{func.__name__}",
                level=level,
                filter_sensitive=filter_sensitive,
                include_performance=include_performance,
                max_value_length=max_value_length,
            )

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"
            correlation_id = None

            # Log call if enabled
            if include_args:
                correlation_id = logger.log_call(func_name, args, kwargs)

            # Execute function
            start_time = time.time()
            error = None
            result = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                execution_time = time.time() - start_time

                # Log return/error if enabled
                if include_result or error:
                    logger.log_return(
                        func_name, result, execution_time, correlation_id, error
                    )

        return wrapper

    return decorator


# Convenience decorators
def log_calls_and_returns(
    logger: Optional[Union[logging.Logger, FunctionLogger]] = None,
    level: Union[int, LogLevel] = LogLevel.INFO,
    **kwargs,
):
    """Log both function calls and returns."""
    if isinstance(logger, logging.Logger):
        # Convert standard logger to FunctionLogger
        logger = FunctionLogger(logger=logger, level=level)

    return create_logger_decorator(
        logger=logger, level=level, include_args=True, include_result=True, **kwargs
    )


def log_calls_only(
    logger: Optional[Union[logging.Logger, FunctionLogger]] = None,
    level: Union[int, LogLevel] = LogLevel.INFO,
    **kwargs,
):
    """Log only function calls."""
    if isinstance(logger, logging.Logger):
        logger = FunctionLogger(logger=logger, level=level)

    return create_logger_decorator(
        logger=logger, level=level, include_args=True, include_result=False, **kwargs
    )


def log_returns_only(
    logger: Optional[Union[logging.Logger, FunctionLogger]] = None,
    level: Union[int, LogLevel] = LogLevel.INFO,
    **kwargs,
):
    """Log only function returns."""
    if isinstance(logger, logging.Logger):
        logger = FunctionLogger(logger=logger, level=level)

    return create_logger_decorator(
        logger=logger, level=level, include_args=False, include_result=True, **kwargs
    )


def detailed_log(
    logger: Optional[Union[logging.Logger, FunctionLogger]] = None,
    level: Union[int, LogLevel] = LogLevel.DEBUG,
    max_length: int = 5000,
    **kwargs,
):
    """Detailed logging with longer output."""
    if isinstance(logger, logging.Logger):
        logger = FunctionLogger(logger=logger, level=level, max_value_length=max_length)

    return create_logger_decorator(
        logger=logger,
        level=level,
        include_args=True,
        include_result=True,
        include_performance=True,
        max_value_length=max_length,
        **kwargs,
    )


def filtered_log(
    arg_filter: Optional[Callable] = None,
    return_filter: Optional[Callable] = None,
    logger: Optional[Union[logging.Logger, FunctionLogger]] = None,
    level: Union[int, LogLevel] = LogLevel.INFO,
    **kwargs,
):
    """Logging with custom filters."""

    def decorator(func: Callable) -> Callable:
        # Create base decorator
        base_decorator = log_calls_and_returns(logger=logger, level=level, **kwargs)
        wrapped = base_decorator(func)

        # Override wrapper to apply filters
        @functools.wraps(func)
        def filtered_wrapper(*args, **kwargs):
            # Apply argument filter
            filtered_args = args
            filtered_kwargs = kwargs
            if arg_filter:
                filtered_args, filtered_kwargs = arg_filter(args, kwargs)

            # Call with filtered args
            result = wrapped(*filtered_args, **filtered_kwargs)

            # Apply return filter
            if return_filter:
                result = return_filter(result)

            return result

        return filtered_wrapper

    return decorator