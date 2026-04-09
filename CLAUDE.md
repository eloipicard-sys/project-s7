# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

S7-1500 Thermal Process Monitor — a Flask-based web application for monitoring and controlling a Siemens S7-1500 PLC thermal process. Built as a thesis project with real-time visualization via Socket.IO and Chart.js. Runs in Docker with a simulation fallback when no PLC is connected.

## Commands

### Docker (primary workflow)
```bash
docker compose up -d --build   # Build and start
docker compose logs -f          # Tail logs
docker compose down             # Stop
docker compose exec app bash    # Open shell in container
```

### Local development (no Docker)
```bash
cd app
pip install -r requirements.txt
PLC_IP=192.168.1.100 FLASK_DEBUG=1 python main.py
```

### Verify running
```bash
curl http://localhost:5000/health
curl http://localhost:5000/api/data
```

## Architecture

### Components
| File | Role |
|------|------|
| `app/main.py` | Flask app, HTTP routes, Socket.IO events, background threads |
| `app/plc_connector.py` | Snap7 wrapper for S7-1500 TCP communication |
| `app/thermal_model.py` | First-order discrete-time simulation with P-controller |
| `app/logger.py` | CSV append-only log to `logs/process_data.csv` |
| `app/templates/index.html` | Main supervision UI (Chart.js, Socket.IO, alarm logic) |
| `app/templates/test.html` | PLC test variable read/write interface |

### Threading Model
`main.py` runs three concurrent threads:
- **Main Flask/SocketIO thread** — serves HTTP and WebSocket
- **`_simulation_loop`** — advances `ThermalProcessModel` every 3 s, protected by `_sim_lock`
- **`_plc_poll_loop`** — polls S7-1500 via Snap7 every 3 s, protected by `_setpoints_lock`

Data source priority: PLC (when connected) → simulation fallback. The `source` field in logs/API responses indicates which is active.

### PLC Memory Map (DB1)
| Address | Type | Variable |
|---------|------|----------|
| DB1.DBD0 | REAL | Measured temperature (°C) |
| DB1.DBD4 | REAL | Measured flow rate (m³/h) |
| DB1.DBD8 | REAL | Temperature setpoint (°C) |
| DB1.DBD12 | REAL | Flow rate setpoint (m³/h) |
| DB1.DBW16 | INT | Valve state (0=CLOSED, 1=OPEN, 2=PARTIAL) |

DB number is configurable via `PLC_DB` env var (default: 1).

### Key API Endpoints
- `GET /api/data` — current process snapshot (JSON)
- `POST /api/setpoint` — update temperature or flow setpoints
- `GET /api/export/csv` — download full CSV log
- `GET /api/status` — PLC connection state and log stats
- `GET /test` — PLC variable test interface (reads/writes V1–V9)

### Configuration (`.env`)
```
PLC_IP=192.168.1.100   # S7-1500 IP
PLC_RACK=0             # CPU rack
PLC_SLOT=1             # CPU slot (1 for S7-1500)
PLC_DB=1               # Data block number
FLASK_DEBUG=1          # Hot-reload
LOG_DIR=/app/logs      # CSV output directory
PORT=5000
```

### Docker Volume Mounts
- `./app` → `/app` — enables hot-reload without rebuild
- `./logs` → `/app/logs` — persists CSV data across container restarts
