# Technical Architecture — S7-1500 Thermal Process Monitor

**Project:** Thesis — Industrial Automation / Thermal Process Control  
**Stack:** Python 3.11 · Flask · Socket.IO · Python-Snap7 · Open Pipe · Docker · HTML/JS · Chart.js  
**Deployment target:** Siemens SIMATIC HMI Unified Comfort Panel 7" (Industrial Edge)  
**Dev environment:** Raspberry Pi 4 (192.168.1.38)

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                      Docker Container                            │
│                                                                  │
│  ┌──────────────┐   ┌──────────────────┐   ┌─────────────────┐   │
│  │  main.py     │──▶│ plc_connector.py │──▶│ S7-1500 PLC    │   │
│  │  (Flask +    │   │  (Snap7/TCP)     │   │ 192.168.1.100   │   │
│  │  Socket.IO)  │   └──────────────────┘   └─────────────────┘   │
│  │              │   ┌──────────────────┐                         │
│  │              │──▶│openpipe_connector│──▶ /tempcontainer/     │
│  │              │   │  .py (WinCC tags)│   (Unix socket)         │
│  │              │   └──────────────────┘                         │
│  │              │   ┌──────────────────┐                         │
│  │              │──▶│ thermal_model.py │  (simulation fallback)
│  │              │   └──────────────────┘                         │
│  │              │   ┌──────────────────┐                         │
│  │              │──▶│   logger.py      │──▶ /app/logs/*.csv     │
│  └──────────────┘   └──────────────────┘                         │
│         │                                                        │
│         ▼  Socket.IO (process_data · process_tags)               │
│  ┌──────────────────────────────────────────────┐                │
│  │  Browser UI — port 5000                      │                │
│  │  / Monitor · /test · /process · /schema      │                │
│  └──────────────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────────────┘
```

**Data source priority:**  
PLC (Snap7/TCP) → Open Pipe (WinCC Unified tags) → Simulation fallback

---

## Module Descriptions

### `main.py` — Flask application entry point

Instantiates singletons and runs three background threads:
- `_simulation_loop` — advances `ThermalProcessModel` every 3 s
- `_plc_poll_loop` — polls S7-1500 via Snap7 every 3 s, emits `process_data`
- `_openpipe_poll_loop` — reads 21 WinCC tags every 3 s, emits `process_tags`

| Route | Method | Description |
|---|---|---|
| `/` | GET | Monitor — charts, PID visualiser, alarms, CSV export |
| `/test` | GET | Test DB — read/write PLC variables V1–V9 |
| `/process` | GET | Process — 21 WinCC tags in 3 sections |
| `/schema` | GET | **Synoptique** — full-screen P&ID schematic (primary panel page) |
| `/api/data` | GET | JSON process snapshot (Snap7 / simulation) |
| `/api/setpoint` | POST | Update temperature / flow setpoints |
| `/api/process/data` | GET | JSON — all 21 WinCC Unified tags |
| `/api/process/write` | POST | Write F1_SP or F2_SP via Open Pipe |
| `/api/export/csv` | GET | Download full process log as CSV |
| `/api/status` | GET | PLC connection state, log statistics |
| `/health` | GET | Docker healthcheck endpoint |

### `plc_connector.py` — Siemens S7-1500 interface (Snap7)

Wraps `python-snap7` for direct DB read/write over TCP.  
Used for the Monitor page and simulation loop.

**DB memory map (DB1):**

| Address | Type | Variable |
|---|---|---|
| DB1.DBD0 | REAL | Measured temperature (°C) |
| DB1.DBD4 | REAL | Measured flow rate (m³/h) |
| DB1.DBD8 | REAL | Temperature setpoint (°C) |
| DB1.DBD12 | REAL | Flow rate setpoint (m³/h) |
| DB1.DBW16 | INT | Valve state (0=CLOSED, 1=OPEN, 2=PARTIAL) |

### `openpipe_connector.py` — WinCC Unified Open Pipe interface

Reads/writes the 21 WinCC Unified internal tags via Unix socket at `/tempcontainer/`.  
Falls back to simulated values when the socket is unavailable (dev on Pi).

**Volume mapping required in `docker-compose.yml`:**
```yaml
volumes:
  - /tmp/siemens/automation:/tempcontainer/
```

> **TODO:** Confirm exact socket filename and JSON protocol format with Siemens docs / Michal before deploying on panel.

**21 WinCC Unified tags:**

| Tag | Type | Role |
|---|---|---|
| T_hin | Real | Heater inlet temperature |
| T_hout | Real | Heater outlet = HE hot inlet |
| Tin1_wymiennik1 | Real | **HE hot inlet (controlled variable — PI+P loop)** |
| Tout1_wymiennik1 | Real | HE hot outlet |
| Tin2_wymiennik1 | Real | HE cold inlet |
| Tout2_wymiennik1 | Real | **HE cold outlet (cascade outer loop — TBD)** |
| F1 | Real | Hot flow rate |
| **F1_SP** | Real | **Hot flow setpoint (manipulated variable — writable)** |
| F2 | Real | Cold flow rate |
| **F2_SP** | Real | **Cold flow setpoint (writable)** |
| Zawor_F1 | Word | Hot valve state |
| Zawor_F2 | Int | Cold valve state |
| power | Bool | Heater on/off |
| *_skal variants | Int | Scaled raw integer values (read-only) |

### `thermal_model.py` — First-order simulation fallback

Discrete-time Euler integration active when no PLC is connected:

```
T[k+1] = T[k] + (dt / τ) · (K · u[k] − (T[k] − T_amb)) + w_T
```

`τ = 45 s`, `K = 220`, noise `w_T ~ N(0, 0.25)`.

### `logger.py` — CSV data persistence

Appends one row per 3-second sample to `/app/logs/process_data.csv`.

**Log columns:** `timestamp, temperature, setpoint_temp, flow_rate, setpoint_flow, valve_state, source`

---

## Web Pages

| Page | Route | Description |
|---|---|---|
| Monitor | `/` | Time-series charts, PID visualiser, multi-level alarms, CSV replay |
| Test DB | `/test` | Raw PLC variable read/write (V1–V9) |
| Process | `/process` | All 21 WinCC tags in 3 sections: Four, Échangeur 1, Échangeur 2 |
| **Synoptique** | `/schema` | **Full-screen P&ID schematic — primary display for the 7" panel** |

### Synoptique (`/schema`) — P&ID layout

```
T_hin → [HEATER] → T_hout=Tin1 → [──── HEAT EXCHANGER ────] → Tout1
  power                F1 (hot flow →)                   Zawor_F1
                       ← ← ← ← ← ← ← ← ← ← ← ← ← ←
         Tout2 ←     F2 (cold flow ←)                   Zawor_F2  ← Tin2
```

Setpoints F1_SP and F2_SP are editable via touch-friendly arrow buttons.

---

## Control Strategy (planned)

### Primary loop — PI+P on Tin1
- **Controlled variable:** Tin1 (HE hot inlet temperature)
- **Manipulated variable:** F1 (hot flow rate via F1_SP)
- **Structure:** PI+P (proportional on measurement — avoids setpoint kick)
- **Gains:** To be identified

### Cascade loop — Tout2 (under discussion with Michal)
- **Outer loop:** Tout2 (cold outlet) → output = Tin1_SP
- **Inner loop:** PI+P on Tin1 → F1_SP
- **Status:** Architecture to be confirmed

> Controllers will be implemented server-side in Python (dedicated thread in `main.py`).  
> The current browser-side PID in `index.html` is a visualisation placeholder only.

---

## Project File Structure

```
project-s7/
├── app/
│   ├── main.py                Flask app + routes + background threads
│   ├── plc_connector.py       Snap7 PLC interface (TCP, DB read/write)
│   ├── openpipe_connector.py  WinCC Unified Open Pipe (21 tags)
│   ├── thermal_model.py       First-order simulation fallback
│   ├── logger.py              CSV data logger
│   ├── requirements.txt       Python dependencies
│   └── templates/
│       ├── index.html         Monitor page
│       ├── test.html          Test DB page
│       ├── process.html       Process page (21 tags)
│       └── schema.html        Synoptique page (primary panel page)
├── logs/                      Persistent process data (gitignored)
├── Dockerfile                 Python 3.11-slim image
├── docker-compose.yml         Service orchestration
├── .env                       PLC IP, rack, slot, DB config
└── .dockerignore
```

---

## Configuration (`.env`)

```env
PLC_IP=192.168.1.100   # S7-1500 IP
PLC_RACK=0
PLC_SLOT=1
PLC_DB=1
PORT=5000
FLASK_DEBUG=1          # Set to 0 in production
```

---

## Deployment

### Development — Raspberry Pi (192.168.1.38)

```bash
# Deploy update
git pull && docker compose down && docker compose up -d --build

# View logs
docker compose logs -f

# Shutdown properly
docker compose down && sudo shutdown -h now
```

### Production target — SIMATIC HMI Unified Comfort Panel 7"

1. Install **Industrial Edge Publisher** (available from Michal, week of 2026-04-14)
2. Activate **Edge licence** (to be provided by Michal)
3. Package `docker-compose.yml` → `.app` with Edge Publisher
4. Add Open Pipe volume: `/tmp/siemens/automation:/tempcontainer/`
5. Deploy `.app` to panel via Edge Management
6. Confirm Open Pipe socket filename + protocol with Siemens docs

---

## Network

```
PC (WiFi) ──────────────────┐
Pi (WiFi/Ethernet) ──────────┤ Router/Switch
S7-1500 PLC (Ethernet) ──────┤  192.168.1.x
Panel Unified 7" (Ethernet) ─┘
```

| Device | IP |
|---|---|
| Raspberry Pi | 192.168.1.38 |
| SIMATIC Panel | 192.168.1.200 |
| S7-1500 PLC | 192.168.1.100 |
