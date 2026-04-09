# Technical Architecture — S7-1500 Thermal Process Monitor

**Project:** Thesis — Industrial Automation / Thermal Process Control
**Stack:** Python 3.11 · Flask · Python-Snap7 · Docker · HTML/JS · Chart.js

---

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Container                      │
│                                                             │
│   ┌──────────────┐    ┌──────────────┐   ┌─────────────┐  │
│   │  main.py     │───▶│plc_connector │──▶│ S7-1500 PLC │  │
│   │  (Flask app) │    │  .py         │   │ (Snap7/TCP) │  │
│   │              │    └──────────────┘   └─────────────┘  │
│   │              │    ┌──────────────┐                     │
│   │              │───▶│thermal_model │  (simulation only)  │
│   │              │    │  .py         │                     │
│   │              │    └──────────────┘                     │
│   │              │    ┌──────────────┐                     │
│   │              │───▶│  logger.py   │──▶ /app/logs/*.csv  │
│   └──────────────┘    └──────────────┘                     │
│          │                                                  │
│          ▼                                                  │
│   ┌──────────────┐                                         │
│   │  Browser UI  │  Chart.js · PID visualizer · Setpoint  │
│   │  port 5000   │  control · CSV export                   │
│   └──────────────┘                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Module Descriptions

### `main.py` — Flask application entry point

Instantiates singletons (PLCConnector, ThermalProcessModel, logger) and
defines all HTTP routes. Implements a data source priority:
real PLC data when connected, simulation fallback otherwise.

| Route | Method | Description |
|---|---|---|
| `/` | GET | Web supervision interface |
| `/api/data` | GET | JSON process snapshot (polling, 3 s) |
| `/api/setpoint` | POST | Update temperature and/or flow setpoints |
| `/api/export/csv` | GET | Download full process log as CSV |
| `/api/status` | GET | PLC connection state, log statistics |
| `/health` | GET | Docker healthcheck endpoint |

### `plc_connector.py` — Siemens S7-1500 interface

Wraps `python-snap7` with connection management, graceful error handling,
and read/write methods mapped to the TIA Portal DB layout.

**DB memory map (DB1 — adapt to TIA Portal):**

| Address | Type | Variable |
|---|---|---|
| DB1.DBD0 | REAL | Measured temperature (°C) |
| DB1.DBD4 | REAL | Measured flow rate (m³/h) |
| DB1.DBD8 | REAL | Temperature setpoint (°C) |
| DB1.DBD12 | REAL | Flow rate setpoint (m³/h) |
| DB1.DBW16 | INT | Valve state (0=CLOSED, 1=OPEN, 2=PARTIAL) |

> Prerequisites in TIA Portal: enable **PUT/GET access** in CPU properties
> (Protection & Security → Connection mechanisms → Permit access with PUT/GET).

### `thermal_model.py` — First-order simulation

Discrete-time Euler integration of a thermal process:

```
T[k+1] = T[k] + (dt / τ) · (K · u[k] − (T[k] − T_amb)) + w_T
```

where `u[k]` is the normalised heater output (0–1) computed by an internal
proportional controller, `τ = 45 s` is the thermal time constant, and
`w_T ~ N(0, 0.25)` is measurement noise. Removed from production when PLC
is connected.

### `logger.py` — CSV data persistence

Appends one row per 3-second sample to `/app/logs/process_data.csv`,
mounted as a Docker named volume to survive container restarts.

**Log columns:** `timestamp, temperature, setpoint_temp, flow_rate,
setpoint_flow, valve_state, source`

---

## Project File Structure

```
project-s7/
├── app/
│   ├── main.py              Flask application + routes
│   ├── plc_connector.py     Snap7 PLC interface
│   ├── thermal_model.py     First-order simulation model
│   ├── logger.py            CSV data logger
│   └── requirements.txt     Python dependencies
├── logs/                    Persistent process data logs (gitignored)
├── Dockerfile               Multi-layer Python 3.11-slim image
├── docker-compose.yml       Service orchestration
├── .env                     PLC IP, rack, slot configuration
└── .dockerignore
```

---

## Configuration (`.env`)

```env
PLC_IP=192.168.0.1     # S7-1500 IP address on the industrial network
PLC_RACK=0             # CPU rack number (default: 0)
PLC_SLOT=1             # CPU slot number (default: 1 for S7-1500)
PLC_DB=1               # Data block number
FLASK_DEBUG=0          # Set to 1 for development hot-reload
```

---

## Docker Commands Reference

```powershell
# Initial build and start
docker compose up -d --build

# View real-time logs
docker compose logs -f

# Rebuild after dependency change (requirements.txt, Dockerfile)
docker compose up -d --build

# Open a shell inside the container (debugging)
docker compose exec app bash

# Stop all services
docker compose down

# Download process log
# → open http://localhost:5000/api/export/csv in browser

# Check system status (PLC connection, log stats)
# → open http://localhost:5000/api/status in browser
```

---

## PLC Connection — Checklist (Friday)

- [ ] Verify network connectivity: `ping <PLC_IP>` from the host
- [ ] TIA Portal: PUT/GET access enabled in CPU Protection settings
- [ ] Update `PLC_IP` in `.env`
- [ ] Update DB number in `plc_connector.py` (`DB_NUMBER`) if different from DB1
- [ ] Verify memory offsets match TIA Portal DB layout
- [ ] Rebuild container: `docker compose up -d --build`
- [ ] Check connection status: `http://localhost:5000/api/status`

---

## PID Controller

The PID visualiser runs client-side (JavaScript) for display purposes.
Gains Kp, Ki, Kd are adjustable from the interface at runtime.
When connected to the real S7-1500, the PID loop runs inside the
TIA Portal FB PID_Compact block; the web interface acts as a supervisor only.
