from __future__ import annotations

from pathlib import Path

# Default config location following XDG Base Directory specification
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "family-schedulekit"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "schedule.yaml"  # Changed to YAML


def get_config_path() -> Path:
    """
    Get the path to the user's config file.

    Returns the default config path: ~/.config/family-schedulekit/schedule.yaml
    Checks for both .yaml and legacy .json for backward compatibility.
    """
    # Prefer YAML, but fall back to JSON for backward compatibility
    yaml_path = DEFAULT_CONFIG_DIR / "schedule.yaml"
    json_path = DEFAULT_CONFIG_DIR / "schedule.json"

    if yaml_path.exists():
        return yaml_path
    elif json_path.exists():
        return json_path
    else:
        return DEFAULT_CONFIG_FILE  # Default to YAML for new configs


def ensure_config_dir() -> Path:
    """
    Ensure the config directory exists, creating it if necessary.

    Returns the config directory path.
    """
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_CONFIG_DIR


def config_exists() -> bool:
    """Check if a config file exists at the default location (supports both YAML and JSON)."""
    yaml_path = DEFAULT_CONFIG_DIR / "schedule.yaml"
    json_path = DEFAULT_CONFIG_DIR / "schedule.json"
    return yaml_path.exists() or json_path.exists()
