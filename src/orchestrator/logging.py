# src/orchestrator/logging.py
"""
Centralized logging utilities for the orchestrator subsystem.
"""

import datetime
from typing import Dict


def log_event(event: str, data: Dict = None) -> None:
    """
    Standardized logging for all orchestrator modules.
    """
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    print(f"[ORCH {timestamp}] {event}")

    if data:
        for key, value in data.items():
            print(f"    {key}: {value}")
