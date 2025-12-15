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
    }
}

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from a YAML file, falling back to defaults."""
    path = Path(config_path)
    config = DEFAULT_CONFIG.copy()
    
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    # Deep merge would be better, but simple update for now
                    config.update(user_config)
        except Exception as e:
            print(f"⚠️ Warning: Failed to load config file: {e}")
            
    return config
