"""
CSV process data logger.

Appends one row per sample to a persistent log file mounted as a Docker volume.
Never raises — logging failures are silent to avoid blocking the main loop.

Log file location: /app/logs/process_data.csv  (override with LOG_DIR env var)
"""

import csv
import os
import threading
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

LOG_DIR  = Path(os.getenv("LOG_DIR", "/app/logs"))
LOG_FILE = LOG_DIR / "process_data.csv"

COLUMNS = [
    "timestamp",
    "temperature",
    "setpoint_temp",
    "flow_rate",
    "setpoint_flow",
    "valve_state",
    "source",
]

_log_lock  = threading.Lock()
_row_count = 0


def init_logger():
    """Create log directory and write CSV header if file does not exist."""
    global _row_count
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        if not LOG_FILE.exists():
            with open(LOG_FILE, "w", newline="") as f:
                csv.writer(f).writerow(COLUMNS)
            logger.info(f"Log file created: {LOG_FILE}")
            _row_count = 0
        else:
            # Count existing rows once at startup (header excluded)
            with open(LOG_FILE, "r") as f:
                _row_count = max(sum(1 for _ in f) - 1, 0)
    except Exception as exc:
        logger.error(f"Logger init failed: {exc}")


def log_sample(data: dict):
    """Append one process data sample to the CSV log."""
    global _row_count
    try:
        with _log_lock:
            with open(LOG_FILE, "a", newline="") as f:
                csv.writer(f).writerow([
                    data.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
                    data.get("temperature"),
                    data.get("setpoint_temp"),
                    data.get("flow_rate"),
                    data.get("setpoint_flow"),
                    data.get("valve_state"),
                    data.get("source"),
                ])
            _row_count += 1
    except Exception as exc:
        logger.warning(f"Log write failed: {exc}")


def get_log_path() -> Path:
    return LOG_FILE


def get_log_stats() -> dict:
    """Return basic statistics about the current log file."""
    try:
        if not LOG_FILE.exists():
            return {"exists": False, "rows": 0, "size_kb": 0}
        size_kb = LOG_FILE.stat().st_size / 1024
        return {"exists": True, "rows": _row_count, "size_kb": round(size_kb, 1)}
    except Exception:
        return {"exists": False, "rows": 0, "size_kb": 0}
