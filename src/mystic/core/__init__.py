"""
Core functionality package for Gnosis Mystic.

This package contains the core function hijacking, logging, and introspection
capabilities that form the foundation of the Mystic debugging system.
"""

from .function_hijacker import *
from .function_inspector import *
from .function_logger import *

__version__ = "0.1.0"
