from __future__ import annotations

from pathlib import Path

# Default config location following XDG Base Directory specification
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "family-schedulekit"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "schedule.json"


def get_config_path() -> Path:
    """
    Get the path to the user's config file.

    Returns the default config path: ~/.config/family-schedulekit/schedule.json
    """
    return DEFAULT_CONFIG_FILE


def ensure_config_dir() -> Path:
    """
    Ensure the config directory exists, creating it if necessary.

    Returns the config directory path.
    """
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_CONFIG_DIR


def config_exists() -> bool:
    """Check if a config file exists at the default location."""
    return DEFAULT_CONFIG_FILE.exists()
