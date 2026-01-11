import yaml
from pathlib import Path
from typing import Dict, Any

DEFAULT_CONFIG = {
    "comments": {
        "top_n": 80,
        "max_download": 20000
    },
    "output": {
        "format": "txt",
        "dir": "."
    },
    "processing": {
        "sentiment": True,
        "keywords": True
    },
    "runtime": {
        "workers": 4,
        "log_level": "INFO"
    }
}


def _deep_merge(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from a YAML file, falling back to defaults."""
    path = Path(config_path)
    config = dict(DEFAULT_CONFIG)

    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f)
                if isinstance(user_config, dict):
                    config = _deep_merge(config, user_config)
        except Exception as e:
            print(f"⚠️ Warning: Failed to load config file: {e}")

    return config

