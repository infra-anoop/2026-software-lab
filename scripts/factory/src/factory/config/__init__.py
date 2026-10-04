"""Typed configuration (the only module that reads the environment — I-A3)."""

from factory.config.settings import (
    DEFAULT_AUTONOMY_HORIZON_MINUTES,
    ConfigError,
    EnvSettings,
    Settings,
    load_env,
    load_settings,
)

__all__ = [
    "DEFAULT_AUTONOMY_HORIZON_MINUTES",
    "ConfigError",
    "EnvSettings",
    "Settings",
    "load_env",
    "load_settings",
]
