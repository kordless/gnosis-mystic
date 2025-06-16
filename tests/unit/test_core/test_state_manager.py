"""Unit tests for the enhanced state manager."""

import json
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mystic.core.state_manager import (
    DiffOperation,
    StateManager,
    StateSnapshot,
    StateType,
    StateDiff,
    capture_snapshot,
    get_global_state_manager,
    time_travel_to,
    track_state,
    update_state,
)


# Test classes for object tracking
class TestObject:
    """Test object for state tracking."""
    
    def __init__(self, value):
        self.value = value
        self.counter = 0
    
    def increment(self):
        self.counter += 1


class TestStateSnapshot:
    """Test StateSnapshot functionality."""
    
    def test_initialization(self):
        """Test snapshot initialization."""
        snapshot = StateSnapshot(
            id="test_1",
            timestamp=datetime.now(),
            function_name="test_func",
            line_number=42,
            state_type=StateType.VARIABLE,
            data={"x": 1, "y": 2}
        )
        
        assert snapshot.id == "test_1"
        assert snapshot.function_name == "test_func"
        assert snapshot.line_number == 42
        assert snapshot.state_type == StateType.VARIABLE
        assert snapshot.data == {"x": 1, "y": 2}
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        timestamp = datetime.now()
        snapshot = StateSnapshot(
            id="test_1",
            timestamp=timestamp,
            function_name="test_func",
            line_number=42,
            state_type=StateType.FUNCTION_ARGS,
            data={"arg1": "value1"},
            metadata={"key": "value"}
        )
        
        result = snapshot.to_dict()
        
        assert result["id"] == "test_1"
        assert result["timestamp"] == timestamp.isoformat()
        assert result["function_name"] == "test_func"
        assert result["line_number"] == 42
        assert result["state_type"] == "function_args"
        assert result["data"] == {"arg1": "value1"}
        assert result["metadata"] == {"key": "value"}
    
    def test_serialize_data(self):
        """Test data serialization."""
        obj = TestObject(42)
        snapshot = StateSnapshot(
            id="test_1",
            timestamp=datetime.now(),
            function_name=None,
            line_number=None,
            state_type=StateType.VARIABLE,
            data={"obj": obj, "list": [1, 2, 3], "dict": {"a": 1}}
        )
        
        result = snapshot.to_dict()
        
        # Check object serialization
        assert "__class__" in result["data"]["obj"]
        assert "__dict__" in result["data"]["obj"]
        assert result["data"]["obj"]["__dict__"]["value"] == 42
        
        # Check list and dict serialization
        assert result["data"]["list"] == [1, 2, 3]
        assert result["data"]["dict"] == {"a": 1}


class TestStateDiff:
    """Test StateDiff functionality."""
    
    def test_initialization(self):
        """Test diff initialization."""
        diff = StateDiff(
            operation=DiffOperation.MODIFY,
            path=["obj", "value"],
            old_value=1,
            new_value=2
        )
        
        assert diff.operation == DiffOperation.MODIFY
        assert diff.path == ["obj", "value"]
        assert diff.old_value == 1
        assert diff.new_value == 2
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        diff = StateDiff(
            operation=DiffOperation.ADD,
            path=["new", "key"],
            new_value="value"
        )
        
        result = diff.to_dict()
        
        assert result["operation"] == "add"
        assert result["path"] == "new.key"
        assert result["new_value"] == "value"
        assert result["old_value"] is None


class TestStateManager:
    """Test the main StateManager class."""
    
    def test_initialization(self):
        """Test state manager initialization."""
        manager = StateManager(
            name="test_manager",
            max_snapshots=100,
            enable_time_travel=True,
            enable_diffing=True,
            thread_safe=True
        )
        
        assert manager.name == "test_manager"
        assert manager.max_snapshots == 100
        assert manager.enable_time_travel is True
        assert manager.enable_diffing is True
        assert len(manager.snapshots) == 0
    
    def test_update_state(self):
        """Test state updates."""
        manager = StateManager()
        
        # Update state
        manager.update_state("x", 10)
        assert manager.current_state["x"] == 10
        
        # Update again
        manager.update_state("x", 20)
        assert manager.current_state["x"] == 20
        
        # Check snapshots were created
        assert len(manager.snapshots) >= 1
    
    def test_capture_snapshot(self):
        """Test manual snapshot capture."""
        manager = StateManager()
        
        # Capture snapshot
        snapshot_id = manager.capture_snapshot(
            StateType.FUNCTION_ARGS,
            {"arg1": "value1", "arg2": 42},
            function_name="test_func",
            line_number=10
        )
        
        assert snapshot_id.startswith("snapshot_")
        
        # Retrieve snapshot
        snapshot = manager.get_snapshot(snapshot_id)
        assert snapshot is not None
        assert snapshot.state_type == StateType.FUNCTION_ARGS
        assert snapshot.data == {"arg1": "value1", "arg2": 42}
        assert snapshot.function_name == "test_func"
        assert snapshot.line_number == 10
    
    def test_track_object(self):
        """Test object tracking."""
        manager = StateManager()
        obj = TestObject(100)
        
        # Track object
        manager.track_object(obj, "test_obj")
        
        # Check initial state captured
        assert "test_obj" in manager.current_state
        assert manager.current_state["test_obj"]["value"] == 100
        assert manager.current_state["test_obj"]["counter"] == 0
        
        # Modify object and update
        obj.increment()
        manager.update_state("test_obj", manager._get_object_state(obj))
        
        # Check updated state
        assert manager.current_state["test_obj"]["counter"] == 1
    
    def test_get_snapshots_filtering(self):
        """Test snapshot filtering."""
        manager = StateManager()
        
        # Create various snapshots
        manager.capture_snapshot(StateType.VARIABLE, {"x": 1})
        time.sleep(0.01)
        manager.capture_snapshot(StateType.FUNCTION_ARGS, {"args": [1, 2]}, function_name="func1")
        time.sleep(0.01)
        manager.capture_snapshot(StateType.FUNCTION_RETURN, {"result": 3}, function_name="func1")
        time.sleep(0.01)
        manager.capture_snapshot(StateType.VARIABLE, {"y": 2})
        
        # Filter by type
        variable_snapshots = manager.get_snapshots(state_type=StateType.VARIABLE)
        assert len(variable_snapshots) == 2
        
        # Filter by function
        func_snapshots = manager.get_snapshots(function_name="func1")
        assert len(func_snapshots) == 2
        
        # Filter with limit
        limited_snapshots = manager.get_snapshots(limit=2)
        assert len(limited_snapshots) == 2
    
    def test_diff_snapshots(self):
        """Test snapshot diffing."""
        manager = StateManager()
        
        # Create two snapshots
        id1 = manager.capture_snapshot(StateType.VARIABLE, {"x": 1, "y": 2, "z": 3})
        id2 = manager.capture_snapshot(StateType.VARIABLE, {"x": 1, "y": 5, "w": 4})
        
        # Calculate diff
        diffs = manager.diff_snapshots(id1, id2)
        
        # Check diffs
        diff_ops = {d.operation for d in diffs}
        assert DiffOperation.REMOVE in diff_ops  # z removed
        assert DiffOperation.ADD in diff_ops     # w added
        assert DiffOperation.MODIFY in diff_ops  # y modified
        
        # Check specific diffs
        modify_diff = next(d for d in diffs if d.operation == DiffOperation.MODIFY)
        assert modify_diff.path == ["y"]
        assert modify_diff.old_value == 2
        assert modify_diff.new_value == 5
    
    def test_time_travel(self):
        """Test time travel functionality."""
        manager = StateManager()
        
        # Create timeline
        manager.update_state("x", 1)
        manager.update_state("x", 2)
        manager.update_state("x", 3)
        
        # Travel backward
        assert manager.time_travel_backward(1)
        assert manager.current_state["x"] == 2
        
        # Travel to specific position
        assert manager.time_travel_to(0)
        assert manager.current_state["x"] == 1
        
        # Travel forward
        assert manager.time_travel_forward(2)
        assert manager.current_state["x"] == 3
    
    def test_bookmarks(self):
        """Test bookmark functionality."""
        manager = StateManager()
        
        # Create timeline
        manager.update_state("x", 1)
        manager.create_bookmark("start")
        
        manager.update_state("x", 2)
        manager.update_state("x", 3)
        manager.create_bookmark("end")
        
        # Travel to bookmarks
        assert manager.time_travel_to("start")
        assert manager.current_state["x"] == 1
        
        assert manager.time_travel_to("end")
        assert manager.current_state["x"] == 3
    
    def test_watchers(self):
        """Test state watchers."""
        manager = StateManager()
        changes = []
        
        def watcher(key, old_value, new_value):
            changes.append((key, old_value, new_value))
        
        # Add watcher
        manager.add_watcher("x", watcher)
        
        # Update state
        manager.update_state("x", 10)
        manager.update_state("x", 20)
        
        # Check watcher was called
        assert len(changes) == 2
        assert changes[0] == ("x", None, 10)
        assert changes[1] == ("x", 10, 20)
        
        # Remove watcher
        manager.remove_watcher("x", watcher)
        manager.update_state("x", 30)
        
        # Watcher should not be called
        assert len(changes) == 2
    
    def test_breakpoints(self):
        """Test breakpoint functionality."""
        manager = StateManager()
        
        # Add breakpoint
        manager.add_breakpoint("test_func", 42)
        
        # Capture snapshot at breakpoint
        snapshot_id = manager.capture_snapshot(
            StateType.LOCAL,
            {"local_var": 123},
            function_name="test_func",
            line_number=42
        )
        
        # Check breakpoint was hit
        snapshot = manager.get_snapshot(snapshot_id)
        assert snapshot.metadata.get("breakpoint_hit") is True
        
        # Remove breakpoint
        manager.remove_breakpoint("test_func", 42)
        
        # New snapshot should not hit breakpoint
        snapshot_id2 = manager.capture_snapshot(
            StateType.LOCAL,
            {"local_var": 456},
            function_name="test_func",
            line_number=42
        )
        
        snapshot2 = manager.get_snapshot(snapshot_id2)
        assert snapshot2.metadata.get("breakpoint_hit") is None
    
    def test_export_import_timeline(self):
        """Test timeline export and import."""
        manager = StateManager()
        
        # Create some state
        manager.update_state("x", 1)
        manager.create_bookmark("checkpoint")
        manager.update_state("x", 2)
        manager.add_breakpoint("func", 10)
        
        # Export timeline
        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = Path(tmpdir) / "timeline.json"
            manager.export_timeline(export_file)
            
            # Create new manager and import
            new_manager = StateManager()
            new_manager.import_timeline(export_file)
            
            # Check imported data
            assert len(new_manager.snapshots) == len(manager.snapshots)
            assert "checkpoint" in new_manager.bookmark_positions
            assert new_manager.current_state == manager.current_state
    
    def test_timeline_summary(self):
        """Test timeline summary generation."""
        manager = StateManager()
        
        # Create diverse timeline
        manager.capture_snapshot(StateType.VARIABLE, {"x": 1})
        manager.capture_snapshot(StateType.FUNCTION_ARGS, {"args": [1, 2]})
        manager.capture_snapshot(StateType.EXCEPTION, {"error": "test"})
        manager.create_bookmark("test_bookmark")
        manager.add_breakpoint("func", 10)
        
        # Get summary
        summary = manager.get_timeline_summary()
        
        assert summary["total_snapshots"] == 3
        assert "test_bookmark" in summary["bookmarks"]
        assert "func:10" in summary["breakpoints"]
        assert summary["snapshot_types"]["variable"] == 1
        assert summary["snapshot_types"]["function_args"] == 1
        assert summary["snapshot_types"]["exception"] == 1
        assert summary["memory_usage"] > 0
    
    def test_clear(self):
        """Test clearing state manager."""
        manager = StateManager()
        
        # Add some data
        manager.update_state("x", 1)
        manager.create_bookmark("bookmark")
        manager.add_breakpoint("func", 10)
        
        # Clear
        manager.clear()
        
        # Check everything is cleared
        assert len(manager.snapshots) == 0
        assert len(manager.current_state) == 0
        assert len(manager.bookmark_positions) == 0
        assert manager.timeline_position == -1
    
    def test_max_snapshots_limit(self):
        """Test that max_snapshots is respected."""
        manager = StateManager(max_snapshots=5)
        
        # Create more snapshots than limit
        for i in range(10):
            manager.capture_snapshot(StateType.VARIABLE, {"i": i})
        
        # Should only keep last 5
        assert len(manager.snapshots) == 5
        
        # Check we have the latest ones
        first_snapshot = manager.snapshots[0]
        assert first_snapshot.data["i"] == 5  # Oldest should be i=5
    
    def test_thread_safety(self):
        """Test thread-safe operations."""
        import threading
        
        manager = StateManager(thread_safe=True)
        results = []
        
        def update_thread(thread_id):
            for i in range(10):
                manager.update_state(f"thread_{thread_id}", i)
                time.sleep(0.001)
            results.append(thread_id)
        
        # Run multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=update_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check all threads completed
        assert len(results) == 5
        
        # Check state contains all thread data
        for i in range(5):
            assert f"thread_{i}" in manager.current_state


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def test_track_state_global(self):
        """Test global state tracking."""
        obj = TestObject(42)
        track_state(obj, "global_obj")
        
        manager = get_global_state_manager()
        assert "global_obj" in manager.current_state
        assert manager.current_state["global_obj"]["value"] == 42
    
    def test_update_state_global(self):
        """Test global state update."""
        update_state("global_x", 100)
        
        manager = get_global_state_manager()
        assert manager.current_state["global_x"] == 100
    
    def test_capture_snapshot_global(self):
        """Test global snapshot capture."""
        snapshot_id = capture_snapshot(
            StateType.GLOBAL,
            {"test": "data"}
        )
        
        manager = get_global_state_manager()
        snapshot = manager.get_snapshot(snapshot_id)
        assert snapshot is not None
        assert snapshot.data == {"test": "data"}
    
    def test_time_travel_global(self):
        """Test global time travel."""
        manager = get_global_state_manager()
        initial_position = manager.timeline_position
        
        # Create some snapshots
        update_state("travel_test", 1)
        update_state("travel_test", 2)
        
        # Travel back
        success = time_travel_to(initial_position + 1)
        assert success
        assert manager.current_state["travel_test"] == 1


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_invalid_snapshot_id(self):
        """Test handling of invalid snapshot IDs."""
        manager = StateManager()
        
        snapshot = manager.get_snapshot("invalid_id")
        assert snapshot is None
        
        diffs = manager.diff_snapshots("invalid_id1", "invalid_id2")
        assert diffs == []
    
    def test_time_travel_bounds(self):
        """Test time travel boundary conditions."""
        manager = StateManager()
        
        # Travel to invalid positions
        assert not manager.time_travel_to(-1)
        assert not manager.time_travel_to(100)
        
        # Travel with no snapshots
        assert not manager.time_travel_forward()
        assert not manager.time_travel_backward()
    
    def test_watcher_exceptions(self):
        """Test that watcher exceptions don't break updates."""
        manager = StateManager()
        
        def bad_watcher(key, old, new):
            raise ValueError("Watcher error")
        
        manager.add_watcher("x", bad_watcher)
        
        # Update should still work
        manager.update_state("x", 10)
        assert manager.current_state["x"] == 10
    
    def test_non_serializable_data(self):
        """Test handling of non-serializable data."""
        manager = StateManager()
        
        # Create a non-serializable object
        class NonSerializable:
            def __repr__(self):
                return "<NonSerializable>"
        
        obj = NonSerializable()
        
        # Should handle gracefully
        snapshot_id = manager.capture_snapshot(
            StateType.VARIABLE,
            {"obj": obj}
        )
        
        snapshot = manager.get_snapshot(snapshot_id)
        # The object should be serialized as a dict with class info
        assert "__class__" in snapshot.data["obj"]
        assert "NonSerializable" in snapshot.data["obj"]["__class__"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])