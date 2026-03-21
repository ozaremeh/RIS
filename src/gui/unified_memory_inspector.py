# unified_memory_inspector.py

import psutil
import subprocess
import re
from typing import Dict, Optional, List


# ---------- low-level helpers ----------

def _run(cmd: List[str]) -> str:
    out = subprocess.check_output(cmd, text=True)
    return out.strip()


# ---------- process-level memory ----------

def get_process_rss_mb_by_name(name_substring: str) -> float:
    """
    Return total RSS (MB) for all processes whose name or cmdline
    contains `name_substring` (case-insensitive).
    """
    name_substring = name_substring.lower()
    total_rss = 0
    for p in psutil.process_iter(["name", "cmdline", "memory_info"]):
        try:
            name = (p.info["name"] or "").lower()
            cmd = " ".join(p.info["cmdline"] or []).lower()
            if name_substring in name or name_substring in cmd:
                total_rss += p.info["memory_info"].rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return total_rss / (1024 ** 2)


def get_lmstudio_rss_mb() -> float:
    """
    LM Studio runtime + UI (approx) by name match.
    Adjust substrings if your process names differ.
    """
    return get_process_rss_mb_by_name("lm studio")


def get_llamacpp_rss_mb() -> float:
    """
    llama.cpp server or CLI (approx) by name match.
    Adjust substrings if your binary name differs.
    """
    return get_process_rss_mb_by_name("llama")


def get_python_orchestrator_rss_mb(hint: Optional[str] = None) -> float:
    """
    Sum RSS for python processes; if `hint` is provided, only those whose
    cmdline contains the hint (e.g. 'orchestrator.py').
    """
    if hint is None:
        return get_process_rss_mb_by_name("python")
    return get_process_rss_mb_by_name(hint)


# ---------- system-level memory (macOS) ----------

def get_vm_stat_pages() -> Dict[str, int]:
    """
    Parse `vm_stat` output into a dict of counters (pages).
    """
    out = _run(["vm_stat"])
    pages = {}
    for line in out.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        # values look like " 12345." or " 12345"
        m = re.search(r"(\d+)", val)
        if m:
            pages[key] = int(m.group(1))
    return pages


def get_page_size_bytes() -> int:
    out = _run(["sysctl", "-n", "hw.pagesize"])
    return int(out)


def get_system_memory_snapshot_mb() -> Dict[str, float]:
    """
    Returns a coarse breakdown of system memory on macOS in MB.
    """
    pages = get_vm_stat_pages()
    page_size = get_page_size_bytes()

    def pages_to_mb(n: int) -> float:
        return n * page_size / (1024 ** 2)

    free_mb = pages_to_mb(pages.get("Pages free", 0))
    active_mb = pages_to_mb(pages.get("Pages active", 0))
    inactive_mb = pages_to_mb(pages.get("Pages inactive", 0))
    speculative_mb = pages_to_mb(pages.get("Pages speculative", 0))
    wired_mb = pages_to_mb(pages.get("Pages wired down", 0))
    compressed_mb = pages_to_mb(pages.get("Pages occupied by compressor", 0))

    total_mb = free_mb + active_mb + inactive_mb + speculative_mb + wired_mb + compressed_mb

    return {
        "total_mb_est": total_mb,
        "free_mb": free_mb,
        "active_mb": active_mb,
        "inactive_mb": inactive_mb,
        "speculative_mb": speculative_mb,
        "wired_mb": wired_mb,
        "compressed_mb": compressed_mb,
    }


def get_memory_pressure_summary() -> Dict[str, str]:
    """
    Wraps `memory_pressure -Q` for a quick qualitative view.
    """
    try:
        out = _run(["memory_pressure", "-Q"])
    except Exception:
        return {"raw": "memory_pressure not available"}
    return {"raw": out}


# ---------- unified snapshot ----------

def get_unified_memory_snapshot() -> Dict[str, object]:
    """
    One call to get everything you care about for the GUI.
    """
    sys_mem = get_system_memory_snapshot_mb()

    lmstudio_mb = get_lmstudio_rss_mb()
    llamacpp_mb = get_llamacpp_rss_mb()
    python_mb = get_python_orchestrator_rss_mb()

    visible_process_mb = lmstudio_mb + llamacpp_mb + python_mb

    suspicious_mb = max(sys_mem["total_mb_est"] - sys_mem["free_mb"] - visible_process_mb, 0)

    return {
        "system": sys_mem,
        "processes": {
            "lmstudio_mb": lmstudio_mb,
            "llamacpp_mb": llamacpp_mb,
            "python_mb": python_mb,
        },
        "derived": {
            # how much memory is in use (total - free)
            "used_mb_est": sys_mem["total_mb_est"] - sys_mem["free_mb"],
            # how much used memory is *not* explained by the three main processes
            "suspicious_mb": suspicious_mb,
        },
        "memory_pressure": get_memory_pressure_summary(),
    }


if __name__ == "__main__":
    import json
    snap = get_unified_memory_snapshot()
    print(json.dumps(snap, indent=2))
