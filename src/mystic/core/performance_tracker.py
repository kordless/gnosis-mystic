"""
Enhanced Performance Tracker for Gnosis Mystic

This module provides comprehensive performance monitoring with <1% overhead,
supporting profiling, memory tracking, and real-time metrics streaming.
"""

import cProfile
import gc
import io
import os
import pstats
import sys
import threading
import time
import tracemalloc
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import functools

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from ..config import Config


class MetricType(Enum):
    """Types of performance metrics."""
    
    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    CALL_COUNT = "call_count"
    CACHE_HIT_RATE = "cache_hit_rate"
    THREAD_COUNT = "thread_count"
    GC_STATS = "gc_stats"


class ProfileMode(Enum):
    """Profiling modes."""
    
    OFF = "off"
    BASIC = "basic"  # Just timing
    DETAILED = "detailed"  # CPU profiling
    MEMORY = "memory"  # Memory profiling
    FULL = "full"  # Everything


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    
    function_name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    last_time: float = 0.0
    total_memory: int = 0
    peak_memory: int = 0
    exceptions: int = 0
    last_called: Optional[datetime] = None
    
    def update(self, execution_time: float, memory_delta: int = 0, had_exception: bool = False):
        """Update metrics with new measurement."""
        self.call_count += 1
        self.total_time += execution_time
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.avg_time = self.total_time / self.call_count
        self.last_time = execution_time
        self.total_memory += memory_delta
        self.peak_memory = max(self.peak_memory, memory_delta)
        if had_exception:
            self.exceptions += 1
        self.last_called = datetime.now()


@dataclass
class MemorySnapshot:
    """Memory usage snapshot."""
    
    timestamp: datetime
    rss: int  # Resident Set Size
    vms: int  # Virtual Memory Size
    available: int
    percent: float
    gc_count: Dict[int, int]
    gc_collected: int
    gc_uncollectable: int
    
    @classmethod
    def capture(cls) -> 'MemorySnapshot':
        """Capture current memory state."""
        gc_stats = gc.get_stats()
        gc_count = {i: gc.get_count()[i] if i < len(gc.get_count()) else 0 for i in range(3)}
        
        if HAS_PSUTIL:
            process = psutil.Process()
            mem_info = process.memory_info()
            mem_percent = process.memory_percent()
            available = psutil.virtual_memory().available
        else:
            # Fallback for systems without psutil
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            mem_info = type('MemInfo', (), {
                'rss': usage.ru_maxrss * 1024,  # Convert to bytes
                'vms': 0
            })()
            mem_percent = 0.0
            available = 0
        
        # Get garbage collection info
        gc_collected = sum(stat.get('collected', 0) for stat in gc_stats)
        gc_uncollectable = sum(stat.get('uncollectable', 0) for stat in gc_stats)
        
        return cls(
            timestamp=datetime.now(),
            rss=mem_info.rss,
            vms=mem_info.vms,
            available=available,
            percent=mem_percent,
            gc_count=gc_count,
            gc_collected=gc_collected,
            gc_uncollectable=gc_uncollectable
        )


class PerformanceTracker:
    """High-performance tracker with minimal overhead."""
    
    def __init__(
        self,
        name: Optional[str] = None,
        profile_mode: ProfileMode = ProfileMode.BASIC,
        max_overhead_percent: float = 1.0,
        memory_tracking: bool = True,
        gc_tracking: bool = True,
        thread_safe: bool = True,
        buffer_size: int = 10000,
        auto_report_interval: Optional[int] = None,
    ):
        """Initialize the performance tracker."""
        self.name = name or "mystic.performance_tracker"
        self.profile_mode = profile_mode
        self.max_overhead_percent = max_overhead_percent
        self.memory_tracking = memory_tracking and HAS_PSUTIL
        self.gc_tracking = gc_tracking
        self.thread_safe = thread_safe
        self.buffer_size = buffer_size
        self.auto_report_interval = auto_report_interval
        
        # Metrics storage
        self.metrics: Dict[str, PerformanceMetrics] = defaultdict(
            lambda: PerformanceMetrics(function_name="")
        )
        self.call_stack: List[Tuple[str, float, Optional[int]]] = []
        self.overhead_measurements: deque = deque(maxlen=1000)
        
        # Memory tracking
        self.memory_snapshots: deque = deque(maxlen=buffer_size)
        self.memory_tracker_enabled = False
        if profile_mode == ProfileMode.MEMORY or profile_mode == ProfileMode.FULL:
            self._start_memory_tracking()
        
        # Thread safety
        self._lock = threading.RLock() if thread_safe else None
        
        # CPU profiler
        self.profiler: Optional[cProfile.Profile] = None
        if profile_mode in (ProfileMode.DETAILED, ProfileMode.FULL):
            self.profiler = cProfile.Profile()
        
        # Auto-reporting
        self._report_thread: Optional[threading.Thread] = None
        if auto_report_interval:
            self._start_auto_reporting()
        
        # Callbacks
        self.metric_callbacks: List[Callable[[str, PerformanceMetrics], None]] = []
        self.threshold_callbacks: Dict[str, List[Tuple[float, Callable]]] = defaultdict(list)
    
    def _start_memory_tracking(self):
        """Start memory tracking."""
        if self.memory_tracking:
            try:
                tracemalloc.start()
                self.memory_tracker_enabled = True
            except Exception:
                self.memory_tracker_enabled = False
    
    def _stop_memory_tracking(self):
        """Stop memory tracking."""
        if self.memory_tracker_enabled:
            try:
                tracemalloc.stop()
            except Exception:
                pass
            self.memory_tracker_enabled = False
    
    def _start_auto_reporting(self):
        """Start automatic reporting thread."""
        def report_loop():
            while self.auto_report_interval:
                time.sleep(self.auto_report_interval)
                self.generate_report()
        
        self._report_thread = threading.Thread(target=report_loop, daemon=True)
        self._report_thread.start()
    
    def track_function(self, func: Callable) -> Callable:
        """Decorator to track function performance."""
        # Use __name__ for consistency with tests
        func_name = f"{func.__module__}.{func.__name__}"
        
        # Pre-create metrics entry to reduce overhead
        with self._get_lock():
            if func_name not in self.metrics:
                self.metrics[func_name] = PerformanceMetrics(function_name=func_name)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Measure overhead
            overhead_start = time.perf_counter()
            
            # Start tracking
            start_time = time.perf_counter()
            start_memory = self._get_memory_usage() if self.memory_tracking else 0
            
            # Push to call stack
            with self._get_lock():
                self.call_stack.append((func_name, start_time, start_memory))
            
            # Profile if enabled
            if self.profiler and self.profile_mode in (ProfileMode.DETAILED, ProfileMode.FULL):
                self.profiler.enable()
            
            # Execute function
            had_exception = False
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                had_exception = True
                raise
            finally:
                # Stop profiling
                if self.profiler and self.profile_mode in (ProfileMode.DETAILED, ProfileMode.FULL):
                    self.profiler.disable()
                
                # Calculate metrics
                end_time = time.perf_counter()
                execution_time = end_time - start_time
                
                # Memory delta
                memory_delta = 0
                if self.memory_tracking:
                    end_memory = self._get_memory_usage()
                    memory_delta = end_memory - start_memory
                
                # Pop from call stack
                with self._get_lock():
                    if self.call_stack and self.call_stack[-1][0] == func_name:
                        self.call_stack.pop()
                
                # Update metrics
                with self._get_lock():
                    metrics = self.metrics[func_name]
                    metrics.update(execution_time, memory_delta, had_exception)
                    
                    # Check thresholds
                    self._check_thresholds(func_name, metrics)
                    
                    # Notify callbacks
                    for callback in self.metric_callbacks:
                        try:
                            callback(func_name, metrics)
                        except Exception:
                            pass
                
                # Measure overhead
                overhead_time = time.perf_counter() - overhead_start - execution_time
                self.overhead_measurements.append(overhead_time)
                
                # GC tracking
                if self.gc_tracking and gc.get_count()[0] > 100:
                    gc.collect(0)  # Collect generation 0 only
        
        # Add wrapper attributes
        wrapper.__wrapped__ = func
        wrapper.metrics = lambda: self.get_metrics(func_name)
        
        return wrapper
    
    def _get_lock(self):
        """Get lock context manager or dummy."""
        if self._lock:
            return self._lock
        else:
            # Dummy context manager
            class DummyLock:
                def __enter__(self): pass
                def __exit__(self, *args): pass
            return DummyLock()
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        if HAS_PSUTIL:
            return psutil.Process().memory_info().rss
        else:
            return 0
    
    def _check_thresholds(self, func_name: str, metrics: PerformanceMetrics):
        """Check if any thresholds are exceeded."""
        for threshold_type, callbacks in self.threshold_callbacks.items():
            for threshold, callback in callbacks:
                exceeded = False
                
                if threshold_type == "execution_time" and metrics.last_time > threshold:
                    exceeded = True
                elif threshold_type == "memory" and metrics.peak_memory > threshold:
                    exceeded = True
                elif threshold_type == "call_count" and metrics.call_count > threshold:
                    exceeded = True
                
                if exceeded:
                    try:
                        callback(func_name, metrics, threshold_type, threshold)
                    except Exception:
                        pass
    
    def get_metrics(self, func_name: Optional[str] = None) -> Union[PerformanceMetrics, Dict[str, PerformanceMetrics]]:
        """Get metrics for a specific function or all functions."""
        with self._get_lock():
            if func_name:
                return self.metrics.get(func_name, PerformanceMetrics(function_name=func_name))
            else:
                return dict(self.metrics)
    
    def get_overhead(self) -> Dict[str, float]:
        """Calculate tracking overhead statistics."""
        if not self.overhead_measurements:
            return {
                "avg_overhead_ms": 0.0,
                "max_overhead_ms": 0.0,
                "overhead_percent": 0.0
            }
        
        overhead_times = list(self.overhead_measurements)
        avg_overhead = sum(overhead_times) / len(overhead_times)
        max_overhead = max(overhead_times)
        
        # Calculate overhead percentage
        total_execution_time = sum(m.total_time for m in self.metrics.values())
        total_overhead = sum(overhead_times)
        overhead_percent = (total_overhead / total_execution_time * 100) if total_execution_time > 0 else 0
        
        return {
            "avg_overhead_ms": avg_overhead * 1000,
            "max_overhead_ms": max_overhead * 1000,
            "overhead_percent": overhead_percent,
            "measurements": len(overhead_times)
        }
    
    def get_memory_snapshots(self, last_n: Optional[int] = None) -> List[MemorySnapshot]:
        """Get recent memory snapshots."""
        with self._get_lock():
            snapshots = list(self.memory_snapshots)
            if last_n:
                return snapshots[-last_n:]
            return snapshots
    
    def capture_memory_snapshot(self):
        """Manually capture a memory snapshot."""
        snapshot = MemorySnapshot.capture()
        with self._get_lock():
            self.memory_snapshots.append(snapshot)
        return snapshot
    
    def get_profile_stats(self, sort_by: str = "cumulative", top_n: int = 20) -> Optional[str]:
        """Get profiler statistics."""
        if not self.profiler:
            return None
        
        stream = io.StringIO()
        stats = pstats.Stats(self.profiler, stream=stream)
        stats.sort_stats(sort_by)
        stats.print_stats(top_n)
        return stream.getvalue()
    
    def reset_metrics(self, func_name: Optional[str] = None):
        """Reset metrics for specific function or all."""
        with self._get_lock():
            if func_name:
                if func_name in self.metrics:
                    self.metrics[func_name] = PerformanceMetrics(function_name=func_name)
            else:
                self.metrics.clear()
                self.overhead_measurements.clear()
                if self.profiler:
                    self.profiler.clear()
    
    def add_metric_callback(self, callback: Callable[[str, PerformanceMetrics], None]):
        """Add callback for metric updates."""
        self.metric_callbacks.append(callback)
    
    def add_threshold_callback(
        self,
        threshold_type: str,
        threshold: float,
        callback: Callable[[str, PerformanceMetrics, str, float], None]
    ):
        """Add callback for threshold violations."""
        self.threshold_callbacks[threshold_type].append((threshold, callback))
    
    def generate_report(self, output_file: Optional[Path] = None) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        with self._get_lock():
            report = {
                "timestamp": datetime.now().isoformat(),
                "tracker_name": self.name,
                "profile_mode": self.profile_mode.value,
                "summary": {
                    "total_functions_tracked": len(self.metrics),
                    "total_calls": sum(m.call_count for m in self.metrics.values()),
                    "total_time": sum(m.total_time for m in self.metrics.values()),
                    "total_exceptions": sum(m.exceptions for m in self.metrics.values()),
                },
                "overhead": self.get_overhead(),
                "top_by_time": self._get_top_functions("total_time", 10),
                "top_by_calls": self._get_top_functions("call_count", 10),
                "top_by_avg_time": self._get_top_functions("avg_time", 10),
                "functions": {
                    name: {
                        "call_count": m.call_count,
                        "total_time": m.total_time,
                        "avg_time": m.avg_time,
                        "min_time": m.min_time,
                        "max_time": m.max_time,
                        "exceptions": m.exceptions,
                        "last_called": m.last_called.isoformat() if m.last_called else None
                    }
                    for name, m in self.metrics.items()
                }
            }
            
            # Add memory report if available
            if self.memory_tracking and self.memory_snapshots:
                latest_snapshot = self.memory_snapshots[-1]
                report["memory"] = {
                    "current_rss_mb": latest_snapshot.rss / 1024 / 1024,
                    "current_percent": latest_snapshot.percent,
                    "gc_stats": latest_snapshot.gc_count,
                    "snapshot_count": len(self.memory_snapshots)
                }
            
            # Add profile stats if available
            if self.profiler:
                report["profile_stats"] = self.get_profile_stats()
        
        # Save to file if requested
        if output_file:
            import json
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
        
        return report
    
    def _get_top_functions(self, sort_key: str, limit: int) -> List[Dict[str, Any]]:
        """Get top functions by specified metric."""
        sorted_metrics = sorted(
            self.metrics.items(),
            key=lambda x: getattr(x[1], sort_key),
            reverse=True
        )[:limit]
        
        return [
            {
                "function": name,
                "value": getattr(metrics, sort_key),
                "call_count": metrics.call_count
            }
            for name, metrics in sorted_metrics
        ]
    
    def __enter__(self):
        """Context manager entry."""
        if self.profiler:
            self.profiler.enable()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.profiler:
            self.profiler.disable()
        
        # Generate report on exit if auto-reporting
        if self.auto_report_interval:
            self.generate_report()


# Singleton instance for global tracking
_global_tracker = PerformanceTracker(
    name="mystic.global_tracker",
    profile_mode=ProfileMode.BASIC,
    thread_safe=True
)


# Convenience decorators
def track_performance(
    profile_mode: ProfileMode = ProfileMode.BASIC,
    memory_tracking: bool = True,
    tracker: Optional[PerformanceTracker] = None
):
    """Decorator to track function performance."""
    if tracker is None:
        tracker = _global_tracker
    
    def decorator(func):
        return tracker.track_function(func)
    
    return decorator


def profile_function(sort_by: str = "cumulative", top_n: int = 20):
    """Decorator for detailed profiling of a single function."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            profiler = cProfile.Profile()
            profiler.enable()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                profiler.disable()
                stream = io.StringIO()
                stats = pstats.Stats(profiler, stream=stream)
                stats.sort_stats(sort_by)
                stats.print_stats(top_n)
                print(f"\n{func.__name__} Profile:\n{stream.getvalue()}")
        return wrapper
    return decorator


def time_it(func):
    """Simple timing decorator with minimal overhead."""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start
            print(f"{func.__name__} took {elapsed:.6f} seconds")
    return wrapper


# Utility functions
def get_global_tracker() -> PerformanceTracker:
    """Get the global performance tracker instance."""
    return _global_tracker


def reset_global_tracker():
    """Reset the global tracker metrics."""
    _global_tracker.reset_metrics()


def generate_global_report(output_file: Optional[Path] = None) -> Dict[str, Any]:
    """Generate report from global tracker."""
    return _global_tracker.generate_report(output_file)