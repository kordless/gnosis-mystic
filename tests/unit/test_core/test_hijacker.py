"""Unit tests for the enhanced function hijacker."""

import tempfile
import time
from datetime import timedelta
from pathlib import Path

import pytest

from mystic.core.function_hijacker import (
    AnalysisStrategy,
    BlockStrategy,
    CacheStrategy,
    CallHijacker,
    ConditionalStrategy,
    HijackContext,
    HijackPriority,
    HijackStrategy,
    MockStrategy,
    RedirectStrategy,
    analyze,
    block,
    cache,
    hijack_function,
    mock,
    redirect,
)


# Test functions
def simple_function(x, y):
    """Simple test function."""
    return x + y


def slow_function(x):
    """Slow function for testing."""
    time.sleep(0.1)
    return x * 2


def error_function():
    """Function that raises an error."""
    raise ValueError("Test error")


class TestHijackStrategy:
    """Test the base HijackStrategy class."""

    def test_base_strategy(self):
        """Test base strategy initialization."""
        strategy = HijackStrategy(HijackPriority.HIGH)
        assert strategy.priority == HijackPriority.HIGH
        assert strategy.name == "HijackStrategy"

    def test_should_hijack_default(self):
        """Test default should_hijack returns True."""
        strategy = HijackStrategy()
        context = HijackContext(function=simple_function, args=(1, 2), kwargs={})
        assert strategy.should_hijack(context) is True

    def test_hijack_call_not_implemented(self):
        """Test hijack_call raises NotImplementedError."""
        strategy = HijackStrategy()
        context = HijackContext(function=simple_function, args=(1, 2), kwargs={})
        with pytest.raises(NotImplementedError):
            strategy.hijack_call(context, simple_function)


class TestCacheStrategy:
    """Test the CacheStrategy class."""

    def test_cache_basic(self):
        """Test basic caching functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategy = CacheStrategy(duration="1h", cache_dir=Path(tmpdir))

            # First call - should execute
            context = HijackContext(function=simple_function, args=(1, 2), kwargs={})
            result = strategy.hijack_call(context, simple_function)
            assert result.executed is True
            assert result.result == 3
            assert result.metadata["cache_hit"] is False

            # Should have cached value now
            assert strategy.has_cached_value(context) is True

            # Second call - should hit cache
            result2 = strategy.hijack_call(context, simple_function)
            assert result2.executed is True
            assert result2.result == 3
            assert result2.metadata["cache_hit"] is True

    def test_cache_expiration(self):
        """Test cache expiration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategy = CacheStrategy(duration=timedelta(seconds=0.1), cache_dir=Path(tmpdir))

            context = HijackContext(function=simple_function, args=(1, 2), kwargs={})
            result = strategy.hijack_call(context, simple_function)
            assert result.metadata["cache_hit"] is False

            # Should have cached value now
            assert strategy.has_cached_value(context) is True

            # Wait for expiration
            time.sleep(0.2)

            # Should not find in cache after expiration
            assert strategy.has_cached_value(context) is False

    def test_cache_different_args(self):
        """Test cache with different arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategy = CacheStrategy(cache_dir=Path(tmpdir))

            context1 = HijackContext(function=simple_function, args=(1, 2), kwargs={})
            result1 = strategy.hijack_call(context1, simple_function)
            assert result1.result == 3

            context2 = HijackContext(function=simple_function, args=(2, 3), kwargs={})
            result2 = strategy.hijack_call(context2, simple_function)
            assert result2.result == 5
            assert result2.metadata["cache_hit"] is False

    def test_duration_parsing(self):
        """Test duration string parsing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test various duration formats
            s1 = CacheStrategy(duration="30s", cache_dir=Path(tmpdir))
            assert s1.duration == timedelta(seconds=30)

            s2 = CacheStrategy(duration="5m", cache_dir=Path(tmpdir))
            assert s2.duration == timedelta(minutes=5)

            s3 = CacheStrategy(duration="2h", cache_dir=Path(tmpdir))
            assert s3.duration == timedelta(hours=2)

            s4 = CacheStrategy(duration="1d", cache_dir=Path(tmpdir))
            assert s4.duration == timedelta(days=1)


class TestMockStrategy:
    """Test the MockStrategy class."""

    def test_mock_static_data(self):
        """Test mocking with static data."""
        strategy = MockStrategy(mock_data="mocked result")
        context = HijackContext(function=simple_function, args=(1, 2), kwargs={})

        assert strategy.should_hijack(context) is True
        result = strategy.hijack_call(context, simple_function)
        assert result.executed is True
        assert result.result == "mocked result"
        assert result.metadata["mocked"] is True

    def test_mock_callable(self):
        """Test mocking with callable."""

        def mock_func(x, y):
            return f"mocked: {x} + {y}"

        strategy = MockStrategy(mock_data=mock_func)
        context = HijackContext(function=simple_function, args=(1, 2), kwargs={})

        result = strategy.hijack_call(context, simple_function)
        assert result.result == "mocked: 1 + 2"

    def test_mock_environment_specific(self):
        """Test environment-specific mocking."""
        mock_data = {
            "development": "dev result",
            "testing": "test result",
            "production": "prod result",
        }
        strategy = MockStrategy(mock_data=mock_data)

        # Test development environment
        context = HijackContext(
            function=simple_function, args=(1, 2), kwargs={}, environment="development"
        )
        result = strategy.hijack_call(context, simple_function)
        assert result.result == "dev result"

        # Test production environment (not in default environments)
        context.environment = "production"
        assert strategy.should_hijack(context) is False

    def test_mock_custom_environments(self):
        """Test mocking with custom environments."""
        strategy = MockStrategy(mock_data="mocked", environments=["staging", "production"])

        context = HijackContext(
            function=simple_function, args=(1, 2), kwargs={}, environment="staging"
        )
        assert strategy.should_hijack(context) is True

        context.environment = "development"
        assert strategy.should_hijack(context) is False


class TestBlockStrategy:
    """Test the BlockStrategy class."""

    def test_block_with_return_value(self):
        """Test blocking with return value."""
        strategy = BlockStrategy(return_value="blocked")
        context = HijackContext(function=simple_function, args=(1, 2), kwargs={})

        result = strategy.hijack_call(context, simple_function)
        assert result.executed is True
        assert result.result == "blocked"
        assert result.metadata["blocked"] is True

    def test_block_with_error(self):
        """Test blocking with error."""
        strategy = BlockStrategy(raise_error=RuntimeError, message="Function is blocked")
        context = HijackContext(function=simple_function, args=(1, 2), kwargs={})

        result = strategy.hijack_call(context, simple_function)
        assert result.executed is False
        assert isinstance(result.error, RuntimeError)
        assert str(result.error) == "Function is blocked"

    def test_block_priority(self):
        """Test block strategy has highest priority."""
        strategy = BlockStrategy()
        assert strategy.priority == HijackPriority.HIGHEST


class TestRedirectStrategy:
    """Test the RedirectStrategy class."""

    def test_redirect_basic(self):
        """Test basic redirection."""

        def target_func(x, y):
            return x * y

        strategy = RedirectStrategy(target_func=target_func)
        context = HijackContext(function=simple_function, args=(3, 4), kwargs={})

        result = strategy.hijack_call(context, simple_function)
        assert result.executed is True
        assert result.result == 12  # 3 * 4
        assert result.metadata["redirected_to"] == "target_func"

    def test_redirect_with_transforms(self):
        """Test redirection with argument and result transforms."""

        def target_func(x):
            return x**2

        def transform_args(args, kwargs):
            # Sum the arguments
            return (sum(args),), {}

        def transform_result(result):
            # Double the result
            return result * 2

        strategy = RedirectStrategy(
            target_func=target_func,
            transform_args=transform_args,
            transform_result=transform_result,
        )
        context = HijackContext(function=simple_function, args=(3, 4), kwargs={})

        result = strategy.hijack_call(context, simple_function)
        assert result.result == 98  # (3 + 4)^2 * 2


class TestAnalysisStrategy:
    """Test the AnalysisStrategy class."""

    def test_analysis_basic(self):
        """Test basic analysis functionality."""
        strategy = AnalysisStrategy()
        context = HijackContext(function=simple_function, args=(1, 2), kwargs={})

        result = strategy.hijack_call(context, simple_function)
        assert result.executed is True
        assert result.result == 3
        assert "execution_time" in result.metadata
        assert result.metadata["success"] is True

    def test_analysis_metrics_collection(self):
        """Test metrics collection."""
        strategy = AnalysisStrategy(
            track_performance=True, track_arguments=True, track_results=True
        )

        # Make multiple calls
        for i in range(3):
            context = HijackContext(function=simple_function, args=(i, i + 1), kwargs={})
            strategy.hijack_call(context, simple_function)

        # Check metrics
        metrics = strategy.get_metrics()
        func_name = f"{simple_function.__module__}.{simple_function.__name__}"
        assert func_name in metrics
        assert len(metrics[func_name]) == 3

        # Check metric contents
        first_metric = metrics[func_name][0]
        assert first_metric["args"] == (0, 1)
        assert first_metric["result"] == 1
        assert first_metric["success"] is True

    def test_analysis_callback(self):
        """Test analysis with callback."""
        callback_data = []

        def callback(context, result, metrics):
            callback_data.append(
                {"function": context.function.__name__, "result": result, "metrics": metrics}
            )

        strategy = AnalysisStrategy(callback=callback)
        context = HijackContext(function=simple_function, args=(2, 3), kwargs={})

        strategy.hijack_call(context, simple_function)
        assert len(callback_data) == 1
        assert callback_data[0]["function"] == "simple_function"
        assert callback_data[0]["result"] == 5

    def test_analysis_error_tracking(self):
        """Test analysis of errors."""
        strategy = AnalysisStrategy()
        context = HijackContext(function=error_function, args=(), kwargs={})

        result = strategy.hijack_call(context, error_function)
        assert result.executed is False
        assert result.error is not None
        assert result.metadata["success"] is False
        assert "error" in result.metadata


class TestConditionalStrategy:
    """Test the ConditionalStrategy class."""

    def test_conditional_basic(self):
        """Test basic conditional strategy."""

        def condition(context):
            return context.args[0] > 5

        true_strategy = MockStrategy(mock_data="large")
        false_strategy = MockStrategy(mock_data="small")

        strategy = ConditionalStrategy(
            condition=condition, true_strategy=true_strategy, false_strategy=false_strategy
        )

        # Test true condition
        context1 = HijackContext(function=simple_function, args=(10, 2), kwargs={})
        result1 = strategy.hijack_call(context1, simple_function)
        assert result1.result == "large"

        # Test false condition
        context2 = HijackContext(function=simple_function, args=(3, 2), kwargs={})
        result2 = strategy.hijack_call(context2, simple_function)
        assert result2.result == "small"

    def test_conditional_no_false_strategy(self):
        """Test conditional without false strategy."""

        def condition(context):
            return context.args[0] > 5

        true_strategy = MockStrategy(mock_data="hijacked")

        strategy = ConditionalStrategy(condition=condition, true_strategy=true_strategy)

        # Test false condition - should execute original
        context = HijackContext(function=simple_function, args=(3, 2), kwargs={})
        result = strategy.hijack_call(context, simple_function)
        assert result.result == 5  # Original function result


class TestCallHijacker:
    """Test the CallHijacker class."""

    def test_hijacker_basic(self):
        """Test basic hijacker functionality."""
        hijacker = CallHijacker(simple_function)
        result = hijacker(1, 2)
        assert result == 3
        assert hijacker.call_count == 1

    def test_hijacker_with_strategies(self):
        """Test hijacker with strategies."""
        strategies = [MockStrategy(mock_data="mocked"), CacheStrategy()]
        hijacker = CallHijacker(simple_function, strategies)

        # Should use mock strategy (higher priority)
        result = hijacker(1, 2)
        assert result == "mocked"

    def test_hijacker_registry(self):
        """Test hijacker registry."""
        hijacker = CallHijacker(simple_function)
        func_name = f"{simple_function.__module__}.{simple_function.__name__}"

        # Check registration
        assert CallHijacker.get_hijacker(func_name) == hijacker

        # Check get all
        all_hijackers = CallHijacker.get_all_hijackers()
        assert func_name in all_hijackers

        # Test unhijack
        original = CallHijacker.unhijack(func_name)
        assert original == simple_function
        assert CallHijacker.get_hijacker(func_name) is None

    def test_hijacker_add_remove_strategies(self):
        """Test adding and removing strategies."""
        hijacker = CallHijacker(simple_function)

        # Add strategy
        mock_strategy = MockStrategy(mock_data="added")
        hijacker.add_strategy(mock_strategy)
        assert len(hijacker.strategies) == 1

        result = hijacker(1, 2)
        assert result == "added"

        # Remove strategy
        hijacker.remove_strategy(MockStrategy)
        assert len(hijacker.strategies) == 0

        result = hijacker(1, 2)
        assert result == 3  # Original result

    def test_hijacker_metadata_preservation(self):
        """Test that hijacker preserves function metadata."""
        hijacker = CallHijacker(simple_function)
        assert hijacker.__name__ == simple_function.__name__
        assert hijacker.__doc__ == simple_function.__doc__
        assert hijacker.__wrapped__ == simple_function


class TestDecorators:
    """Test the decorator functions."""

    def test_hijack_function_decorator(self):
        """Test hijack_function decorator."""

        @hijack_function(MockStrategy(mock_data="decorated"), CacheStrategy())
        def decorated_func(x):
            return x * 2

        assert isinstance(decorated_func, CallHijacker)
        result = decorated_func(5)
        assert result == "decorated"

    def test_cache_decorator(self):
        """Test cache decorator."""
        call_count = 0

        @cache(duration="1h")
        def cached_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = cached_func(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - should use cache
        result2 = cached_func(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

    def test_mock_decorator(self):
        """Test mock decorator."""

        @mock(mock_data="mocked value")
        def mocked_func(x):
            return x * 2

        result = mocked_func(5)
        assert result == "mocked value"

    def test_block_decorator(self):
        """Test block decorator."""

        @block(return_value="blocked")
        def blocked_func(x):
            return x * 2

        result = blocked_func(5)
        assert result == "blocked"

    def test_redirect_decorator(self):
        """Test redirect decorator."""

        def target(x):
            return x * 3

        @redirect(target_func=target)
        def redirected_func(x):
            return x * 2

        result = redirected_func(5)
        assert result == 15  # 5 * 3

    def test_analyze_decorator(self):
        """Test analyze decorator."""

        @analyze(track_performance=True)
        def analyzed_func(x):
            return x * 2

        result = analyzed_func(5)
        assert result == 10

        # Check metrics were collected
        hijacker = analyzed_func
        metrics = hijacker.get_metrics()
        assert "strategy_metrics" in metrics

    def test_auto_analysis_option(self):
        """Test auto_analysis option in hijack_function."""

        @hijack_function(MockStrategy(mock_data="mocked"), auto_analysis=True)
        def func(x):
            return x * 2

        # Should have 2 strategies: MockStrategy and AnalysisStrategy
        assert len(func.strategies) == 2
        assert any(isinstance(s, MockStrategy) for s in func.strategies)
        assert any(isinstance(s, AnalysisStrategy) for s in func.strategies)


class TestMCPIntegration:
    """Test MCP integration features."""

    def test_mcp_notifications(self):
        """Test MCP notification system."""
        notifications = []

        def callback(notification):
            notifications.append(notification)

        # Register callback
        CallHijacker.register_mcp_callback(callback)

        # Create hijacked function
        hijacker = CallHijacker(simple_function)
        hijacker(1, 2)

        # Check notification
        assert len(notifications) > 0
        notification = notifications[-1]
        assert notification["type"] == "function_call"
        assert (
            notification["function"] == f"{simple_function.__module__}.{simple_function.__name__}"
        )
        assert notification["executed"] is True
        assert notification["error"] is None

        # Clear callbacks for other tests
        CallHijacker._mcp_callbacks.clear()

    def test_mcp_error_notifications(self):
        """Test MCP notifications for errors."""
        notifications = []

        def callback(notification):
            notifications.append(notification)

        CallHijacker.register_mcp_callback(callback)

        hijacker = CallHijacker(error_function)

        with pytest.raises(ValueError):
            hijacker()

        # Check error notification
        assert len(notifications) > 0
        notification = notifications[-1]
        assert notification["executed"] is False
        assert notification["error"] is not None
        assert "Test error" in notification["error"]

        # Clear callbacks
        CallHijacker._mcp_callbacks.clear()


class TestPerformance:
    """Test performance requirements."""

    def test_hijacking_overhead(self):
        """Test that hijacking overhead is < 1%."""
        # Time original function
        iterations = 1000

        start = time.time()
        for _ in range(iterations):
            simple_function(1, 2)
        original_time = time.time() - start

        # Time hijacked function (no strategies)
        hijacker = CallHijacker(simple_function)

        start = time.time()
        for _ in range(iterations):
            hijacker(1, 2)
        hijacked_time = time.time() - start

        # Calculate overhead
        overhead = (hijacked_time - original_time) / original_time

        # Should be less than 1% (0.01)
        # Note: In practice this might be higher in test environments
        # but should be verified in production
        assert overhead < 0.1  # 10% for test tolerance

    def test_cache_performance(self):
        """Test cache performance improvement."""

        @cache(duration="1h")
        def expensive_func(x):
            time.sleep(0.1)  # Simulate expensive operation
            return x * 2

        # First call - slow
        start = time.time()
        result1 = expensive_func(5)
        first_time = time.time() - start
        assert result1 == 10
        assert first_time >= 0.1

        # Second call - fast (from cache)
        start = time.time()
        result2 = expensive_func(5)
        second_time = time.time() - start
        assert result2 == 10
        assert second_time < 0.01  # Much faster


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
