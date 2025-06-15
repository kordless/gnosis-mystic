"""Test fixtures for Gnosis Mystic tests."""

import pytest

from mystic import MysticConfig


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return MysticConfig(debug=True, verbose=True, hijacking_enabled=True)


@pytest.fixture
def sample_function():
    """Sample function for testing hijacking and logging."""

    def test_function(x: int, y: int = 10) -> int:
        """A simple test function."""
        return x + y

    return test_function


@pytest.fixture
def complex_function():
    """More complex function for advanced testing."""

    def complex_test_function(data: dict, transform: bool = True) -> dict:
        """A more complex test function with dict arguments."""
        if transform:
            return {k: v * 2 for k, v in data.items()}
        return data.copy()

    return complex_test_function
