"""
explore_plc.py — Exploratory script for Snap7 / S7-1500 communication
Run directly on Windows (no Docker needed):
    pip install python-snap7
    python explore_plc.py
"""

import snap7
import time
import struct

# ── Connection parameters ────────────────────────────────────────────
PLC_IP   = "192.168.1.100"
PLC_RACK = 0
PLC_SLOT = 1
DB       = 1   # Data Block number

# ── Connect ──────────────────────────────────────────────────────────
print("=" * 55)
print("  Snap7 — S7-1500 Exploration Script")
print("=" * 55)
print(f"\n[1] Connecting to {PLC_IP} (rack={PLC_RACK}, slot={PLC_SLOT})...")

client = snap7.client.Client()
client.connect(PLC_IP, PLC_RACK, PLC_SLOT)

if not client.get_connected():
    print("    ERROR: could not connect. Check IP / PUT-GET access.")
    exit(1)

info = client.get_cpu_info()
print(f"    OK — Connected.")
print(f"    CPU: {info.ModuleTypeName.decode().strip()}")

# ── Raw byte dump ────────────────────────────────────────────────────
print(f"\n[2] Raw byte dump — DB{DB}, bytes 0..5")
print(f"    DB layout : [BOOL V1][padding][INT V2 high][INT V2 low][INT counter high][INT counter low]")
raw = client.db_read(DB, start=0, size=6)
print(f"    Hex : {raw.hex(' ').upper()}")
print(f"    Dec : {list(raw)}")
print(f"    Bin : {' '.join(f'{b:08b}' for b in raw)}")

# ── Interpret BOOL (V1) — byte 0, bit 0 ─────────────────────────────
print(f"\n[3] Interpret V1 (BOOL) — DB{DB}.DBX0.0")
byte0 = raw[0]
bit0  = bool(byte0 & 0b00000001)
print(f"    Byte 0 raw  : 0x{byte0:02X} = {byte0:08b}b")
print(f"    Bit 0 (DBX0.0) : {bit0}  --> V1 = {'TRUE' if bit0 else 'FALSE'}")

# ── Interpret INT (V2) — bytes 2-3, big-endian signed ───────────────
print(f"\n[4] Interpret V2 (INT) — DB{DB}.DBW2")
b_high = raw[2]
b_low  = raw[3]
v2 = int.from_bytes([b_high, b_low], byteorder="big", signed=True)
print(f"    Byte 2 (high) : 0x{b_high:02X} = {b_high:08b}b")
print(f"    Byte 3 (low)  : 0x{b_low:02X}  = {b_low:08b}b")
print(f"    Combined      : 0x{b_high:02X}{b_low:02X}")
print(f"    As INT (big-endian, signed) : {v2}  --> V2 = {v2}")

# ── Continuous read loop ─────────────────────────────────────────────
print(f"\n[5] Continuous read (Ctrl+C to stop) — refresh 1s")
print(f"    {'Timestamp':<12} {'V1 (BOOL)':<14} {'V2 (INT)':<12} {'Counter':<12} {'Raw bytes'}")
print(f"    {'-'*64}")

try:
    while True:
        raw = client.db_read(DB, 0, 6)
        v1      = bool(raw[0] & 0x01)
        v2      = int.from_bytes(raw[2:4], byteorder="big", signed=True)
        counter = int.from_bytes(raw[4:6], byteorder="big", signed=True)
        ts = time.strftime("%H:%M:%S")
        raw_str = raw.hex(' ').upper()
        print(f"    {ts:<12} {'TRUE' if v1 else 'FALSE':<14} {v2:<12} {counter:<12} {raw_str}")
        time.sleep(1)

except KeyboardInterrupt:
    print("\n\n[6] Stopped by user.")

# ── Disconnect ───────────────────────────────────────────────────────
client.disconnect()
print("[7] Disconnected.\n")
