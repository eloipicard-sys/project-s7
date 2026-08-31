"""
PLC Connector — Siemens S7-1500
Wraps python-snap7 with connection management and automatic fallback to simulation.

DB layout (adapt to your TIA Portal project):
  DB1.DBD0   REAL  — measured temperature   (deg C)
  DB1.DBD4   REAL  — measured flow rate     (m3/h)
  DB1.DBD8   REAL  — temperature setpoint   (deg C)
  DB1.DBD12  REAL  — flow rate setpoint     (m3/h)
  DB1.DBW16  INT   — valve state (0=CLOSED, 1=OPEN, 2=PARTIAL)
"""

import os
import logging
import threading

# Attempt to import snap7 — graceful fallback if not installed
try:
    import snap7
    from snap7.util import get_real, set_real
    from snap7.types import Areas
    SNAP7_AVAILABLE = True
except ImportError:
    SNAP7_AVAILABLE = False
    logging.warning("python-snap7 not available — PLCConnector will report disconnected")

logger = logging.getLogger(__name__)

# ── DB1 memory map ───────────────────────────────────────────────────────────
DB_NUMBER = int(os.getenv("PLC_DB", 1))

# Process variables block — 9 × REAL starting at offset 28 (36 bytes total)
# DB1.DBD56 = krPI (Kp of inner PI, written by Docker after identification)
# DB1.DBD60 = TiPI (Ti of inner PI, written by Docker after identification)
OFFSET_PROCESS = 28
_PROCESS_VARS  = [
    (28, "Tin1_HE1"),
    (32, "Tout1_HE1"),
    (36, "Tin2_HE1"),
    (40, "Tout2_HE1"),
    (44, "F1"),
    (48, "F2"),
    (52, "F1_SP"),
    (56, "krPI"),
    (60, "TiPI"),
]
OFFSET_F1_SP = 52
OFFSET_krPI  = 56
OFFSET_TiPI  = 60


class PLCConnector:
    """
    Thread-safe wrapper around the snap7 client.
    All read/write operations are guarded by connection checks.
    """

    def __init__(self):
        self.client   = None
        self.plc_ip   = os.getenv("PLC_IP", "")
        self.plc_rack = int(os.getenv("PLC_RACK", 0))
        self.plc_slot = int(os.getenv("PLC_SLOT", 1))
        self._lock    = threading.Lock()

    # ── Connection management ────────────────────────────────────────────────

    def connect(self) -> bool:
        """Attempt connection to the S7-1500. Returns True on success."""
        if not SNAP7_AVAILABLE:
            logger.warning("snap7 library not installed")
            return False
        if not self.plc_ip:
            logger.warning("PLC_IP not configured — cannot connect")
            return False
        try:
            self.client = snap7.client.Client()
            self.client.connect(self.plc_ip, self.plc_rack, self.plc_slot)
            connected = self.client.get_connected()
            if connected:
                logger.info(f"Connected to S7-1500 at {self.plc_ip} "
                            f"(rack={self.plc_rack}, slot={self.plc_slot})")
            return connected
        except Exception as exc:
            logger.error(f"PLC connection failed: {exc}")
            self.client = None
            return False

    def is_connected(self) -> bool:
        if self.client is None:
            return False
        try:
            return bool(self.client.get_connected())
        except Exception:
            return False

    def disconnect(self):
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
        self.client = None

    # ── Low-level read/write ─────────────────────────────────────────────────

    def _read_real(self, db: int, offset: int) -> float:
        raw = self.client.db_read(db, offset, 4)
        return get_real(raw, 0)

    def _write_real(self, db: int, offset: int, value: float):
        raw = bytearray(4)
        set_real(raw, 0, float(value))
        self.client.db_write(db, offset, raw)

    def _read_int(self, db: int, offset: int) -> int:
        raw = self.client.db_read(db, offset, 2)
        return int.from_bytes(raw, byteorder="big", signed=True)

    def _read_bool(self, db: int, byte_offset: int, bit_offset: int = 0) -> bool:
        """Read a single BOOL bit from a DB byte."""
        raw = self.client.db_read(db, byte_offset, 1)
        return bool(raw[0] & (1 << bit_offset))

    def _write_bool(self, db: int, byte_offset: int, bit_offset: int, value: bool):
        """Read-modify-write a single BOOL bit in a DB byte."""
        raw = bytearray(self.client.db_read(db, byte_offset, 1))
        if value:
            raw[0] |= (1 << bit_offset)
        else:
            raw[0] &= ~(1 << bit_offset)
        self.client.db_write(db, byte_offset, bytes(raw))

    def _write_int(self, db: int, offset: int, value: int):
        """Write a 16-bit signed INT to a DB."""
        raw = int(value).to_bytes(2, byteorder="big", signed=True)
        self.client.db_write(db, offset, raw)

    # ── Merker area helpers ───────────────────────────────────────────────────

    # All real-valued MD tags: (byte_offset, tag_name)
    _MERKER_REALS = [
        (12, "T_hout"),
        (16, "T_hin"),
        (20, "power_SP"),
        (24, "F1_SP"),
        (28, "F1"),
        (32, "F2"),
        (36, "F2_SP"),
        (40, "Tin2_HE1"),
        (44, "Tout1_HE1"),
        (48, "Tin1_HE1"),
        (52, "Tout2_HE1"),
        (56, "pressure"),
    ]
    _MK_START = 12
    _MK_END   = 60  # exclusive

    def read_merker_tags(self) -> dict:
        """
        Read all REAL-valued MD variables in one Merker area read.
        Returns dict with same keys as openpipe.read_all_tags() for real-valued tags.
        Raw ADC / Bool / Word tags are absent (not in Merker REAL area).
        """
        if not self.is_connected():
            raise ConnectionError("PLC not connected")
        size = self._MK_END - self._MK_START
        with self._lock:
            raw = self.client.read_area(Areas.MK, 0, self._MK_START, size)
        result = {}
        for offset, name in self._MERKER_REALS:
            result[name] = round(get_real(raw, offset - self._MK_START), 3)
        return result

    def write_merker_real(self, byte_offset: int, value: float):
        """Write a REAL value to a Merker double-word (MD) address."""
        if not self.is_connected():
            raise ConnectionError("PLC not connected")
        data = bytearray(4)
        set_real(data, 0, float(value))
        with self._lock:
            self.client.write_area(Areas.MK, 0, byte_offset, data)
        logger.info(f"Merker write: MD{byte_offset} = {value}")

    # ── Process data API ─────────────────────────────────────────────────────

    def read_process_data(self) -> dict:
        """
        Read all 7 process REAL variables from DB1 (offsets 28–55).
        Returns dict with canonical tag names matching openpipe_connector.
        Raises ConnectionError if PLC is not reachable.
        """
        if not self.is_connected():
            raise ConnectionError("PLC not connected")

        with self._lock:
            raw = self.client.db_read(DB_NUMBER, OFFSET_PROCESS, 36)

        result = {}
        for offset, name in _PROCESS_VARS:
            result[name] = round(get_real(raw, offset - OFFSET_PROCESS), 3)
        return result

    def write_flow_setpoint(self, value: float):
        """Write F1_SP to DB1 at offset 52."""
        if not self.is_connected():
            raise ConnectionError("PLC not connected")
        with self._lock:
            self._write_real(DB_NUMBER, OFFSET_F1_SP, value)
        logger.info(f"F1_SP written: {value} m3/h → DB{DB_NUMBER}.DBD{OFFSET_F1_SP}")

    def write_pi_params(self, krPI: float, TiPI: float):
        """Write identified PI parameters to DB1 (DBD56=krPI, DBD60=TiPI)."""
        if not self.is_connected():
            raise ConnectionError("PLC not connected")
        with self._lock:
            self._write_real(DB_NUMBER, OFFSET_krPI, krPI)
            self._write_real(DB_NUMBER, OFFSET_TiPI, TiPI)
        logger.info(f"PI params written: krPI={krPI} → DB{DB_NUMBER}.DBD{OFFSET_krPI}, "
                    f"TiPI={TiPI} → DB{DB_NUMBER}.DBD{OFFSET_TiPI}")

    # ── Test variables API ────────────────────────────────────────────────────
    # DB layout:
    #   Offset 0  → V1      BOOL  (1 byte)
    #   Offset 1  → padding       (1 byte)
    #   Offset 2  → V2      INT   (2 bytes)
    #   Offset 4  → V3      INT   (2 bytes)
    #   Offset 6  → V4      INT   (2 bytes)
    #   Offset 8  → V5      INT   (2 bytes)
    #   Offset 10 → V6      INT   (2 bytes)
    #   Offset 12 → V7      INT   (2 bytes)
    #   Offset 14 → V8      INT   (2 bytes)
    #   Offset 16 → V9      INT   (2 bytes)
    #   Offset 18 → counter INT   (2 bytes)  ← read-only, incremented by PLC
    #   Total     → 20 bytes

    def read_test_vars(self, db: int) -> dict:
        """Read all test variables from TIA Portal DB (20 bytes)."""
        if not self.is_connected():
            raise ConnectionError("PLC not connected")
        raw = self.client.db_read(db, 0, 20)
        return {
            "V1":      bool(raw[0] & 0x01),
            "V2":      int.from_bytes(raw[2:4],   byteorder="big", signed=True),
            "V3":      int.from_bytes(raw[4:6],   byteorder="big", signed=True),
            "V4":      int.from_bytes(raw[6:8],   byteorder="big", signed=True),
            "V5":      int.from_bytes(raw[8:10],  byteorder="big", signed=True),
            "V6":      int.from_bytes(raw[10:12], byteorder="big", signed=True),
            "V7":      int.from_bytes(raw[12:14], byteorder="big", signed=True),
            "V8":      int.from_bytes(raw[14:16], byteorder="big", signed=True),
            "V9":      int.from_bytes(raw[16:18], byteorder="big", signed=True),
            "counter": int.from_bytes(raw[18:20], byteorder="big", signed=True),
        }

    # INT offsets for V2–V9
    _INT_OFFSETS = {"V2": 2, "V3": 4, "V4": 6, "V5": 8,
                    "V6": 10, "V7": 12, "V8": 14, "V9": 16}

    def write_test_v1(self, db: int, value: bool):
        if not self.is_connected():
            raise ConnectionError("PLC not connected")
        self._write_bool(db, byte_offset=0, bit_offset=0, value=value)
        logger.info(f"[TEST] V1 (BOOL) written: {value} → DB{db}.DBX0.0")

    def write_test_int(self, db: int, variable: str, value: int):
        """Write any INT variable V2–V9 by name."""
        if not self.is_connected():
            raise ConnectionError("PLC not connected")
        offset = self._INT_OFFSETS.get(variable.upper())
        if offset is None:
            raise ValueError(f"Unknown variable: {variable} (valid: V2–V9)")
        if not (-32768 <= value <= 32767):
            raise ValueError(f"INT out of range: {value}")
        self._write_int(db, offset=offset, value=value)
        logger.info(f"[TEST] {variable} (INT) written: {value} → DB{db}.DBW{offset}")
