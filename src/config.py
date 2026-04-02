"""
Configuration loader for SCA Time Automation.
Loads settings from YAML files and environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import yaml

# Global API keys (Documents/.secrets/.env)
_global_env = Path.home() / "Documents" / ".secrets" / ".env"
if _global_env.exists():
    load_dotenv(_global_env, override=False)

# Local .env (project-specific vars only)
load_dotenv(override=False)


def expand_path(path: str) -> str:
    """Expand environment variables in path."""
    return os.path.expandvars(path)


def get_project_root() -> Path:
    """Return project root directory."""
    return Path(__file__).parent.parent  # było parent.parent.parent


def load_yaml(filename: str) -> dict:
    """Load YAML config file from config/ directory."""
    config_path = get_project_root() / "config" / filename
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_settings() -> dict:
    """Load settings with path expansion."""
    settings = load_yaml("settings.yaml")

    # Expand environment variables in paths
    if "paths" in settings:
        for key, value in settings["paths"].items():
            if isinstance(value, str):
                settings["paths"][key] = os.path.expandvars(value)

    # Env var overrides for specific paths
    project_codes_env = os.environ.get("PROJECT_CODES_EXCEL")
    if project_codes_env:
        settings.setdefault("paths", {})["project_codes"] = project_codes_env

    return settings


def get_category_mapping() -> dict:
    """Load category_mapping.yaml."""
    return load_yaml("category_mapping.yaml")


def get_excluded() -> dict:
    """Load excluded.yaml."""
    return load_yaml("excluded.yaml")


def get_env(key: str, default: str = "") -> str:
    """Get environment variable."""
    return os.getenv(key, default)
