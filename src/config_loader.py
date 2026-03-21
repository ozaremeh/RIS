# src/config_loader.py

import yaml
from pathlib import Path

class Config:
    def __init__(self, data: dict):
        self.projects = data["projects"]
        self.thresholds = data["thresholds"]
        self.weights = data["weights"]
        self.retrieval = data["retrieval"]
        self.model = data["model"]

def load_config(path: str = "config.yaml") -> Config:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    return Config(data)

