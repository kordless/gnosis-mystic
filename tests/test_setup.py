"""Test to verify pytest setup is working correctly in WSL."""


def test_basic_setup():
    """Verify basic test setup works."""
    assert True


def test_import_mystic():
    """Verify we can import the mystic module."""
    import mystic

    assert mystic is not None


def test_python_version():
    """Verify Python version is 3.8+."""
    import sys

    assert sys.version_info >= (3, 8)
