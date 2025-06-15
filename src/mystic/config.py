"""
Configuration Management for Gnosis Mystic

Handles loading, saving, and managing configuration for the Mystic system.
"""

import json
import os
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MysticConfig:
    """Main configuration class for Gnosis Mystic."""

    # Core settings
    debug: bool = False
    verbose: bool = False
    project_root: Optional[str] = None
    environment: str = "development"  # development, testing, production

    # Storage settings
    data_dir: Optional[str] = None
    cache_dir: Optional[str] = None
    log_dir: Optional[str] = None

    # MCP settings
    mcp_transport: str = "stdio"
    mcp_host: str = "localhost"
    mcp_port: int = 8899

    # REPL settings
    repl_theme: str = "dark"
    repl_history: bool = True
    repl_history_file: Optional[str] = None

    # Hijacking settings
    hijacking_enabled: bool = True
    auto_discover: bool = True
    cache_enabled: bool = True
    cache_ttl: str = "1h"

    # Logging settings
    log_level: str = "INFO"
    log_format: str = "detailed"
    log_to_file: bool = True

    # Security settings
    security_enabled: bool = True
    sandbox_execution: bool = False
    allowed_modules: List[str] = None
    blocked_functions: List[str] = None

    # Performance settings
    max_cache_size: int = 1000
    performance_tracking: bool = True

    def __post_init__(self):
        """Set up default paths if not provided."""
        if not self.project_root:
            self.project_root = os.getcwd()

        if not self.data_dir:
            self.data_dir = os.path.join(self.project_root, ".mystic", "data")

        if not self.cache_dir:
            self.cache_dir = os.path.join(self.data_dir, "cache")

        if not self.log_dir:
            self.log_dir = os.path.join(self.data_dir, "logs")

        if not self.repl_history_file:
            self.repl_history_file = os.path.join(self.data_dir, ".repl_history")

        if self.allowed_modules is None:
            self.allowed_modules = []

        if self.blocked_functions is None:
            self.blocked_functions = []

        # Create directories if they don't exist
        for dir_path in [self.data_dir, self.cache_dir, self.log_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)


class Config:
    """Global configuration singleton."""

    _instance: Optional[MysticConfig] = None
    _lock = threading.RLock()
    _config_file: Optional[Path] = None

    @classmethod
    def initialize(cls, config_path: Optional[Path] = None, **kwargs) -> MysticConfig:
        """Initialize configuration from file or kwargs."""
        with cls._lock:
            if config_path:
                cls._config_file = config_path
                cls._instance = cls.load_config(config_path)
            else:
                cls._instance = MysticConfig(**kwargs)
            return cls._instance

    @classmethod
    def get_instance(cls) -> MysticConfig:
        """Get the configuration instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = MysticConfig()
            return cls._instance

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        instance = cls.get_instance()
        return getattr(instance, key, default)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Set a configuration value."""
        instance = cls.get_instance()
        if hasattr(instance, key):
            setattr(instance, key, value)

    @classmethod
    def get_environment(cls) -> str:
        """Get the current environment."""
        # Check environment variable first
        env = os.environ.get("MYSTIC_ENV", None)
        if env:
            return env

        # Fall back to config
        return cls.get("environment", "development")

    @classmethod
    def get_cache_dir(cls) -> str:
        """Get the cache directory."""
        return cls.get("cache_dir", os.path.join(os.getcwd(), ".mystic", "cache"))

    @classmethod
    def get_log_dir(cls) -> str:
        """Get the log directory."""
        return cls.get("log_dir", os.path.join(os.getcwd(), ".mystic", "logs"))

    @classmethod
    def get_data_dir(cls) -> str:
        """Get the data directory."""
        return cls.get("data_dir", os.path.join(os.getcwd(), ".mystic", "data"))

    @classmethod
    def load_config(cls, config_path: Path) -> MysticConfig:
        """Load configuration from file."""
        if config_path.exists():
            try:
                with open(config_path) as f:
                    data = json.load(f)
                return MysticConfig(**data)
            except Exception as e:
                print(f"Error loading config from {config_path}: {e}")

        return MysticConfig()

    @classmethod
    def save_config(cls, config_path: Optional[Path] = None) -> bool:
        """Save current configuration to file."""
        instance = cls.get_instance()
        path = config_path or cls._config_file

        if not path:
            path = Path(instance.data_dir) / "config.json"

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(asdict(instance), f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error saving config to {path}: {e}")
            return False

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(cls.get_instance())

    @classmethod
    def update(cls, updates: Dict[str, Any]) -> None:
        """Update multiple configuration values."""
        instance = cls.get_instance()
        for key, value in updates.items():
            if hasattr(instance, key):
                setattr(instance, key, value)


# Convenience functions to match old API
def load_config(config_path: Optional[Path] = None) -> MysticConfig:
    """Load configuration from file or use defaults."""
    return Config.initialize(config_path)


def save_config(config: MysticConfig, config_path: Path) -> bool:
    """Save configuration to file."""
    Config._instance = config
    return Config.save_config(config_path)


def get_config() -> MysticConfig:
    """Get the current configuration."""
    return Config.get_instance()
