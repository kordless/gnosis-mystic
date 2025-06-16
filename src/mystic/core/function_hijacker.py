"""
Enhanced Function Hijacker for Gnosis Mystic

This module provides advanced function hijacking capabilities with multiple strategies,
MCP awareness, and real-time notifications for AI assistant integration.
"""

import functools
import hashlib
import pickle
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

from ..config import Config


class HijackPriority(Enum):
    """Priority levels for hijacking strategies."""

    HIGHEST = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    LOWEST = 5


@dataclass
class HijackContext:
    """Context information for hijack decisions."""

    function: Callable
    args: tuple
    kwargs: dict
    environment: str = "development"  # development, testing, production
    timestamp: datetime = field(default_factory=datetime.now)
    call_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HijackResult:
    """Result of a hijack operation."""

    executed: bool
    strategy: Optional["HijackStrategy"] = None
    result: Any = None
    error: Optional[Exception] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class HijackStrategy:
    """Base class for hijacking strategies."""

    def __init__(self, priority: HijackPriority = HijackPriority.NORMAL):
        self.priority = priority
        self.name = self.__class__.__name__

    def should_hijack(self, context: HijackContext) -> bool:
        """Determine if this strategy should hijack the call."""
        return True

    def hijack_call(self, context: HijackContext, original_func: Callable) -> HijackResult:
        """Execute the hijack strategy."""
        raise NotImplementedError

    def __repr__(self):
        return f"{self.name}(priority={self.priority.name})"


class CacheStrategy(HijackStrategy):
    """Cache function results with disk persistence and TTL support."""

    def __init__(
        self,
        duration: Union[str, timedelta] = "1h",
        cache_dir: Optional[Path] = None,
        max_size: int = 1000,
        priority: HijackPriority = HijackPriority.HIGH,
    ):
        super().__init__(priority)
        self.duration = self._parse_duration(duration)
        self.cache_dir = cache_dir or Path(Config.get_cache_dir()) / "function_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size
        self._memory_cache: Dict[str, tuple] = {}
        self._access_times: Dict[str, datetime] = {}
        self._lock = threading.RLock()

    def _parse_duration(self, duration: Union[str, timedelta]) -> timedelta:
        """Parse duration string or timedelta."""
        if isinstance(duration, timedelta):
            return duration

        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        if duration[-1] in units:
            value = int(duration[:-1])
            return timedelta(seconds=value * units[duration[-1]])
        return timedelta(hours=1)

    def _get_cache_key(self, context: HijackContext) -> str:
        """Generate cache key for function call."""
        func_name = f"{context.function.__module__}.{context.function.__name__}"
        args_repr = repr(context.args)
        kwargs_repr = repr(sorted(context.kwargs.items()))
        key_str = f"{func_name}:{args_repr}:{kwargs_repr}"
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key."""
        return self.cache_dir / f"{key}.cache"

    def _load_from_disk(self, key: str) -> Optional[tuple]:
        """Load cached result from disk."""
        cache_file = self._get_cache_file(key)
        if cache_file.exists():
            try:
                with open(cache_file, "rb") as f:
                    return pickle.load(f)
            except Exception:
                cache_file.unlink(missing_ok=True)
        return None

    def _save_to_disk(self, key: str, value: Any, timestamp: datetime):
        """Save result to disk cache."""
        cache_file = self._get_cache_file(key)
        try:
            with open(cache_file, "wb") as f:
                pickle.dump((value, timestamp), f)
        except Exception:
            pass

    def _evict_old_entries(self):
        """Evict old entries if cache is full."""
        with self._lock:
            if len(self._memory_cache) >= self.max_size:
                # Remove oldest accessed entries
                sorted_keys = sorted(self._access_times.items(), key=lambda x: x[1])
                for key, _ in sorted_keys[: len(sorted_keys) // 2]:
                    self._memory_cache.pop(key, None)
                    self._access_times.pop(key, None)

    def should_hijack(self, context: HijackContext) -> bool:
        """Always return True for cache strategy to handle caching."""
        # CacheStrategy should always process calls to handle both cache hits and misses
        return True

    def has_cached_value(self, context: HijackContext) -> bool:
        """Check if we have a valid cached result."""
        key = self._get_cache_key(context)

        # Check memory cache first
        with self._lock:
            if key in self._memory_cache:
                value, timestamp = self._memory_cache[key]
                if datetime.now() - timestamp < self.duration:
                    return True
                else:
                    # Expired
                    self._memory_cache.pop(key, None)
                    self._access_times.pop(key, None)

        # Check disk cache
        cached = self._load_from_disk(key)
        if cached:
            value, timestamp = cached
            if datetime.now() - timestamp < self.duration:
                return True
            else:
                # Expired
                self._get_cache_file(key).unlink(missing_ok=True)

        return False

    def hijack_call(self, context: HijackContext, original_func: Callable) -> HijackResult:
        """Return cached result or execute and cache."""
        key = self._get_cache_key(context)

        # Check memory cache first
        with self._lock:
            if key in self._memory_cache:
                value, timestamp = self._memory_cache[key]
                if datetime.now() - timestamp < self.duration:
                    self._access_times[key] = datetime.now()
                    return HijackResult(
                        executed=True,
                        strategy=self,
                        result=value,
                        metadata={"cache_hit": True, "cache_key": key},
                    )
                else:
                    # Expired, remove from cache
                    self._memory_cache.pop(key, None)
                    self._access_times.pop(key, None)

        # Check disk cache
        cached = self._load_from_disk(key)
        if cached:
            value, timestamp = cached
            if datetime.now() - timestamp < self.duration:
                # Valid cache, add to memory and return
                with self._lock:
                    self._evict_old_entries()
                    self._memory_cache[key] = (value, timestamp)
                    self._access_times[key] = datetime.now()
                return HijackResult(
                    executed=True,
                    strategy=self,
                    result=value,
                    metadata={"cache_hit": True, "cache_key": key},
                )

        # Execute function
        start_time = time.time()
        try:
            result = original_func(*context.args, **context.kwargs)
            execution_time = time.time() - start_time

            # Cache result
            timestamp = datetime.now()
            with self._lock:
                self._evict_old_entries()
                self._memory_cache[key] = (result, timestamp)
                self._access_times[key] = timestamp

            # Save to disk
            self._save_to_disk(key, result, timestamp)

            return HijackResult(
                executed=True,
                strategy=self,
                result=result,
                execution_time=execution_time,
                metadata={"cache_hit": False, "cache_key": key},
            )
        except Exception as e:
            return HijackResult(
                executed=False, strategy=self, error=e, execution_time=time.time() - start_time
            )


class MockStrategy(HijackStrategy):
    """Mock function calls with environment-aware behavior."""

    def __init__(
        self,
        mock_data: Union[Any, Callable, Dict[str, Any]] = None,
        environments: List[str] = None,
        priority: HijackPriority = HijackPriority.HIGH,
    ):
        super().__init__(priority)
        self.mock_data = mock_data
        self.environments = environments or ["development", "testing"]

    def should_hijack(self, context: HijackContext) -> bool:
        """Only hijack in specified environments."""
        return context.environment in self.environments

    def hijack_call(self, context: HijackContext, original_func: Callable) -> HijackResult:
        """Return mock data instead of executing function."""
        start_time = time.time()

        try:
            if callable(self.mock_data) and not isinstance(self.mock_data, type):
                # Mock data is a function
                result = self.mock_data(*context.args, **context.kwargs)
            elif isinstance(self.mock_data, dict):
                # Mock data is environment-specific
                result = self.mock_data.get(context.environment, None)
            else:
                # Static mock data
                result = self.mock_data

            return HijackResult(
                executed=True,
                strategy=self,
                result=result,
                execution_time=time.time() - start_time,
                metadata={"mocked": True, "environment": context.environment},
            )
        except Exception as e:
            return HijackResult(
                executed=False, strategy=self, error=e, execution_time=time.time() - start_time
            )


class BlockStrategy(HijackStrategy):
    """Block function execution with optional return value."""

    def __init__(
        self,
        return_value: Any = None,
        raise_error: Optional[Type[Exception]] = None,
        message: str = "Function blocked by BlockStrategy",
        priority: HijackPriority = HijackPriority.HIGHEST,
    ):
        super().__init__(priority)
        self.return_value = return_value
        self.raise_error = raise_error
        self.message = message

    def hijack_call(self, context: HijackContext, original_func: Callable) -> HijackResult:
        """Block function execution."""
        if self.raise_error:
            error = self.raise_error(self.message)
            return HijackResult(
                executed=False,
                strategy=self,
                error=error,
                metadata={"blocked": True, "message": self.message},
            )

        return HijackResult(
            executed=True,
            strategy=self,
            result=self.return_value,
            metadata={"blocked": True, "message": self.message},
        )


class RedirectStrategy(HijackStrategy):
    """Redirect calls to a different function."""

    def __init__(
        self,
        target_func: Callable,
        transform_args: Optional[Callable] = None,
        transform_result: Optional[Callable] = None,
        priority: HijackPriority = HijackPriority.NORMAL,
    ):
        super().__init__(priority)
        self.target_func = target_func
        self.transform_args = transform_args
        self.transform_result = transform_result

    def hijack_call(self, context: HijackContext, original_func: Callable) -> HijackResult:
        """Redirect to target function."""
        start_time = time.time()

        try:
            # Transform arguments if needed
            args = context.args
            kwargs = context.kwargs
            if self.transform_args:
                args, kwargs = self.transform_args(args, kwargs)

            # Call target function
            result = self.target_func(*args, **kwargs)

            # Transform result if needed
            if self.transform_result:
                result = self.transform_result(result)

            return HijackResult(
                executed=True,
                strategy=self,
                result=result,
                execution_time=time.time() - start_time,
                metadata={"redirected_to": self.target_func.__name__},
            )
        except Exception as e:
            return HijackResult(
                executed=False, strategy=self, error=e, execution_time=time.time() - start_time
            )


class AnalysisStrategy(HijackStrategy):
    """Analyze function calls for performance and behavior."""

    def __init__(
        self,
        track_performance: bool = True,
        track_arguments: bool = True,
        track_results: bool = True,
        callback: Optional[Callable] = None,
        priority: HijackPriority = HijackPriority.LOW,
    ):
        super().__init__(priority)
        self.track_performance = track_performance
        self.track_arguments = track_arguments
        self.track_results = track_results
        self.callback = callback
        self.metrics = defaultdict(list)
        self._lock = threading.RLock()

    def hijack_call(self, context: HijackContext, original_func: Callable) -> HijackResult:
        """Execute function and analyze."""
        start_time = time.time()
        memory_before = 0

        if self.track_performance:
            try:
                import psutil

                process = psutil.Process()
                memory_before = process.memory_info().rss
            except Exception:
                pass

        try:
            # Execute original function
            result = original_func(*context.args, **context.kwargs)
            execution_time = time.time() - start_time

            # Collect metrics
            metrics = {
                "timestamp": datetime.now(),
                "execution_time": execution_time,
                "success": True,
            }

            if self.track_performance:
                try:
                    import psutil

                    process = psutil.Process()
                    memory_after = process.memory_info().rss
                    metrics["memory_delta"] = memory_after - memory_before
                    metrics["cpu_percent"] = process.cpu_percent()
                except Exception:
                    pass

            if self.track_arguments:
                metrics["args"] = context.args
                metrics["kwargs"] = context.kwargs

            if self.track_results:
                metrics["result"] = result
                metrics["result_size"] = len(str(result))

            # Store metrics
            func_name = f"{context.function.__module__}.{context.function.__name__}"
            with self._lock:
                self.metrics[func_name].append(metrics)

            # Call callback if provided
            if self.callback:
                self.callback(context, result, metrics)

            return HijackResult(
                executed=True,
                strategy=self,
                result=result,
                execution_time=execution_time,
                metadata=metrics,
            )
        except Exception as e:
            metrics = {
                "timestamp": datetime.now(),
                "execution_time": time.time() - start_time,
                "success": False,
                "error": str(e),
            }

            func_name = f"{context.function.__module__}.{context.function.__name__}"
            with self._lock:
                self.metrics[func_name].append(metrics)

            return HijackResult(
                executed=False,
                strategy=self,
                error=e,
                execution_time=time.time() - start_time,
                metadata=metrics,
            )

    def get_metrics(self, func_name: Optional[str] = None) -> Dict[str, List[Dict]]:
        """Get collected metrics."""
        with self._lock:
            if func_name:
                return {func_name: self.metrics.get(func_name, [])}
            return dict(self.metrics)


class ConditionalStrategy(HijackStrategy):
    """Conditional hijacking based on custom criteria."""

    def __init__(
        self,
        condition: Callable[[HijackContext], bool],
        true_strategy: HijackStrategy,
        false_strategy: Optional[HijackStrategy] = None,
        priority: HijackPriority = HijackPriority.NORMAL,
    ):
        super().__init__(priority)
        self.condition = condition
        self.true_strategy = true_strategy
        self.false_strategy = false_strategy

    def should_hijack(self, context: HijackContext) -> bool:
        """Check if condition is met."""
        try:
            if self.condition(context):
                return self.true_strategy.should_hijack(context)
            elif self.false_strategy:
                return self.false_strategy.should_hijack(context)
            return False
        except Exception:
            return False

    def hijack_call(self, context: HijackContext, original_func: Callable) -> HijackResult:
        """Execute appropriate strategy based on condition."""
        try:
            if self.condition(context):
                return self.true_strategy.hijack_call(context, original_func)
            elif self.false_strategy:
                return self.false_strategy.hijack_call(context, original_func)
            else:
                # No false strategy, execute original
                result = original_func(*context.args, **context.kwargs)
                return HijackResult(
                    executed=True, strategy=self, result=result, metadata={"condition_met": False}
                )
        except Exception as e:
            return HijackResult(executed=False, strategy=self, error=e)


class CallHijacker:
    """Enhanced function call hijacker with MCP integration."""

    # Class-level registry for all hijacked functions
    _registry: Dict[str, "CallHijacker"] = {}
    _registry_lock = threading.RLock()

    # MCP notification callbacks
    _mcp_callbacks: List[Callable] = []

    def __init__(self, func: Callable, strategies: List[HijackStrategy] = None):
        """Initialize hijacker for a function."""
        self.func = func
        self.func_name = f"{func.__module__}.{func.__name__}"
        self.strategies = sorted(strategies or [], key=lambda s: s.priority.value)
        self.call_count = 0
        self.environment = Config.get_environment()
        self._lock = threading.RLock()

        # Preserve function metadata
        self.__wrapped__ = func
        functools.update_wrapper(self, func)

        # Register hijacker
        with self._registry_lock:
            self._registry[self.func_name] = self

    def __call__(self, *args, **kwargs):
        """Execute hijacked function."""
        with self._lock:
            self.call_count += 1

        # Create context
        context = HijackContext(
            function=self.func,
            args=args,
            kwargs=kwargs,
            environment=self.environment,
            call_count=self.call_count,
        )

        # Try strategies in priority order
        for strategy in self.strategies:
            if strategy.should_hijack(context):
                result = strategy.hijack_call(context, self.func)

                # Notify MCP clients
                self._notify_mcp(context, result)

                if result.error:
                    raise result.error
                return result.result

        # No strategy hijacked, execute original
        start_time = time.time()
        try:
            result_value = self.func(*args, **kwargs)
            result = HijackResult(
                executed=True, result=result_value, execution_time=time.time() - start_time
            )

            # Notify MCP clients
            self._notify_mcp(context, result)

            return result_value
        except Exception as e:
            result = HijackResult(executed=False, error=e, execution_time=time.time() - start_time)

            # Notify MCP clients
            self._notify_mcp(context, result)

            raise

    def _notify_mcp(self, context: HijackContext, result: HijackResult):
        """Send notifications to MCP clients."""
        notification = {
            "type": "function_call",
            "function": self.func_name,
            "timestamp": context.timestamp.isoformat(),
            "environment": context.environment,
            "call_count": context.call_count,
            "executed": result.executed,
            "strategy": result.strategy.name if result.strategy else None,
            "execution_time": result.execution_time,
            "error": str(result.error) if result.error else None,
            "metadata": result.metadata,
        }

        for callback in self._mcp_callbacks:
            try:
                callback(notification)
            except Exception:
                pass

    def add_strategy(self, strategy: HijackStrategy):
        """Add a new strategy."""
        with self._lock:
            self.strategies.append(strategy)
            self.strategies.sort(key=lambda s: s.priority.value)

    def remove_strategy(self, strategy_type: Type[HijackStrategy]):
        """Remove strategies of a specific type."""
        with self._lock:
            self.strategies = [s for s in self.strategies if not isinstance(s, strategy_type)]

    def get_metrics(self) -> Dict[str, Any]:
        """Get hijacker metrics."""
        metrics = {
            "function": self.func_name,
            "call_count": self.call_count,
            "environment": self.environment,
            "strategies": [str(s) for s in self.strategies],
            "strategy_metrics": {},
        }

        # Collect metrics from analysis strategies
        for strategy in self.strategies:
            if isinstance(strategy, AnalysisStrategy):
                metrics["strategy_metrics"][strategy.name] = strategy.get_metrics(self.func_name)

        return metrics

    @classmethod
    def register_mcp_callback(cls, callback: Callable):
        """Register a callback for MCP notifications."""
        cls._mcp_callbacks.append(callback)

    @classmethod
    def get_hijacker(cls, func_name: str) -> Optional["CallHijacker"]:
        """Get hijacker for a function by name."""
        with cls._registry_lock:
            return cls._registry.get(func_name)

    @classmethod
    def get_all_hijackers(cls) -> Dict[str, "CallHijacker"]:
        """Get all registered hijackers."""
        with cls._registry_lock:
            return dict(cls._registry)

    @classmethod
    def unhijack(cls, func_name: str) -> Optional[Callable]:
        """Remove hijacker and return original function."""
        with cls._registry_lock:
            hijacker = cls._registry.pop(func_name, None)
            if hijacker:
                return hijacker.func
            return None


def hijack_function(*strategies, **kwargs):
    """
    Decorator to hijack a function with multiple strategies.

    Args:
        *strategies: HijackStrategy instances to apply
        **kwargs: Additional options:
            - environment: Override environment detection
            - auto_analysis: Automatically add AnalysisStrategy

    Example:
        @hijack_function(
            CacheStrategy(duration="1h"),
            MockStrategy({"dev": "mock_result"}),
            AnalysisStrategy(track_performance=True)
        )
        def expensive_function(x, y):
            return complex_calculation(x, y)
    """

    def decorator(func):
        # Add auto analysis if requested
        strategy_list = list(strategies)
        if kwargs.get("auto_analysis", False):
            strategy_list.append(AnalysisStrategy())

        # Create hijacker
        hijacker = CallHijacker(func, strategy_list)

        # Override environment if specified
        if "environment" in kwargs:
            hijacker.environment = kwargs["environment"]

        return hijacker

    return decorator


# Convenience functions for common hijacking patterns
def cache(duration="1h", **kwargs):
    """Cache decorator."""
    return hijack_function(CacheStrategy(duration=duration, **kwargs))


def mock(mock_data, environments=None, **kwargs):
    """Mock decorator."""
    return hijack_function(MockStrategy(mock_data=mock_data, environments=environments, **kwargs))


def block(return_value=None, raise_error=None, message="Blocked", **kwargs):
    """Block decorator."""
    return hijack_function(
        BlockStrategy(return_value=return_value, raise_error=raise_error, message=message, **kwargs)
    )


def redirect(target_func, **kwargs):
    """Redirect decorator."""
    return hijack_function(RedirectStrategy(target_func=target_func, **kwargs))


def analyze(**kwargs):
    """Analysis decorator."""
    return hijack_function(AnalysisStrategy(**kwargs))



class HijackRegistry:
    """Registry for tracking hijacked functions."""
    
    def __init__(self):
        self._registry: Dict[str, CallHijacker] = {}
        self._lock = threading.RLock()
    
    def register(self, name: str, hijacker: CallHijacker):
        """Register a hijacked function."""
        with self._lock:
            self._registry[name] = hijacker
    
    def unregister(self, name: str):
        """Unregister a hijacked function."""
        with self._lock:
            self._registry.pop(name, None)
    
    def get(self, name: str) -> Optional[CallHijacker]:
        """Get a hijacker by name."""
        with self._lock:
            return self._registry.get(name)
    
    def list_all(self) -> List[str]:
        """List all hijacked function names."""
        with self._lock:
            return list(self._registry.keys())
