"""
Open Pipe Connector — Siemens WinCC Unified
Reads/writes WinCC Unified internal tags via the Open Pipe Unix socket.

Volume mapping required in docker-compose.yml:
  /tmp/siemens/automation:/tempcontainer/

When the socket is not available (e.g., running on Pi for dev),
all reads return simulated values automatically.

NOTE: The exact socket filename and JSON protocol must be confirmed
      with Siemens documentation / Michal before deploying on the panel.
"""

import os
import socket
import json
import logging
import time

logger = logging.getLogger(__name__)

SOCKET_DIR  = os.getenv("OPENPIPE_SOCKET_DIR", "/tempcontainer")
SOCKET_FILE = os.getenv("OPENPIPE_SOCKET_FILE", "openpipe.sock")

# All 21 WinCC Unified internal tags with their types
TAG_TYPES = {
    "T_hin":                 "Real",
    "T_hout":                "Real",
    "T_we_piec_skal":        "Int",
    "T_wy_PIEC_skal":        "Int",
    "Tin1_wymiennik1":       "Real",
    "Tout1_wymiennik1":      "Real",
    "Tin1_wymiennik1_skal":  "Int",
    "Tout1_wymiennik1_skal": "Int",
    "Tin2_wymiennik1":       "Real",
    "Tout2_wymiennik1":      "Real",
    "Tin2_wymiennik1_skal":  "Int",
    "Tout2_wymiennik1_skal": "Int",
    "F1":                    "Real",
    "F1_SP":                 "Real",
    "F1_skal":               "Int",
    "F2":                    "Real",
    "F2_SP":                 "Real",
    "F2_skal":               "Int",
    "Zawor_F1":              "Word",
    "Zawor_F2":              "Int",
    "power":                 "Bool",
}

TAGS = list(TAG_TYPES.keys())


class OpenPipeConnector:
    """
    Communicates with WinCC Unified via Open Pipe Unix socket.
    Falls back to simulation when socket is unavailable (dev on Pi).
    """

    def __init__(self):
        self._sock_path = os.path.join(SOCKET_DIR, SOCKET_FILE)
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        available = os.path.exists(self._sock_path)
        if available:
            logger.info(f"Open Pipe socket found: {self._sock_path}")
        else:
            logger.warning(
                f"Open Pipe socket not found at {self._sock_path} — simulation mode active"
            )
        return available

    def is_available(self) -> bool:
        return self._available

    # ── Public API ─────────────────────────────────────────────────────────────

    def read_all_tags(self) -> dict:
        """
        Read all 21 WinCC Unified tags.
        Returns {tag_name: value, ...} + 'source' key.
        """
        if not self._available:
            data = self._simulated_values()
            data["source"] = "SIMULATION"
            return data
        try:
            data = self._read_via_socket(TAGS)
            data["source"] = "OPENPIPE"
            return data
        except Exception as exc:
            logger.error(f"Open Pipe read failed: {exc}")
            data = self._simulated_values()
            data["source"] = "SIMULATION"
            return data

    def write_tag(self, tag_name: str, value) -> bool:
        """Write a single tag value via Open Pipe."""
        if tag_name not in TAG_TYPES:
            raise ValueError(f"Unknown tag: {tag_name}")
        if not self._available:
            logger.warning(f"Open Pipe not available — write {tag_name}={value} ignored")
            return False
        try:
            self._write_via_socket(tag_name, value)
            logger.info(f"Open Pipe write: {tag_name} = {value}")
            return True
        except Exception as exc:
            logger.error(f"Open Pipe write {tag_name} failed: {exc}")
            return False

    # ── Socket I/O ─────────────────────────────────────────────────────────────

    def _read_via_socket(self, tag_names: list) -> dict:
        """
        Send a read request via the Open Pipe Unix socket.
        Protocol: newline-delimited JSON over Unix domain socket.
        TODO: confirm exact socket filename + message format with Siemens docs.
        """
        request = json.dumps({"action": "read", "tags": tag_names}) + "\n"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect(self._sock_path)
            s.sendall(request.encode())
            response = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b"\n" in response:
                    break
        return json.loads(response.split(b"\n")[0].decode())

    def _write_via_socket(self, tag_name: str, value):
        """Write a tag value via the Open Pipe Unix socket."""
        request = json.dumps({"action": "write", "tag": tag_name, "value": value}) + "\n"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect(self._sock_path)
            s.sendall(request.encode())

    # ── Simulation fallback ────────────────────────────────────────────────────

    def _simulated_values(self) -> dict:
        """Return plausible simulated values for all 21 tags."""
        t = time.time()
        base_t = 80.0 + 20.0 * abs((t % 60) / 30.0 - 1.0)
        f1 = round(2.5 + 0.5 * abs((t % 30) / 15.0 - 1.0), 2)
        f2 = round(1.8 + 0.3 * abs((t % 20) / 10.0 - 1.0), 2)
        return {
            "T_hin":                 round(base_t - 10.0, 1),
            "T_hout":                round(base_t + 15.0, 1),
            "T_we_piec_skal":        int((base_t - 10.0) * 10),
            "T_wy_PIEC_skal":        int((base_t + 15.0) * 10),
            "Tin1_wymiennik1":       round(base_t - 5.0, 1),
            "Tout1_wymiennik1":      round(base_t + 8.0, 1),
            "Tin1_wymiennik1_skal":  int((base_t - 5.0) * 10),
            "Tout1_wymiennik1_skal": int((base_t + 8.0) * 10),
            "Tin2_wymiennik1":       round(base_t - 3.0, 1),
            "Tout2_wymiennik1":      round(base_t + 6.0, 1),
            "Tin2_wymiennik1_skal":  int((base_t - 3.0) * 10),
            "Tout2_wymiennik1_skal": int((base_t + 6.0) * 10),
            "F1":                    f1,
            "F1_SP":                 3.0,
            "F1_skal":               int(f1 * 100),
            "F2":                    f2,
            "F2_SP":                 2.0,
            "F2_skal":               int(f2 * 100),
            "Zawor_F1":              1,
            "Zawor_F2":              2,
            "power":                 True,
        }
