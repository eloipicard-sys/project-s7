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

from process_sim import ProcessSimulator

logger = logging.getLogger(__name__)

SOCKET_DIR  = os.getenv("OPENPIPE_SOCKET_DIR", "/tempcontainer")
SOCKET_FILE = os.getenv("OPENPIPE_SOCKET_FILE", "openpipe.sock")

# All 21 WinCC Unified internal tags with their types
TAG_TYPES = {
    # Furnace
    "T_hin":                      "Real",
    "T_hout":                     "Real",
    "T_we_rock_furnace":          "Int",
    "T_wy_Oven_scale":            "Int",
    # Heat exchanger HE1
    "Tin1_HE1":                   "Real",
    "Tout1_HE1":                  "Real",
    "Tin2_HE1":                   "Real",
    "Tout2_HE1":                  "Real",
    "Tin1_heat_exchanger1_scale": "Int",
    "Tout1_HE1_raw":              "Int",
    "Tin2_HE1_raw":               "Int",
    "Tout2_HE1_raw":              "Int",
    # Flow circuit 1
    "F1":                         "Real",
    "F1_SP":                      "Real",
    "F1_skal":                    "Int",
    "Valve_F1":                   "Word",
    # Flow circuit 2
    "F2":                         "Real",
    "F2_SP":                      "Real",
    "F2_skal":                    "Int",
    "Valve_F2":                   "Int",
    # Power
    "power":                      "Bool",
    # Heater PWM command (0–100 %) — tag name to confirm with Michal
    "HeaterLarge_PWM":            "Real",
}

TAGS = list(TAG_TYPES.keys())


class OpenPipeConnector:
    """
    Communicates with WinCC Unified via Open Pipe Unix socket.
    Falls back to Snap7 Merker reads when socket is unavailable (dev PC / Pi).
    Falls back to simulation when neither Open Pipe nor Snap7 is available.
    """

    def __init__(self):
        self._sock_path  = os.path.join(SOCKET_DIR, SOCKET_FILE)
        self._available  = self._check_availability()
        self._plc        = None  # set via set_snap7_fallback()
        self._sim        = ProcessSimulator()

    def set_snap7_fallback(self, plc_connector) -> None:
        """Register a PLCConnector to use as fallback when Open Pipe is unavailable."""
        self._plc = plc_connector

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
        Read all WinCC Unified tags.
        Priority: Open Pipe socket → Snap7 Merker → simulation.
        """
        if self._available:
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
        """
        Write a single tag value.
        Priority: Open Pipe socket → Snap7 Merker (F1_SP/F2_SP only) → no-op.
        """
        if tag_name not in TAG_TYPES:
            raise ValueError(f"Unknown tag: {tag_name}")

        if self._available:
            try:
                self._write_via_socket(tag_name, value)
                logger.info(f"Open Pipe write: {tag_name} = {value}")
                return True
            except Exception as exc:
                logger.error(f"Open Pipe write {tag_name} failed: {exc}")

        # Aucun transport : la valeur est appliquée au modèle de simulation, pour
        # que l'interface réagisse aux commandes comme elle le ferait sur le banc.
        if tag_name == "HeaterLarge_PWM":
            self._sim.set_pwm(value)
        elif tag_name == "F1_SP":
            self._sim.set_flows(f1=value)
        elif tag_name == "F2_SP":
            self._sim.set_flows(f2=value)
        else:
            logger.warning(f"write_tag {tag_name}={value} — no transport available")
            return False
        logger.info(f"simulation: {tag_name} = {value}")
        return True

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
        """
        Valeurs simulées des 21 variables, issues du modèle dynamique.

        Le modèle reproduit la structure identifiée expérimentalement : la
        commande PWM agit sur Tin1 avec le retard et la constante de temps
        mesurés, et Tout2 suit Tin1 avec sa propre dynamique, plus lente.
        """
        s = self._sim.step()

        f1, f2 = s["F1"], s["F2"]
        return {
            "T_hin":                      s["T_hin"],
            "T_hout":                     s["T_hout"],
            "T_we_rock_furnace":          int(s["T_hin"] * 10),
            "T_wy_Oven_scale":            int(s["T_hout"] * 10),
            "Tin1_HE1":                   s["Tin1"],
            "Tout1_HE1":                  s["Tout1"],
            "Tin2_HE1":                   s["Tin2"],
            "Tout2_HE1":                  s["Tout2"],
            "Tin1_heat_exchanger1_scale": int(s["Tin1"] * 10),
            "Tout1_HE1_raw":              int(s["Tout1"] * 10),
            "Tin2_HE1_raw":               int(s["Tin2"] * 10),
            "Tout2_HE1_raw":              int(s["Tout2"] * 10),
            "F1":                         f1,
            "F1_SP":                      f1,
            "F1_skal":                    int(f1 * 100),
            "Valve_F1":                   1,
            "F2":                         f2,
            "F2_SP":                      f2,
            "F2_skal":                    int(f2 * 100),
            "Valve_F2":                   2,
            "power":                      True,
            "HeaterLarge_PWM":            s["PWM"],
        }
