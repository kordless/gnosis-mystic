"""
Gnosis Mystic - Advanced Python Function Debugging with MCP Integration

A comprehensive Python function debugging and introspection system that combines
function hijacking, logging, and real-time monitoring with MCP (Model Context Protocol)
integration for AI assistants.
"""

__version__ = "0.1.0"
__author__ = "Gnosis Team"
__email__ = "team@gnosis.dev"
__license__ = "Apache-2.0"

# Core public API
# Configuration
from .config import MysticConfig, load_config, save_config
from .core.function_hijacker import (
    AnalysisStrategy,
    BlockStrategy,
    CacheStrategy,
    ConditionalStrategy,
    HijackStrategy,
    MockStrategy,
    RedirectStrategy,
    hijack_function,
)
from .core.function_inspector import (
    FunctionInspector,
    get_function_schema,
    get_function_signature,
    inspect_function,
)
from .core.function_logger import (
    FunctionLogger,
    detailed_log,
    filtered_log,
    log_calls_and_returns,
    log_calls_only,
    log_returns_only,
)

# Main decorators (convenience imports)
hijack = hijack_function
log = log_calls_and_returns
inspect = inspect_function

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    # Core functionality
    "hijack_function",
    "hijack",
    "HijackStrategy",
    "CacheStrategy",
    "MockStrategy",
    "BlockStrategy",
    "RedirectStrategy",
    "AnalysisStrategy",
    "ConditionalStrategy",
    # Logging
    "log_calls_and_returns",
    "log",
    "log_calls_only",
    "log_returns_only",
    "detailed_log",
    "filtered_log",
    "FunctionLogger",
    # Inspection
    "inspect_function",
    "inspect",
    "get_function_signature",
    "get_function_schema",
    "FunctionInspector",
    # Configuration
    "MysticConfig",
    "load_config",
    "save_config",
]
