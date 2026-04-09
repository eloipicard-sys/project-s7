# Deployment Options — S7-1500 Thermal Process Monitor
**Document prepared for:** Michal
**Context:** Master's thesis in Industrial Engineering — Flask-based supervision app (Python + snap7) for a Siemens S7-1500 thermal process

---

## Background

The supervision application is a Flask web server that:
- Reads/writes process data from the S7-1500 PLC via the snap7 protocol (TCP port 102)
- Provides a real-time web dashboard (Socket.IO + Chart.js)
- Logs process data to CSV
- Runs in Docker (already containerized)

The question is **where** to run this application alongside the existing SIMATIC HMI Unified Comfort Panel 7".

---

## Option 1 — Docker on the Unified Comfort Panel (with Edge License)

### How it works
The SIMATIC HMI Unified Comfort Panel ships with a built-in Industrial Edge Runtime (Docker-based). With the appropriate license, custom Docker applications can be deployed directly on the panel and run in parallel with WinCC Unified.

Deployment is done locally via the panel's built-in web interface ("Device-managed" mode) — no cloud IEM server required.

### Architecture
```
S7-1500 PLC
    ↕ Ethernet (snap7 / TCP:102)
Unified Panel 7"
    ├── WinCC Unified  (native HMI)
    └── Edge Runtime   (Docker)
            └── Flask app  ← our supervision application
```

### Requirements
- **License:** "Edge for Unified Panels" — approx. €450/panel (production)
  - Educational/academic license may be available through Siemens Education programs — to be confirmed
- **Docker image** must be rebuilt for **linux/arm64** (panel CPU is ARM-based)
- App is packaged with the free **Industrial Edge App Publisher (IEAP)** tool
- Imported via the panel's local web UI ("Import Offline") — no internet connection needed

### Advantages
- **No additional hardware** — panel serves as both HMI and edge computer
- Clean, compact industrial architecture
- Demonstrates Edge capabilities of modern Unified Panels — strong thesis value
- WinCC Unified and the Flask app coexist on the same device

### Constraints
- License cost (~€450), unless an educational license is granted
- Docker image must be cross-compiled for ARM64 (additional build step)
- Panel resources are shared (CPU/RAM) between WinCC Unified and Edge apps

---

## Option 2 — Python + Flask on a SIMATIC IPC

### How it works
A SIMATIC IPC (e.g., IPC427E or IPC677C) running Windows 10 IoT Enterprise acts as a standalone supervision computer. Python and Flask are installed natively, with no Docker or Edge stack required. The IPC connects to both the S7-1500 and the panel over Ethernet.

### Architecture
```
S7-1500 PLC  ←→  SIMATIC IPC (Flask app, Python, Docker)
                        ↕ Ethernet
              Unified Panel 7" (WinCC Unified — HMI only)
```

### Requirements
- Access to a SIMATIC IPC (justification needed)
- No additional licenses — standard Windows installation
- `pip install flask python-snap7` — runs as-is from the existing codebase

### Advantages
- **No license cost** beyond hardware
- Full flexibility: Python, Docker, databases, OPC UA — no restrictions
- Standard industrial architecture (IPC for SCADA/supervision is industry norm)
- Existing Docker image runs without modification (x86/amd64)

### Constraints
- Requires a second piece of hardware (IPC) — must be justified and sourced
- Higher overall cost if IPC must be purchased
- Slightly more complex network topology

---

## Option 3 — Raspberry Pi 4 (Fallback / Low-Cost)

### How it works
A Raspberry Pi 4 (ARM64, Debian Linux) runs Python + Flask + snap7 natively. It connects to the S7-1500 over Ethernet. The Unified Panel remains the WinCC HMI; the Pi handles supervision independently.

### Requirements
- Raspberry Pi 4 (4 GB RAM recommended) — approx. €80
- No licenses, standard Debian packages

### Advantages
- Lowest cost solution
- ARM64 — same architecture as the panel, so Docker images built for Option 1 are reusable
- Full Python/Docker freedom

### Constraints
- Not rated for industrial environments (temperature range, vibration, EMC)
- Acceptable for a thesis/lab environment, not for production deployment
- Requires justification as a non-Siemens component

---

## Comparison Summary

| Criterion | Option 1 — Panel Edge | Option 2 — SIMATIC IPC | Option 3 — Raspberry Pi |
|---|---|---|---|
| Additional hardware | None | IPC required | Pi required |
| License cost | ~€450 (edu TBD) | None | None |
| Hardware cost | None | ~€800–2000 | ~€80 |
| Docker image change | ARM64 rebuild needed | None (amd64) | ARM64 rebuild needed |
| Industrial rating | Yes (panel) | Yes (IPC) | No |
| Thesis relevance | High (Edge/IoT angle) | High (standard SCADA arch) | Medium |
| Setup complexity | Medium | Low | Low |

---

## PLC Prerequisites (all options)

Regardless of the chosen deployment option, two settings must be configured in TIA Portal on the S7-1500:

1. **CPU Properties → Protection → enable "Permit access with PUT/GET communication"**
2. **Each DB used by the app → uncheck "Optimized block access"** (standard/absolute addressing required)

---

## Recommendation

**Option 1** is the most academically compelling choice — it demonstrates a complete, modern industrial architecture on a single Siemens device. The main question is whether an **educational Edge license** can be obtained through Siemens Education France or an institutional agreement.

**Option 2** is the most pragmatic fallback if the license is unavailable — no code changes, no license cost, standard industrial topology.

**Option 3** is valid for a lab/thesis context if neither hardware nor license budget is available.
