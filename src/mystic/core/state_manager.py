"""
Enhanced State Manager for Gnosis Mystic

This module provides comprehensive state management with time-travel debugging,
snapshot capabilities, and state diffing for enhanced debugging experience.
"""

import copy
import json
import pickle
import threading
import time
import weakref
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from ..config import Config


class StateType(Enum):
    """Types of state data."""
    
    VARIABLE = "variable"
    FUNCTION_ARGS = "function_args"
    FUNCTION_RETURN = "function_return"
    EXCEPTION = "exception"
    GLOBAL = "global"
    LOCAL = "local"
    ATTRIBUTE = "attribute"


class DiffOperation(Enum):
    """Types of diff operations."""
    
    ADD = "add"
    REMOVE = "remove"
    MODIFY = "modify"
    NONE = "none"


@dataclass
class StateSnapshot:
    """A snapshot of state at a specific point in time."""
    
    id: str
    timestamp: datetime
    function_name: Optional[str]
    line_number: Optional[int]
    state_type: StateType
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "function_name": self.function_name,
            "line_number": self.line_number,
            "state_type": self.state_type.value,
            "data": self._serialize_data(self.data),
            "metadata": self.metadata
        }
    
    def _serialize_data(self, data: Any) -> Any:
        """Serialize data for storage."""
        if isinstance(data, dict):
            return {k: self._serialize_data(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return type(data)(self._serialize_data(item) for item in data)
        elif hasattr(data, "__dict__"):
            # Custom object - store class info and attributes
            return {
                "__class__": f"{data.__class__.__module__}.{data.__class__.__name__}",
                "__dict__": self._serialize_data(vars(data))
            }
        else:
            # Primitive or serializable type
            try:
                json.dumps(data)
                return data
            except:
                # For non-serializable objects, check if it's the actual object
                # If so, serialize it as a custom object
                if hasattr(data, "__dict__"):
                    return {
                        "__class__": f"{data.__class__.__module__}.{data.__class__.__name__}",
                        "__dict__": self._serialize_data(vars(data))
                    }
                else:
                    return repr(data)


@dataclass
class StateDiff:
    """Difference between two state snapshots."""
    
    operation: DiffOperation
    path: List[str]
    old_value: Any = None
    new_value: Any = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "operation": self.operation.value,
            "path": ".".join(self.path),
            "old_value": self.old_value,
            "new_value": self.new_value
        }


class StateManager:
    """Enhanced state manager with time-travel debugging."""
    
    def __init__(
        self,
        name: Optional[str] = None,
        max_snapshots: int = 1000,
        enable_time_travel: bool = True,
        enable_diffing: bool = True,
        auto_snapshot_interval: Optional[float] = None,
        thread_safe: bool = True,
    ):
        """Initialize the state manager."""
        self.name = name or "mystic.state_manager"
        self.max_snapshots = max_snapshots
        self.enable_time_travel = enable_time_travel
        self.enable_diffing = enable_diffing
        self.auto_snapshot_interval = auto_snapshot_interval
        self.thread_safe = thread_safe
        
        # Storage
        self.snapshots: deque = deque(maxlen=max_snapshots)
        self.snapshot_index: Dict[str, StateSnapshot] = {}
        self.current_state: Dict[str, Any] = {}
        self.watchers: Dict[str, List[Callable]] = defaultdict(list)
        self.breakpoints: Set[Tuple[Optional[str], Optional[int]]] = set()
        
        # Time travel
        self.timeline_position: int = -1
        self.bookmark_positions: Dict[str, int] = {}
        
        # Thread safety
        self._lock = threading.RLock() if thread_safe else None
        self._snapshot_counter = 0
        
        # Weak references to tracked objects
        self._tracked_objects: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        
        # Auto snapshot thread
        self._auto_snapshot_thread: Optional[threading.Thread] = None
        if auto_snapshot_interval:
            self._start_auto_snapshot()
    
    def _get_lock(self):
        """Get lock context manager or dummy."""
        if self._lock:
            return self._lock
        else:
            class DummyLock:
                def __enter__(self): pass
                def __exit__(self, *args): pass
            return DummyLock()
    
    def _start_auto_snapshot(self):
        """Start automatic snapshot thread."""
        def snapshot_loop():
            while self.auto_snapshot_interval:
                time.sleep(self.auto_snapshot_interval)
                self.capture_snapshot(StateType.GLOBAL, self.current_state.copy())
        
        self._auto_snapshot_thread = threading.Thread(
            target=snapshot_loop,
            daemon=True
        )
        self._auto_snapshot_thread.start()
    
    def track_object(self, obj: Any, name: str):
        """Track an object for state changes."""
        with self._get_lock():
            self._tracked_objects[name] = obj
            # Capture initial state
            self.update_state(name, self._get_object_state(obj))
    
    def _get_object_state(self, obj: Any) -> Any:
        """Get the current state of an object."""
        if hasattr(obj, "__dict__"):
            return vars(obj).copy()
        elif hasattr(obj, "__getstate__"):
            return obj.__getstate__()
        else:
            return obj
    
    def update_state(self, key: str, value: Any, state_type: StateType = StateType.VARIABLE):
        """Update a state value and potentially create a snapshot."""
        with self._get_lock():
            old_value = self.current_state.get(key)
            self.current_state[key] = copy.deepcopy(value)
            
            # Notify watchers
            for watcher in self.watchers.get(key, []):
                try:
                    watcher(key, old_value, value)
                except Exception:
                    pass
            
            # Check if we should create a snapshot
            if self._should_snapshot(key, old_value, value):
                self.capture_snapshot(
                    state_type,
                    {key: value},
                    metadata={"changed_key": key}
                )
    
    def _should_snapshot(self, key: str, old_value: Any, new_value: Any) -> bool:
        """Determine if a change warrants a snapshot."""
        # Always snapshot if no previous value
        if old_value is None:
            return True
        
        # Check if values are different
        try:
            return old_value != new_value
        except:
            # If comparison fails, assume they're different
            return True
    
    def capture_snapshot(
        self,
        state_type: StateType,
        data: Dict[str, Any],
        function_name: Optional[str] = None,
        line_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Capture a state snapshot."""
        with self._get_lock():
            self._snapshot_counter += 1
            snapshot_id = f"snapshot_{self._snapshot_counter}"
            
            # Serialize data using StateSnapshot's serialization method
            temp_snapshot = StateSnapshot(
                id="temp",
                timestamp=datetime.now(),
                function_name=None,
                line_number=None,
                state_type=state_type,
                data=data
            )
            serialized_data = json.loads(json.dumps(temp_snapshot.to_dict()["data"], default=str))
            
            snapshot = StateSnapshot(
                id=snapshot_id,
                timestamp=datetime.now(),
                function_name=function_name,
                line_number=line_number,
                state_type=state_type,
                data=serialized_data,
                metadata=metadata or {}
            )
            
            self.snapshots.append(snapshot)
            self.snapshot_index[snapshot_id] = snapshot
            self.timeline_position = len(self.snapshots) - 1
            
            # Check breakpoints
            if (function_name, line_number) in self.breakpoints:
                self._handle_breakpoint(snapshot)
            
            return snapshot_id
    
    def _handle_breakpoint(self, snapshot: StateSnapshot):
        """Handle a breakpoint hit."""
        # In a real implementation, this would pause execution
        # For now, we'll just record it
        snapshot.metadata["breakpoint_hit"] = True
    
    def get_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        """Get a specific snapshot by ID."""
        with self._get_lock():
            return self.snapshot_index.get(snapshot_id)
    
    def get_snapshots(
        self,
        state_type: Optional[StateType] = None,
        function_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[StateSnapshot]:
        """Get snapshots matching criteria."""
        with self._get_lock():
            snapshots = list(self.snapshots)
            
            # Filter by type
            if state_type:
                snapshots = [s for s in snapshots if s.state_type == state_type]
            
            # Filter by function
            if function_name:
                snapshots = [s for s in snapshots if s.function_name == function_name]
            
            # Filter by time range
            if start_time:
                snapshots = [s for s in snapshots if s.timestamp >= start_time]
            if end_time:
                snapshots = [s for s in snapshots if s.timestamp <= end_time]
            
            # Apply limit
            if limit:
                snapshots = snapshots[-limit:]
            
            return snapshots
    
    def diff_snapshots(self, snapshot_id1: str, snapshot_id2: str) -> List[StateDiff]:
        """Calculate differences between two snapshots."""
        if not self.enable_diffing:
            return []
        
        with self._get_lock():
            snapshot1 = self.snapshot_index.get(snapshot_id1)
            snapshot2 = self.snapshot_index.get(snapshot_id2)
            
            if not snapshot1 or not snapshot2:
                return []
            
            return self._calculate_diff(snapshot1.data, snapshot2.data)
    
    def _calculate_diff(
        self,
        data1: Dict[str, Any],
        data2: Dict[str, Any],
        path: Optional[List[str]] = None
    ) -> List[StateDiff]:
        """Calculate differences between two data dictionaries."""
        if path is None:
            path = []
        
        diffs = []
        
        # Check for removed keys
        for key in data1:
            if key not in data2:
                diffs.append(StateDiff(
                    operation=DiffOperation.REMOVE,
                    path=path + [key],
                    old_value=data1[key]
                ))
        
        # Check for added keys
        for key in data2:
            if key not in data1:
                diffs.append(StateDiff(
                    operation=DiffOperation.ADD,
                    path=path + [key],
                    new_value=data2[key]
                ))
        
        # Check for modified keys
        for key in set(data1) & set(data2):
            if isinstance(data1[key], dict) and isinstance(data2[key], dict):
                # Recursive diff for nested dicts
                nested_diffs = self._calculate_diff(
                    data1[key],
                    data2[key],
                    path + [key]
                )
                diffs.extend(nested_diffs)
            else:
                try:
                    if data1[key] != data2[key]:
                        diffs.append(StateDiff(
                            operation=DiffOperation.MODIFY,
                            path=path + [key],
                            old_value=data1[key],
                            new_value=data2[key]
                        ))
                except:
                    # If comparison fails, assume modified
                    diffs.append(StateDiff(
                        operation=DiffOperation.MODIFY,
                        path=path + [key],
                        old_value=data1[key],
                        new_value=data2[key]
                    ))
        
        return diffs
    
    def time_travel_to(self, position: Union[int, str]) -> bool:
        """Travel to a specific position in the timeline."""
        if not self.enable_time_travel:
            return False
        
        with self._get_lock():
            # Handle bookmark
            if isinstance(position, str):
                if position in self.bookmark_positions:
                    position = self.bookmark_positions[position]
                else:
                    return False
            
            # Validate position
            if not 0 <= position < len(self.snapshots):
                return False
            
            self.timeline_position = position
            
            # Restore state from snapshot
            snapshot = self.snapshots[position]
            self.current_state = copy.deepcopy(snapshot.data)
            
            return True
    
    def time_travel_forward(self, steps: int = 1) -> bool:
        """Move forward in the timeline."""
        with self._get_lock():
            new_position = self.timeline_position + steps
            return self.time_travel_to(new_position)
    
    def time_travel_backward(self, steps: int = 1) -> bool:
        """Move backward in the timeline."""
        with self._get_lock():
            new_position = self.timeline_position - steps
            return self.time_travel_to(new_position)
    
    def create_bookmark(self, name: str, position: Optional[int] = None):
        """Create a bookmark at the current or specified position."""
        with self._get_lock():
            if position is None:
                position = self.timeline_position
            
            if 0 <= position < len(self.snapshots):
                self.bookmark_positions[name] = position
    
    def add_watcher(self, key: str, callback: Callable[[str, Any, Any], None]):
        """Add a watcher for state changes."""
        with self._get_lock():
            self.watchers[key].append(callback)
    
    def remove_watcher(self, key: str, callback: Callable):
        """Remove a watcher."""
        with self._get_lock():
            if key in self.watchers and callback in self.watchers[key]:
                self.watchers[key].remove(callback)
    
    def add_breakpoint(self, function_name: Optional[str] = None, line_number: Optional[int] = None):
        """Add a breakpoint."""
        with self._get_lock():
            self.breakpoints.add((function_name, line_number))
    
    def remove_breakpoint(self, function_name: Optional[str] = None, line_number: Optional[int] = None):
        """Remove a breakpoint."""
        with self._get_lock():
            self.breakpoints.discard((function_name, line_number))
    
    def export_timeline(self, output_file: Path, format: str = "json"):
        """Export the timeline to a file."""
        with self._get_lock():
            timeline_data = {
                "name": self.name,
                "created": datetime.now().isoformat(),
                "snapshots": [s.to_dict() for s in self.snapshots],
                "bookmarks": self.bookmark_positions,
                "current_position": self.timeline_position
            }
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            if format == "json":
                with open(output_file, 'w') as f:
                    json.dump(timeline_data, f, indent=2, default=str)
            elif format == "pickle":
                with open(output_file, 'wb') as f:
                    pickle.dump(timeline_data, f)
    
    def import_timeline(self, input_file: Path):
        """Import a timeline from a file."""
        if not input_file.exists():
            raise FileNotFoundError(f"Timeline file not found: {input_file}")
        
        with self._get_lock():
            if input_file.suffix == ".json":
                with open(input_file, 'r') as f:
                    timeline_data = json.load(f)
            else:
                with open(input_file, 'rb') as f:
                    timeline_data = pickle.load(f)
            
            # Clear current data
            self.snapshots.clear()
            self.snapshot_index.clear()
            self.bookmark_positions = timeline_data.get("bookmarks", {})
            self.timeline_position = timeline_data.get("current_position", -1)
            
            # Rebuild snapshots
            for snapshot_dict in timeline_data["snapshots"]:
                snapshot = StateSnapshot(
                    id=snapshot_dict["id"],
                    timestamp=datetime.fromisoformat(snapshot_dict["timestamp"]),
                    function_name=snapshot_dict.get("function_name"),
                    line_number=snapshot_dict.get("line_number"),
                    state_type=StateType(snapshot_dict["state_type"]),
                    data=snapshot_dict["data"],
                    metadata=snapshot_dict.get("metadata", {})
                )
                self.snapshots.append(snapshot)
                self.snapshot_index[snapshot.id] = snapshot
            
            # Restore current state from last snapshot if available
            if self.snapshots and self.timeline_position >= 0:
                self.current_state = copy.deepcopy(self.snapshots[self.timeline_position].data)
    
    def get_timeline_summary(self) -> Dict[str, Any]:
        """Get a summary of the current timeline."""
        with self._get_lock():
            return {
                "total_snapshots": len(self.snapshots),
                "current_position": self.timeline_position,
                "bookmarks": list(self.bookmark_positions.keys()),
                "breakpoints": [f"{func}:{line}" if func else f"*:{line}" 
                              for func, line in self.breakpoints],
                "snapshot_types": {
                    state_type.value: sum(1 for s in self.snapshots if s.state_type == state_type)
                    for state_type in StateType
                },
                "memory_usage": sum(len(str(s.data)) for s in self.snapshots)  # Rough estimate
            }
    
    def clear(self):
        """Clear all state and snapshots."""
        with self._get_lock():
            self.snapshots.clear()
            self.snapshot_index.clear()
            self.current_state.clear()
            self.timeline_position = -1
            self.bookmark_positions.clear()
            self._snapshot_counter = 0


# Global state manager instance
_global_state_manager = StateManager(
    name="mystic.global_state",
    max_snapshots=10000,
    thread_safe=True
)


# Convenience functions
def track_state(obj: Any, name: str):
    """Track an object's state globally."""
    _global_state_manager.track_object(obj, name)


def update_state(key: str, value: Any, state_type: StateType = StateType.VARIABLE):
    """Update global state."""
    _global_state_manager.update_state(key, value, state_type)


def capture_snapshot(
    state_type: StateType = StateType.GLOBAL,
    data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
    """Capture a global state snapshot."""
    if data is None:
        data = _global_state_manager.current_state.copy()
    return _global_state_manager.capture_snapshot(state_type, data, **kwargs)


def time_travel_to(position: Union[int, str]) -> bool:
    """Travel to a position in the global timeline."""
    return _global_state_manager.time_travel_to(position)


def get_global_state_manager() -> StateManager:
    """Get the global state manager instance."""
    return _global_state_manager