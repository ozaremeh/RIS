# core/src/llama_server_manager.py

import subprocess
import socket
import time
from typing import Optional
import requests
import psutil

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

LLAMA_SERVER_BIN = "/Users/ozare/llama.cpp/build/bin/llama-server"
LLAMA_MODEL_PATH = "/Users/ozare/llama.cpp/models/qwen2-72b-instruct-q4_k_s.gguf"
LLAMA_SERVER_PORT = 8080
LLAMA_SERVER_HOST = "127.0.0.1"

# Keep a handle so we don't launch multiple servers
_llama_server_process: Optional[subprocess.Popen] = None


# ------------------------------------------------------------
# Basic port check
# ------------------------------------------------------------

def is_server_running(host: str = LLAMA_SERVER_HOST, port: int = LLAMA_SERVER_PORT) -> bool:
    """Return True if something is listening on host:port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        try:
            sock.connect((host, port))
            return True
        except OSError:
            return False


# ------------------------------------------------------------
# Readiness check (server may open port before model is ready)
# ------------------------------------------------------------

def _server_is_ready() -> bool:
    """
    Check if llama.cpp server is ready to accept chat completions.
    The server opens the port BEFORE the model is loaded, so we must
    test an actual /v1/chat/completions call.
    """
    try:
        r = requests.post(
            f"http://{LLAMA_SERVER_HOST}:{LLAMA_SERVER_PORT}/v1/chat/completions",
            json={
                "model": "test",
                "messages": [{"role": "user", "content": "ping"}],
                "stream": False,
            },
            timeout=1.0,
        )
        return r.status_code == 200
    except Exception:
        return False


# ------------------------------------------------------------
# Launch server if needed
# ------------------------------------------------------------

def launch_llama_server_if_needed() -> None:
    """
    Launch the llama.cpp server if it's not already running.
    Wait until the server is actually READY (not just port-open).
    """
    global _llama_server_process

    # If server is already running AND ready, nothing to do
    if is_server_running() and _server_is_ready():
        return

    # If process exists but died, clear it
    if _llama_server_process is not None and _llama_server_process.poll() is not None:
        _llama_server_process = None

    # Launch if not running
    if _llama_server_process is None:
        cmd = [
            LLAMA_SERVER_BIN,
            "-m", LLAMA_MODEL_PATH,
            "-c", "4096",
            "-ngl", "100",
            "--port", str(LLAMA_SERVER_PORT),
        ]

        try:
            _llama_server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            print(f"[llama_server_manager] Failed to launch llama.cpp server: {e}")
            return

    # --------------------------------------------------------
    # Wait for port to open
    # --------------------------------------------------------
    for _ in range(60):  # up to ~30 seconds
        if is_server_running():
            break
        time.sleep(0.5)

    # --------------------------------------------------------
    # Wait for server to be READY (model fully loaded)
    # --------------------------------------------------------
    for _ in range(120):  # up to ~60 seconds
        if _server_is_ready():
            return
        time.sleep(0.5)

    print("[llama_server_manager] Warning: llama.cpp server did not become ready in time.")


# ------------------------------------------------------------
# Stop llama.cpp server (robust)
# ------------------------------------------------------------

def stop_llama_server() -> None:
    """
    Stop the llama.cpp server whether we launched it or not.
    """
    global _llama_server_process

    print("LLAMA: stop_llama_server called")
    print("LLAMA: process handle =", _llama_server_process)

    # --------------------------------------------------------
    # 1. If we launched it via subprocess, kill it cleanly
    # --------------------------------------------------------
    if _llama_server_process is not None:
        try:
            _llama_server_process.terminate()
            _llama_server_process.wait(timeout=5)
        except Exception:
            try:
                _llama_server_process.kill()
            except Exception:
                pass
        finally:
            _llama_server_process = None
        return

    # --------------------------------------------------------
    # 2. Kill any process listening on the port (external server)
    # --------------------------------------------------------
    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                for conn in proc.connections(kind="inet"):
                    if conn.laddr.port == LLAMA_SERVER_PORT:
                        print(f"LLAMA: killing external server PID {proc.pid}")
                        proc.terminate()
                        proc.wait(timeout=5)
                        return
            except Exception:
                continue
    except Exception as e:
        print("LLAMA: failed to scan processes:", e)

    # --------------------------------------------------------
    # 3. Soft shutdown attempt (optional)
    # --------------------------------------------------------
    try:
        requests.post(
            f"http://{LLAMA_SERVER_HOST}:{LLAMA_SERVER_PORT}/v1/shutdown",
            timeout=1.0
        )
    except Exception:
        pass


# ------------------------------------------------------------
# Public status API for the GUI
# ------------------------------------------------------------

def get_llama_server_status() -> str:
    """
    Return a simple status string: 'running' or 'offline'.
    The GUI uses this to update the indicator.
    """
    return "running" if is_server_running() else "offline"
