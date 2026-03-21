# src/orchestrator/__init__.py
"""
Lazy-loading public API for the orchestrator package.
Prevents model loading at import time.
"""

def send_message(*args, **kwargs):
    from .orchestrator import send_message as _impl
    return _impl(*args, **kwargs)

def send_message_streaming(*args, **kwargs):
    from .orchestrator import send_message_streaming as _impl
    return _impl(*args, **kwargs)

def reset_history():
    from .orchestrator import reset_history as _impl
    return _impl()

def get_history():
    from .history import get_history as _impl
    return _impl()

def route_model(*args, **kwargs):
    from .routing import route_model as _impl
    return _impl(*args, **kwargs)

def process_memory_pipeline(*args, **kwargs):
    from .memory_pipeline import process_memory_pipeline as _impl
    return _impl(*args, **kwargs)

def log_event(*args, **kwargs):
    from .logging import log_event as _impl
    return _impl(*args, **kwargs)

__all__ = [
    "send_message",
    "send_message_streaming",
    "reset_history",
    "get_history",
    "route_model",
    "process_memory_pipeline",
    "log_event",
]
