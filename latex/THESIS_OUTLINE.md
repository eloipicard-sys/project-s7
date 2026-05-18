# Thesis Outline — Detailed Plan
## Supervision and Cascade Control of a Thermal Process on Siemens S7-1500 PLC with Embedded Web Interface

**Author:** Eloi Picard — ICAM Engineering School
**Academic year:** 2025–2026
**Estimated length:** 50–60 pages (excluding appendices)
**Language:** English

---

## Front Matter

### Cover Page
- Title, author, institution (ICAM), academic year
- Supervisor name (Michal)
- Logo ICAM

### Abstract *(½ page EN + ½ page FR)*
**English:**
This thesis presents the design and implementation of a real-time supervision and cascade control system for a thermal process based on a Siemens S7-1500 programmable logic controller. The system monitors a plate heat exchanger installation in which a hot fluid heated by an electric furnace exchanges heat with a cold counter-current flow. A Flask-based web application communicates with the PLC via two protocols: Snap7 for direct data block access and Open Pipe for WinCC Unified tag exchange. A step-response identification experiment is conducted in open loop to extract the process gain K, time constant τ, and dead time θ. Based on these parameters, an IMC-tuned PI controller with proportional-on-measurement action is implemented for the inner loop (Tin1 → F1), while a proportional outer controller manages the cascade (Tout2_SP → Tin1_SP). The supervision interface is deployed on a Siemens SIMATIC Unified 7" panel via Industrial Edge, providing real-time P&ID visualization and setpoint control.

**Keywords:** PLC, S7-1500, cascade control, process identification, Flask, Docker, WinCC Unified, Industrial Edge, heat exchanger, PI controller

**Français :**
Ce mémoire présente la conception et l'implémentation d'un système de supervision temps réel et de contrôle en cascade d'un procédé thermique basé sur un automate Siemens S7-1500. [version française de l'abstract]

---

### Acknowledgements *(¼ page)*
- Michal (lab supervisor, process expertise)
- ICAM teaching staff

### Table of Contents
### List of Figures
### List of Tables
### List of Abbreviations

| Abbreviation | Meaning |
|---|---|
| PLC | Programmable Logic Controller |
| HE | Heat Exchanger |
| PI | Proportional-Integral |
| IMC | Internal Model Control |
| FOPTD | First-Order Plus Time Delay |
| P&ID | Piping and Instrumentation Diagram |
| OB | Organization Block |
| FC | Function |
| DB | Data Block |
| API | Application Programming Interface |
| REST | Representational State Transfer |

---

## Chapter 1 — Introduction *(4 pages)*

### 1.1 Industrial Context *(1 page)*
**Content to write:**
- Thermal process control is ubiquitous in chemical, food, and energy industries
- Modern requirements: remote monitoring, real-time data, web-accessible HMI
- Gap: traditional SCADA systems are expensive and proprietary vs. open web technologies
- Opportunity: combining industrial-grade PLCs with modern web frameworks
- Mention the lab installation at ICAM as a representative testbed

**Key message:** Industrial automation is evolving toward web-based supervision; this project bridges PLC-level control with modern web technologies.

### 1.2 Problem Statement *(½ page)*
**Content to write:**
- The heat exchanger outlet temperature (Tout2) must be regulated despite disturbances
- Simple PID on Tout2 is slow due to the cascade of thermal dynamics
- Cascade control offers faster disturbance rejection but requires parameter identification
- No existing web interface for this installation — operators lack real-time visibility

### 1.3 Objectives *(½ page)*
**Content to write:**
Three main objectives:
1. Build a real-time web supervision system communicating with the S7-1500 PLC
2. Identify the dynamic model of the thermal process experimentally
3. Implement and validate a cascade PI+P control strategy

### 1.4 Thesis Structure *(¼ page)*
Brief description of each chapter.

### 1.5 Scope and Limitations *(¼ page)*
- Scope: HE-001 installation, inner loop identification, software implementation
- Out of scope: full outer loop identification (single session), safety interlocks, industrial certification

---

## Chapter 2 — The Thermal Process *(7 pages)*

### 2.1 Installation Overview *(1.5 pages)*
**Content to write:**
- Description of the laboratory installation
- Electric furnace heats a hot fluid circuit (F1)
- Plate heat exchanger HE-001: hot fluid (F1) vs. cold fluid (F2), counter-current configuration
- Two temperature measurement points per fluid stream: inlet and outlet of HE-001
- Flow measurement via electromagnetic flowmeters on F1 and F2
- Valve control: Valve_F1 (Word, %QW8), Valve_F2 (Int, %QW4)

**Figure to include:** P&ID diagram of the installation (based on schema.html SVG)
```
[FURNACE] → T_hin → T_hout/Tin1_HE1 → [HE-001] → Tout1_HE1 → HOT OUT
                                            ↕ (counter-current)
                         Tin2_HE1 ← [HE-001] ← Tout2_HE1 ← COLD IN
```

### 2.2 Instrumentation and Signals *(2 pages)*
**Content to write:**
- Temperature sensors: thermocouple or PT100, raw signal on %IW (0–27648 integers), scaled to °C in %MD
- Flow sensors: electromagnetic flowmeters, 4–20 mA output, scaled in m³/h
- Valve actuators: analog output %QW, 0–27648 = 0–100% opening
- Power output: Boolean %Q0.3 (furnace ON/OFF)

**Table to include:** Complete instrument list

| Tag | Address | Type | Range | Unit | Description |
|-----|---------|------|-------|------|-------------|
| T_hin | %MD16 | Real | 0–300 | °C | Furnace inlet temperature |
| T_hout / Tin1_HE1 | %MD12 / %MD48 | Real | 0–300 | °C | Furnace outlet / HE hot inlet |
| Tout1_HE1 | %MD44 | Real | 0–300 | °C | HE hot outlet |
| Tin2_HE1 | %MD40 | Real | 0–300 | °C | HE cold inlet |
| Tout2_HE1 | %MD52 | Real | 0–300 | °C | HE cold outlet |
| F1 | %MD28 | Real | 0–10 | m³/h | Hot flow rate |
| F2 | %MD32 | Real | 0–10 | m³/h | Cold flow rate |
| Valve_F1 | %QW8 | Word | 0–27648 | — | Hot valve command |
| Valve_F2 | %QW4 | Int | 0–27648 | — | Cold valve command |

### 2.3 Process Physics *(2 pages)*
**Content to write:**
- Heat exchanger thermal model: LMTD (Log Mean Temperature Difference) approach
- Simplified 1st-order dynamic: increasing F1 brings more energy → Tin1 rises
- Why Tout2 responds slowly to F1_SP changes: two-stage dynamics (furnace → Tin1 → HE → Tout2)
- This two-stage structure naturally motivates cascade control

**Equations to include:**
```
Q = U × A × LMTD
LMTD = (ΔT1 - ΔT2) / ln(ΔT1/ΔT2)
```

**Figure to include:** Qualitative step response of Tin1 and Tout2 to a F1_SP step (expected shape — S-curve with different time constants)

### 2.4 Control Objectives *(1 page)*
**Content to write:**
- Primary objective: regulate Tout2_HE1 to a setpoint (e.g., 45°C)
- Secondary objective: reject disturbances (changes in T_hin, F2)
- Constraints: F1_SP within [F1_min, F1_max], smooth valve operation (no oscillations)
- Performance metrics: settling time, overshoot, steady-state error

### 2.5 Operating Point *(½ page)*
**Content to write:**
- Nominal operating conditions from experimental session (to be completed after session with Michal)
- Placeholder for: T_hin_nom, F1_nom, Tin1_nom, Tout2_nom

---

## Chapter 3 — Siemens S7-1500 and TIA Portal *(9 pages)*

### 3.1 S7-1500 PLC Architecture *(2 pages)*
**Content to write:**
- S7-1500 CPU overview: CPU 1516-3 PN (or actual model), memory organization
- Scan cycle: input update → OB1 execution → output update
- Memory areas:
  - `%I` (Process Image Input): analog input readings at start of scan
  - `%Q` (Process Image Output): analog/digital outputs updated end of scan
  - `%M` (Bit memory / Merkers): global flags and computed values
  - `DB` (Data Blocks): structured storage, accessible via Snap7
- Communication interfaces: PROFINET, Snap7 (TCP/ISO on TCP port 102)

**Figure:** S7-1500 memory organization diagram

### 3.2 TIA Portal V18 Configuration *(2.5 pages)*
**Content to write:**

**3.2.1 Hardware configuration**
- CPU slot, rack configuration
- Analog input modules (AI): address assignment for %IW channels
- Analog output modules (AO): address assignment for %QW channels
- Importance of module order for address allocation

**3.2.2 Tag table (PLC tags)**
- 21 process tags defined (see Chapter 2 table)
- Naming convention adopted: English, HE1 suffix for heat exchanger variables
- Direct mapping: %IW (raw ADC) and %MD (scaled engineering units)

**3.2.3 OB1 and scaling FC**
- OB1: main cyclic program block, called every scan cycle
- FC scaling: converts raw %IW integer values (0–27648) to engineering units (°C, m³/h)
- Scaling formula: `value = (raw / 27648) × (max - min) + min`
- Result written to %MD addresses

**3.2.4 DB1 for Snap7 access**
- Non-optimized block access: mandatory for absolute addressing via Snap7
- Structure: 5 variables in fixed order (DBD0, DBD4, DBD8, DBD12, DBW16)
- FC in OB1 copies %MD values into DB1 each cycle

**Figure:** TIA Portal block diagram (OB1 → FC_scale → %MD → FC_DB1_update → DB1)

### 3.3 WinCC Unified and SIMATIC Panel 7" *(2.5 pages)*
**Content to write:**

**3.3.1 WinCC Unified Runtime**
- Tag table in WinCC mirrors PLC tags (same addresses)
- Screen: Synoptique displayed on 7" touchscreen (800×480 or 1280×800)
- Real-time update of tag values via PROFINET PLC connection

**3.3.2 Open Pipe communication**
- What is Open Pipe: Unix domain socket provided by WinCC Unified on the panel
- Allows external applications (running in Docker on Edge) to read/write WinCC tags
- Socket location: `/tmp/siemens/automation/openpipe.sock` (mapped via Docker volume)
- Protocol: newline-delimited JSON over Unix domain socket
  ```json
  Request:  {"action": "read", "tags": ["Tin1_HE1", "F1_SP"]}
  Response: {"Tin1_HE1": 75.3, "F1_SP": 3.0}
  ```
- Write: `{"action": "write", "tag": "F1_SP", "value": 3.5}`
- Advantage over Snap7: no raw byte offset, uses tag names directly

**Note:** Protocol format to be confirmed with Siemens documentation (pending session with Michal)

**3.3.3 Simulation fallback**
- When Open Pipe socket is unavailable (development on PC), `openpipe_connector.py` returns plausible simulated values
- Enables full UI development and testing without physical PLC access

### 3.4 Industrial Edge Deployment *(2 pages)*
**Content to write:**

**3.4.1 Industrial Edge architecture**
- Edge Runtime installed on SIMATIC Panel 7"
- Runs Docker containers natively on the panel
- App Publisher tool: packages Docker Compose application as `.app` file
- Port constraints: external ports must be in range 30000–35000
- This project: published on port 30500

**3.4.2 Docker Compose configuration**
```yaml
services:
  app:
    image: project-s7-app
    ports:
      - "30500:5000"
    mem_limit: 256m
    volumes:
      - /tmp/siemens/automation:/tempcontainer/
```
- Volume mount: gives Docker container access to Open Pipe socket
- Memory limit: 256 MB (panel hardware constraint)

**3.4.3 Deployment process**
1. Build image with `docker compose build` on PC
2. Import in App Publisher → validate configuration → publish as `.app`
3. Transfer `.app` to panel via Edge Management Console (requires license credentials)
4. Panel runs the app → accessible at `http://192.168.1.200:30500`

**3.4.4 Status at writing**
- `.app` file generated successfully
- Import pending: license credentials not yet obtained
- Development and testing run on PC Docker (port 5000) over lab network

---

## Chapter 4 — Software Architecture *(9 pages)*

### 4.1 Technology Stack *(1 page)*
**Content to write:**
- Why Python/Flask: rapid development, rich ecosystem, Snap7 binding available
- Why Socket.IO: bidirectional real-time push without polling (WebSocket with fallback)
- Why Docker: reproducible deployment on any host (PC, Pi, panel Edge)
- Why Chart.js: lightweight, no server-side rendering, runs in browser
- Comparison with classical SCADA approach: cost, flexibility, maintainability

**Table:** Technology choices summary

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Web server | Flask (Python) | Lightweight, REST + SocketIO |
| Real-time | Socket.IO | WebSocket push, multi-client |
| PLC comm. (direct) | Snap7 | Open-source S7 TCP library |
| PLC comm. (tags) | Open Pipe | Native WinCC Unified interface |
| Frontend | HTML/CSS/JS + Chart.js | No framework overhead |
| Containerization | Docker | Reproducible on PC and Edge |
| Data persistence | CSV (append-only) | Simple, portable |

### 4.2 Application Structure *(1.5 pages)*
**Content to write:**
- Module overview and responsibilities (table)
- Threading model: 3 daemon threads + Flask/SocketIO main thread
- Singleton pattern: one PLCConnector, one OpenPipeConnector, one CascadeController, one StepIdentifier

**Figure:** Module dependency diagram

**Table:** Thread responsibilities

| Thread | Module | Period | Role |
|--------|--------|--------|------|
| Flask/SocketIO | main.py | event-driven | HTTP routes + WebSocket |
| sim-loop | main.py | 3 s | Advance thermal simulation (fallback) |
| plc-poll | main.py | 3 s | Read DB1 via Snap7 when PLC connected |
| openpipe-poll | main.py | 3 s | Read 21 tags + run cascade + emit events |

### 4.3 PLC Communication Layer *(2 pages)*
**Content to write:**

**4.3.1 Snap7 — Direct DB access**
- `plc_connector.py`: wraps python-snap7 library
- Connection to S7-1500 at IP:port, rack 0, slot 1
- `read_process_data()`: reads DB1 at absolute offsets (DBD0, DBD4, DBD8, DBD12, DBW16)
- `write_temperature_setpoint()`, `write_flow_setpoint()`: write to DB1
- Priority: when PLC connected, Snap7 data overrides simulation
- Error handling: connection retry, graceful fallback to simulation

**4.3.2 Open Pipe — WinCC tag access**
- `openpipe_connector.py`: Unix socket JSON communication
- `read_all_tags()`: reads all 21 WinCC tags in a single request
- `write_tag(name, value)`: writes a single tag (F1_SP, F2_SP)
- Availability check: socket existence at startup
- Simulation fallback: returns plausible values when socket unavailable

**Why two protocols:**
- Snap7 reads DB1 → used by the legacy Monitor page and historical logger
- Open Pipe reads all 21 WinCC tags → used by Synoptique, Process, Cascade pages
- Both coexist without conflict

### 4.4 Real-Time Data Flow *(1.5 pages)*
**Content to write:**
- Socket.IO events:
  - `process_data`: emitted by sim-loop/plc-poll (basic 5-variable snapshot)
  - `process_tags`: emitted by openpipe-poll (all 21 tags)
  - `cascade_data`: emitted by openpipe-poll (controller state)
  - `ident_update`: emitted during identification (status + chart data)
- Client-side: each page subscribes to relevant events, updates DOM
- Data source indicator: `source` field = `"OPENPIPE"` / `"SIMULATION"` / `"PLC"`

**Figure:** Socket.IO event flow diagram (server → broadcast → multiple clients)

### 4.5 REST API *(1 page)*
**Content to write:**
Summary of HTTP endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/data` | Current process snapshot (5 vars) |
| POST | `/api/setpoint` | Update temperature or flow setpoint |
| GET | `/api/process/data` | All 21 WinCC tags |
| POST | `/api/process/write` | Write F1_SP or F2_SP |
| GET | `/api/cascade/status` | Cascade controller state |
| POST | `/api/cascade/mode` | Switch Manual / Auto-inner / Auto-full |
| POST | `/api/cascade/setpoint` | Set Tout2_SP or Tin1_SP |
| POST | `/api/cascade/params` | Set controller gains |
| POST | `/api/identification/start` | Start step test |
| POST | `/api/identification/cancel` | Cancel and restore F1_SP |
| GET | `/api/identification/status` | Identification state + result |
| GET | `/api/export/csv` | Download process log |
| GET | `/health` | Docker healthcheck |

### 4.6 Data Persistence *(½ page)*
**Content to write:**
- `logger.py`: append-only CSV at `/app/logs/process_data.csv`
- Docker volume mount: `./logs:/app/logs` — survives container restarts
- Fields: timestamp, temperature, flow_rate, setpoints, valve_state, source
- Export: `GET /api/export/csv` with timestamped filename

### 4.7 Web Interface Pages *(1.5 pages)*
**Content to write:**
Brief description of each page

**4.7.1 Synoptique (`/schema`)** — Primary panel display
- Full-screen SVG P&ID with animated flow lines
- 10 live values overlaid on the diagram
- Touch-friendly setpoint controls (F1_SP, F2_SP) with ±0.1 increments
- Optimised for 7" screen: no scroll, large touch targets

**4.7.2 Cascade (`/cascade`)** — Identification and control setup (PC use)
- Tab 1 — Identification: step test form, live Chart.js with dual Y-axis, IMC results table
- Tab 2 — Cascade control: visual schema, parameter forms, mode buttons, status grid

**4.7.3 Process (`/process`)** — Debug tag monitor
- 21 tags displayed in 3 sections (Furnace, HE1 hot side, HE1 cold side)
- Color-coded valve states (OPEN/PARTIAL/CLOSED)

**4.7.4 Monitor (`/`)** — Historical chart
- Chart.js time-series of temperature and flow
- Alarm logic, setpoint controls, CSV export button

---

## Chapter 5 — Process Identification *(9 pages)*

### 5.1 Theoretical Background *(2 pages)*
**Content to write:**

**5.1.1 First-Order Plus Time Delay (FOPTD) model**
The inner loop dynamic (F1_SP → Tin1) can be approximated by:
```
G(s) = K × e^(−θs) / (τs + 1)
```
Where:
- K [°C / (m³/h)] — static gain
- τ [s] — time constant (63.2% of steady-state response)
- θ [s] — dead time (transport delay)

**Justification:** Thermal systems with single dominant time constant → FOPTD is standard first approximation. Higher-order effects neglected for controller design purposes.

**5.1.2 Step response characterization**
From a step input ΔF1_SP at t = 0:
- K = ΔTin1_∞ / ΔF1_SP
- τ: time from step to reach Tin1_base + 0.632 × ΔTin1_∞
- θ: delay before first measurable response (|ΔTin1| > 2% of total step)

**Figure:** Ideal FOPTD step response annotated with K, τ, θ

**5.1.3 IMC tuning rules**
Internal Model Control (IMC) tuning for PI:
```
Kp = τ / (K × (λ + θ))
Ti = τ
```
λ = desired closed-loop time constant (tuning parameter):
- λ = 0.5τ → aggressive (fast, more overshoot)
- λ = τ → balanced (recommended starting point)
- λ = 2τ → conservative (slow, robust)

**Advantage of IMC over Ziegler-Nichols:** direct relationship between λ and closed-loop bandwidth; easy detuning if oscillations occur.

### 5.2 Experimental Protocol *(1.5 pages)*
**Content to write:**

**5.2.1 Pre-test conditions**
- Installation at steady state (≥ 30 min warm-up)
- Cascade controller in Manual mode
- Baseline F1_SP at nominal operating point
- Record: T_hin, Tin1_HE1, Tout2_HE1, F1, F2 at steady state

**5.2.2 Step application**
- Amplitude selection: 10–20% of F1 operating range
  - Too small: signal buried in noise; too large: nonlinear region
  - Recommended: +0.5 m³/h from nominal ≈ 3.0 m³/h
- Duration: minimum 3–4 × τ_estimated → 180 s used
- Implementation: `POST /api/identification/start` from `/cascade` page

**5.2.3 Acquisition**
- Sampling period: 3 s (dictated by Open Pipe poll rate)
- Variables recorded: Tin1_HE1, Tout2_HE1, F1_SP, F1 (actual)
- Baseline phase: 5 samples (15 s) averaged before step application
- Restoration: F1_SP automatically restored to baseline on test completion

**5.2.4 Identification resolution**
- With Ts = 3 s: τ resolution ≈ ±3 s (linear interpolation between samples)
- θ resolution: ±3 s (one sample period)
- For τ >> θ (typical thermal process), this is acceptable for PI tuning

### 5.3 Identification Results *(2.5 pages)*
**⚠ Section to be completed after session with Michal (2026-05-19)**

**5.3.1 Raw step response curves**
*[Figure placeholder: Chart with F1_SP step (right Y-axis) and Tin1 / Tout2 responses (left Y-axis) vs time]*

**5.3.2 Extracted parameters**

| Parameter | Value | Unit | Method |
|-----------|-------|------|--------|
| ΔF1_SP | TBD | m³/h | Input amplitude |
| ΔTin1_∞ | TBD | °C | Steady-state change |
| K | TBD | °C/(m³/h) | ΔTin1_∞ / ΔF1_SP |
| τ | TBD | s | 63.2% crossing |
| θ | TBD | s | First measurable response |

**5.3.3 Comparison with simulation model**
- Simulation uses K_proc = 220 (arbitrary unit), τ_T = 45 s
- After measurement: validate or update model parameters
- Discussion: simulation vs. real dynamics

**5.3.4 Model validation**
*[Figure placeholder: comparison between FOPTD model prediction and measured step response]*
- RMSE between model and measurement
- Discussion of model quality and validity domain

### 5.4 Controller Tuning *(2 pages)*
**Content to write:**

**5.4.1 IMC gain calculation**
Using identified K, τ, θ:

| Tuning | λ | Kp | Ti (s) |
|--------|---|-----|--------|
| Aggressive | 0.5τ | TBD | TBD |
| Normal | τ | TBD | TBD |
| Conservative | 2τ | TBD | TBD |

**5.4.2 Selection rationale**
- Start with Normal tuning for first closed-loop tests
- Tighten to Aggressive if response is too slow
- Back off to Conservative if oscillations appear
- Note: with Ts = 3 s sampling, gains must account for discrete-time approximation

**5.4.3 Discrete PI velocity form**
Chosen implementation: PI with proportional on measurement (P-on-M), velocity form:
```
Δu[k] = −Kp × (y[k] − y[k−1]) + (Kp / Ti) × e[k] × Ts
u[k]  = u[k−1] + Δu[k]
u[k]  = clamp(u[k], F1_min, F1_max)
```
**Advantage of velocity form:**
1. No proportional kick when setpoint changes
2. Bumpless transfer from manual: `u[k-1]` initialized to current manual output
3. Implicit anti-windup: output saturation prevents integral accumulation

---

## Chapter 6 — Cascade Control Implementation *(9 pages)*

### 6.1 Why Cascade Control *(1.5 pages)*
**Content to write:**

**6.1.1 Limitation of single-loop control on Tout2**
- Tout2 responds to F1_SP through two sequential dynamics:
  - F1_SP → Tin1 (inner, relatively fast, τ ≈ τ measured)
  - Tin1 → Tout2 (outer, slower, HE dynamics)
- A single PID on Tout2 must be detuned to avoid instability → slow response
- Any disturbance on T_hin or Tin1 propagates fully to Tout2 before correction

**6.1.2 Cascade principle**
- Inner loop (fast): regulates Tin1 by manipulating F1_SP — fast rejection of F1 disturbances
- Outer loop (slow): sets Tin1_SP based on Tout2 error — guides Tout2 to setpoint
- Key property: inner loop must be 3–5× faster than outer loop for cascade to improve performance

**Figure:** Block diagram comparing single-loop vs cascade structure

**6.1.3 Applicability condition**
- Required: measurable intermediate variable (Tin1) that influences the controlled variable (Tout2)
- Required: inner loop bandwidth >> outer loop bandwidth
- This installation: ✓ Tin1 measured, ✓ τ_inner < τ_outer (Tin1 responds faster than Tout2)

### 6.2 Inner Loop — PI+P Controller *(2.5 pages)*
**Content to write:**

**6.2.1 Controller structure**
PI with Proportional on Measurement (P-on-M), also called PI+P:
```
u[k] = u[k−1] − Kp×(y[k]−y[k−1]) + (Kp/Ti)×e[k]×Ts
```
Where y = Tin1 (measurement), e = Tin1_SP − Tin1 (error)

**Comparison with standard PI:**
| Property | Standard PI | PI+P (P on measurement) |
|---------|------------|------------------------|
| Setpoint step response | Proportional kick | No kick |
| Disturbance rejection | Identical | Identical |
| Implementation | Position form | Velocity form |
| Bumpless transfer | Requires special logic | Natural (u[k-1] init) |

**6.2.2 Anti-windup**
- Velocity form naturally limits integral wind-up: output is clamped each cycle
- If u[k] saturates, subsequent Δu is computed from the clamped value
- This prevents unbounded integral accumulation

**6.2.3 Bumpless transfer**
When switching from Manual to Auto:
- `inner.init_output(current_F1_SP, current_Tin1)` sets u[k-1] and y[k-1]
- First Δu is purely from the integral term (small), no step in F1_SP

**6.2.4 Output limits**
- F1_SP constrained to [F1_min, F1_max] (to be confirmed from installation specs)
- Default: [0.0, 10.0] m³/h

### 6.3 Outer Loop — Proportional Controller *(1.5 pages)*
**Content to write:**

**6.3.1 Structure**
```
Tin1_SP_cmd = Tin1_SP_base + Kp_ext × (Tout2_SP − Tout2)
```
- Tout2_SP: operator setpoint
- Tout2: measured cold outlet temperature
- Tin1_SP_base: operator-defined base setpoint for inner loop
- Kp_ext: outer proportional gain

**6.3.2 Steady-state analysis**
With a pure P outer loop:
- Inner loop (I term) ensures Tin1 → Tin1_SP_cmd exactly
- Tout2_ss from implicit equation: `Tout2_ss = f(Tin1_SP_base + Kp_ext×(Tout2_SP − Tout2_ss))`
- For linear process: `Tout2_ss = (K2×Kp_ext×Tout2_SP + K2×Tin1_SP_base + d) / (1 + K2×Kp_ext)`
- **Steady-state error:** exists unless K2×Kp_ext >> 1 or Tin1_SP_base tuned correctly

**6.3.3 Discussion: P vs PI outer**
- With P only: residual offset in Tout2 (acceptable if small, operator can trim Tin1_SP_base)
- With PI outer: zero offset guaranteed, but requires outer loop identification
- Decision: start with P outer, upgrade to PI after validating inner loop

### 6.4 Control Modes and State Machine *(1 page)*
**Content to write:**

**Three operating modes:**

| Mode | Inner loop | Outer loop | Operator inputs |
|------|-----------|-----------|----------------|
| MANUAL | OFF | OFF | F1_SP set directly |
| AUTO_INNER | ON | OFF | Tin1_SP set by operator |
| AUTO_FULL | ON | ON | Tout2_SP set by operator |

**Mode transitions:**
- MANUAL → AUTO_INNER: `init_output(current_F1_SP, current_Tin1)` → bumpless
- AUTO_INNER → AUTO_FULL: outer loop activates, overrides Tin1_SP — potential small bump if Tout2 error ≠ 0
- Any AUTO → MANUAL: controller output frozen at last value

**Safeguard:** identification (step test) is blocked when mode ≠ MANUAL to prevent controller–identification conflict.

### 6.5 Experimental Validation *(2.5 pages)*
**⚠ Section to be completed after closed-loop tests**

**6.5.1 Inner loop — setpoint step response**
*[Figure placeholder: Tin1 response to Tin1_SP step, with F1_SP output]*
- Metrics: rise time, settling time, overshoot, steady-state error
- Compare Normal vs Aggressive tuning

**6.5.2 Inner loop — disturbance rejection**
*[Figure placeholder: Tin1 response to T_hin disturbance (furnace power change)]*
- How quickly does inner loop reject disturbance before it reaches Tout2?

**6.5.3 Full cascade — Tout2 setpoint step**
*[Figure placeholder: Tout2 and Tin1 responses to Tout2_SP step]*
- Compare: cascade vs hypothetical single-loop (from simulation or literature)
- Demonstrate improved disturbance rejection

**6.5.4 Discussion**
- Observed steady-state error in Tout2 (P outer limitation)
- Sensitivity to Kp_ext tuning
- Practical recommendations for operator use

---

## Chapter 7 — Supervision Interface *(5 pages)*

### 7.1 Design Principles *(1 page)*
**Content to write:**
- Two distinct users: operator on panel (7" touchscreen) vs engineer on PC
- Panel interface: minimal interaction, maximum readability at distance, no scroll
- PC interface: rich information, configuration, analysis tools
- Common theme: industrial dark header, monospaced values, color-coded states

### 7.2 Synoptique — Panel Display *(1.5 pages)*
**Content to write:**
- SVG P&ID: animated flow lines (orange hot, blue cold), heat exchanger internals
- 10 live values as overlay cards (T_hin, T_hout, Tin1, Tout1, Tin2, Tout2, F1, F2, Valve_F1, Valve_F2)
- Furnace power indicator (color dot + ON/OFF text)
- F1_SP and F2_SP touch controls: long-press for rapid increment
- Socket.IO: updates every 3 s, source indicator (OPENPIPE/SIMULATION)
- Designed for 7" (800×480): tested for visibility at 1–2 m distance

**Figure:** Screenshot of Synoptique page

### 7.3 Cascade Page — Engineering Tool *(1.5 pages)*
**Content to write:**

**Identification tab:**
- Step test configuration: base F1_SP (auto-filled from PLC), amplitude, duration
- Progress: PRE-STEP baseline → STEP active (progress bar) → DONE
- Live Chart.js: Tin1 (red), Tout2 (orange dashed), F1_SP step (blue, right axis)
- Results: K, τ, θ KPI cards + IMC tuning table (3 rows × Apply button)

**Cascade tab:**
- Visual block diagram: Tout2_SP → [P] → Tin1_SP → [PI+P] → F1_SP
- Parameter forms: Kp/Ti inner, Kp outer, setpoints
- Mode buttons: MANUAL / AUTO INNER / AUTO FULL (bumpless switch)
- Status grid: live Tin1, Tout2, errors, F1_SP output

### 7.4 Real-Time Performance *(½ page)*
**Content to write:**
- Socket.IO latency: < 100 ms on local network (3 s poll → WebSocket push)
- Chart.js performance: up to ~100 data points with `animation: false` → no lag
- Browser compatibility: tested on Chrome/Edge (PC) and panel embedded browser

### 7.5 Deployment Summary *(½ page)*

| Environment | URL | Access |
|-------------|-----|--------|
| PC development | http://localhost:5000 | Local only |
| PC → Panel network | http://192.168.1.149:5000 | Lab network |
| Panel Edge (target) | http://192.168.1.200:30500 | Lab network (pending licenses) |

---

## Chapter 8 — Conclusion *(3 pages)*

### 8.1 Summary of Contributions *(1 page)*
**Content to write:**
- Implemented a complete real-time supervision system communicating with S7-1500 via dual protocol (Snap7 + Open Pipe)
- Conducted open-loop step identification experiment → extracted K, τ, θ
- Designed and implemented PI+P cascade controller in Python with bumpless transfer and anti-windup
- Built a web supervision interface suited for both panel (7" touch) and PC use
- Deployed via Docker for reproducible cross-platform execution

### 8.2 Results Assessment *(1 page)*
**Content to write:**
- Identification results: [to be completed]
- Controller performance: [to be completed]
- Interface usability: positive feedback from use on panel
- Open Pipe: pending validation with WinCC Unified real socket

### 8.3 Limitations *(½ page)*
**Content to write:**
- Sampling period of 3 s limits identification resolution (θ ± 3 s)
- Pure P outer loop introduces steady-state error in Tout2
- Open Pipe protocol not fully validated (socket format pending Michal confirmation)
- Industrial Edge deployment blocked on license credentials

### 8.4 Perspectives *(½ page)*
**Content to write:**
- Outer loop PI upgrade: identify Tout2 dynamics → tune outer IMC gains
- Increase sampling rate for identification (1 s possible with threading adjustment)
- Add alarm management: high-temperature cutoff on T_hin, flow fault detection
- PLC-side interlocks: integrate safety FC in TIA Portal
- Edge deployment completion: obtain licenses, final panel deployment

---

## References

*(To be completed during writing)*

- Seborg, D.E. et al., *Process Dynamics and Control*, Wiley, 4th ed., 2017
- Rivera, D.E. et al., "Internal model control", *IEC Proc.*, 1986 — IMC tuning rules
- Siemens, *S7-1500 System Manual*, 2023
- Siemens, *TIA Portal V18 Programming Guide*, 2023
- Siemens, *WinCC Unified Open Pipe Documentation*
- python-snap7 library documentation
- Flask documentation — https://flask.palletsprojects.com
- Socket.IO documentation — https://socket.io/docs

---

## Appendices

### Appendix A — WinCC Unified Tag Table (21 tags)
*(Full table with names, types, addresses — Chapter 2 table extended)*

### Appendix B — DB1 Structure for Snap7
| Offset | Type | Tag name | Description |
|--------|------|----------|-------------|
| DBD0 | Real | temperature | Measured temperature (Tin1) |
| DBD4 | Real | flow_rate | Measured flow rate (F1) |
| DBD8 | Real | setpoint_temp | Temperature setpoint |
| DBD12 | Real | setpoint_flow | Flow setpoint |
| DBW16 | Int | valve_state | 0=CLOSED, 1=OPEN, 2=PARTIAL |

### Appendix C — Key Code Extracts

**C.1 PI+P velocity form (cascade_controller.py)**
```python
def update(self, setpoint: float, measurement: float) -> float:
    if self._last_meas is None:
        self._last_meas = measurement
    error = setpoint - measurement
    delta_u = (-self.Kp * (measurement - self._last_meas)
               + (self.Kp / max(self.Ti, 0.01)) * error * self.dt)
    raw = self.last_output + delta_u
    clamped = max(self.out_min, min(self.out_max, raw))
    self.last_output = clamped
    self._last_meas = measurement
    return clamped
```

**C.2 IMC tuning (identification.py)**
```python
def imc(factor: float) -> dict:
    tau_c = max(factor * tau, theta)
    Kp = round(tau / (K * (tau_c + theta)), 4) if K != 0 else 0.0
    return {'Kp': Kp, 'Ti': round(tau, 1)}
```

**C.3 Open Pipe read (openpipe_connector.py)**
```python
def _read_via_socket(self, tag_names: list) -> dict:
    request = json.dumps({"action": "read", "tags": tag_names}) + "\n"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(2.0)
        s.connect(self._sock_path)
        s.sendall(request.encode())
        response = b""
        while True:
            chunk = s.recv(4096)
            if not chunk or b"\n" in response:
                break
            response += chunk
    return json.loads(response.split(b"\n")[0].decode())
```

### Appendix D — Step Response Experimental Results
*(Figures and raw data — to be completed after 2026-05-19 session)*

### Appendix E — User Manual (Supervision Interface)
*(Brief guide for lab operators — Synoptique and Cascade pages)*

---

## Writing Status Tracker

| Section | Status | Priority | Notes |
|---------|--------|----------|-------|
| Abstract | ✅ Done | High | EN + FR written in THESIS_DRAFT.md |
| Chapter 1 — Introduction | ✅ Done | High | Written in THESIS_DRAFT.md |
| Chapter 2 — Thermal process | 🟡 Partial | High | Written; §2.5 operating point TBD after session |
| Chapter 3 — S7-1500 & TIA Portal | ✅ Done | High | Written in THESIS_DRAFT.md |
| Chapter 4 — Software architecture | ✅ Done | Medium | Written in THESIS_DRAFT.md |
| Chapter 5 — Identification | 🟡 Partial | High | Theory + protocol done; §5.3 + §5.4 **waiting 2026-05-19** |
| Chapter 6 — Cascade control | 🟡 Partial | High | Design + implementation done; §6.5 **waiting closed-loop tests** |
| Chapter 7 — Interface | ✅ Done | Medium | Written in THESIS_DRAFT.md; screenshots TBD |
| Chapter 8 — Conclusion | 🟡 Partial | Low | Skeleton written; §8.2 results TBD |
| References | ✅ Done | Medium | 12 references listed |
| Appendices | ✅ Done | Low | A–E written; Appendix D TBD after session |

**Legend:** ✅ Done · 🟡 Partial · ⬜ To write

**Draft file:** `THESIS_DRAFT.md` (1522 lines — all chapters written)
