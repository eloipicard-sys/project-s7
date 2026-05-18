# Supervision and Cascade Control of a Thermal Process on a Siemens S7-1500 PLC with Embedded Web Interface

**Author:** Eloi Picard
**Institution:** ICAM Engineering School
**Academic year:** 2025–2026
**Supervisor:** Michal [Last name to be confirmed]

---

## Abstract

This thesis presents the design and implementation of a real-time supervision and cascade control system for a thermal process based on a Siemens S7-1500 programmable logic controller. The installation under study consists of a plate heat exchanger in which a hot fluid, pre-heated by an electric furnace, exchanges energy in counter-current with a cold fluid circuit. A Flask-based web application communicates with the PLC via two complementary protocols: Snap7 for direct access to a structured data block (DB1), and the Siemens Open Pipe mechanism for reading and writing WinCC Unified tags over a Unix domain socket.

An open-loop step-response identification experiment is conducted on the inner process (F1_SP → Tin1_HE1) to extract the three parameters of a First-Order Plus Time Delay model: static gain K, time constant τ, and dead time θ. These parameters are used to tune a PI controller with proportional action on the measurement (PI+P) using Internal Model Control rules. This controller forms the inner loop of a cascade architecture, regulating the heat exchanger hot inlet temperature (Tin1). An outer proportional controller closes the cascade by driving Tin1 toward the setpoint required to achieve the desired cold outlet temperature (Tout2).

The supervision interface runs inside a Docker container and is accessible both from a PC on the laboratory network and, after deployment via Siemens Industrial Edge, from the embedded browser of a SIMATIC Unified 7" touch panel. The interface provides a real-time P&ID synoptic, a cascade identification and commissioning page, and a full process tag monitor.

**Keywords:** PLC, S7-1500, cascade control, process identification, Flask, Docker, WinCC Unified, Industrial Edge, heat exchanger, PI+P controller, IMC tuning

---

## Résumé

Ce mémoire présente la conception et l'implémentation d'un système de supervision temps réel et de contrôle en cascade d'un procédé thermique basé sur un automate Siemens S7-1500. L'installation étudiée est un échangeur de chaleur à plaques dans lequel un fluide chaud, préchauffé par un four électrique, échange de l'énergie à contre-courant avec un circuit froid. Une application web développée en Flask communique avec l'automate via deux protocoles complémentaires : Snap7 pour l'accès direct à un bloc de données (DB1), et le mécanisme Open Pipe de Siemens pour la lecture et l'écriture des variables WinCC Unified.

Une expérience d'identification en boucle ouverte par test échelon est conduite sur le processus interne (F1_SP → Tin1_HE1) afin d'extraire les paramètres d'un modèle du premier ordre avec retard : gain statique K, constante de temps τ et retard pur θ. Ces paramètres sont utilisés pour régler un régulateur PI avec action proportionnelle sur la mesure (PI+P) selon les règles IMC. Ce régulateur constitue la boucle interne d'une structure en cascade, régulant la température d'entrée chaude de l'échangeur (Tin1). Une boucle externe proportionnelle ferme la cascade en pilotant Tin1 vers la consigne nécessaire pour atteindre la température de sortie froide souhaitée (Tout2).

L'interface de supervision fonctionne dans un conteneur Docker et est accessible depuis un PC du réseau de laboratoire ainsi que, après déploiement via Siemens Industrial Edge, depuis le navigateur intégré d'un panel SIMATIC Unified 7 pouces tactile.

**Mots-clés :** automate programmable, S7-1500, contrôle en cascade, identification de procédé, Flask, Docker, WinCC Unified, Industrial Edge, échangeur de chaleur, régulateur PI+P, méthode IMC

---

## Acknowledgements

I would like to express my sincere gratitude to Michal, my laboratory supervisor at ICAM, whose process expertise, guidance, and patience throughout the experimental sessions were invaluable to the success of this project. His practical knowledge of the S7-1500 installation and Siemens tools significantly accelerated my understanding of industrial automation systems.

I also thank the faculty and staff of ICAM Engineering School for providing access to the laboratory facilities and for the support offered throughout the academic year.

---

## Table of Contents

1. Introduction
2. The Thermal Process
3. Siemens S7-1500 and TIA Portal
4. Software Architecture
5. Process Identification
6. Cascade Control Implementation
7. Supervision Interface
8. Conclusion

Appendix A — WinCC Unified Tag Table
Appendix B — DB1 Structure for Snap7
Appendix C — Key Code Extracts
Appendix D — Step Response Experimental Results
Appendix E — User Manual

---

## List of Abbreviations

| Abbreviation | Meaning |
|---|---|
| ADC | Analog-to-Digital Converter |
| API | Application Programming Interface |
| CPU | Central Processing Unit |
| DB | Data Block (Siemens S7) |
| FC | Function (Siemens TIA Portal block type) |
| FOPTD | First-Order Plus Time Delay |
| HE | Heat Exchanger |
| HMI | Human–Machine Interface |
| IMC | Internal Model Control |
| I/O | Input / Output |
| JSON | JavaScript Object Notation |
| LMTD | Log Mean Temperature Difference |
| OB | Organization Block (Siemens S7) |
| P&ID | Piping and Instrumentation Diagram |
| PI | Proportional-Integral |
| PLC | Programmable Logic Controller |
| P-on-M | Proportional on Measurement |
| REST | Representational State Transfer |
| SCADA | Supervisory Control and Data Acquisition |
| TCP/IP | Transmission Control Protocol / Internet Protocol |
| WS | WebSocket |

---

# Chapter 1 — Introduction

## 1.1 Industrial Context

Thermal processes are among the most common applications of automatic control in industry. Whether in chemical reactors, food processing lines, pharmaceutical production, or power generation systems, the ability to regulate temperatures precisely and reliably directly determines product quality, energy efficiency, and process safety. A plate heat exchanger, for example, appears at every scale of industrial production: from pasteurization of beverages to cooling of power electronics and conditioning of building HVAC systems.

The supervision of such processes has historically relied on dedicated SCADA (Supervisory Control and Data Acquisition) systems — proprietary software suites connected to programmable logic controllers via industrial fieldbus protocols. While reliable and certified, classical SCADA systems carry significant costs in licensing, hardware, and engineering time. Their interfaces, designed for control-room workstations, are not naturally suited to the web-connected, multi-device environments that modern facilities increasingly demand.

Over the past decade, the convergence of industrial automation and information technology has given rise to a new paradigm often called Industrial IoT (IIoT) or Industry 4.0. In this paradigm, PLCs and sensors publish data to web-accessible services; dashboards run in standard browsers; and control logic can be deployed as containerized software on hardware directly integrated into the control cabinet or operator panel. Siemens' Industrial Edge platform is a concrete realization of this vision: it allows Docker containers to run natively on a SIMATIC Unified panel, inches from the process they supervise.

This project is situated precisely at this intersection. The installation used is a laboratory-scale thermal rig at ICAM Engineering School, equipped with a Siemens S7-1500 PLC, a plate heat exchanger, an electric furnace, and a SIMATIC Unified 7" touch panel. It provides a representative testbed to explore how modern web technologies — Python, Flask, Socket.IO, Chart.js, Docker — can be combined with an industrial-grade controller to deliver a complete supervision and control solution without the cost or rigidity of a classical SCADA system.

## 1.2 Problem Statement

The process under study is a plate heat exchanger in which a hot fluid (circuit F1), pre-heated by an electric furnace, transfers heat to a cold counter-current fluid (circuit F2). The primary control objective is to maintain the cold outlet temperature Tout2_HE1 at a desired setpoint, despite disturbances arising from changes in furnace temperature or cold circuit flow rate.

A straightforward approach would be to apply a single PID controller acting directly on Tout2_HE1 by manipulating the hot flow setpoint F1_SP. However, this approach faces a fundamental limitation: the dynamic path from F1_SP to Tout2_HE1 passes through two sequential processes — the furnace (F1_SP → Tin1_HE1) and the heat exchanger (Tin1_HE1 → Tout2_HE1). The combined transfer function exhibits a relatively large apparent time delay and a long settling time. A controller tuned aggressively enough to achieve good setpoint tracking will tend to oscillate; one tuned conservatively will be too slow to reject disturbances before they affect Tout2.

Cascade control offers an elegant solution to this problem. By introducing an intermediate measurement — the heat exchanger hot inlet temperature Tin1_HE1 — and dedicating a fast inner control loop to regulate it, disturbances in the hot circuit are corrected before they propagate to the cold outlet. An outer loop then adjusts the Tin1 setpoint to guide Tout2 toward the desired value. This structure improves both setpoint tracking and disturbance rejection compared to a single-loop strategy.

A second problem addressed in this project is the absence of any web-based supervision interface for this installation. Operators currently have no real-time visibility into the process state from a network-connected device. The panel displays a static WinCC Unified screen, but no data logging, trend charts, or remote accessibility exist. Building such an interface, deployable both on a PC and directly on the panel via Industrial Edge, represents a significant operational improvement.

## 1.3 Objectives

This project pursues three main objectives:

**Objective 1 — Real-time web supervision.** Design and implement a web application that communicates with the S7-1500 PLC in real time, displays all relevant process variables (temperatures, flow rates, valve positions, furnace state), provides setpoint controls, and logs data to a persistent file. The interface must be accessible both from a workstation and from the embedded browser of the SIMATIC Unified 7" panel.

**Objective 2 — Experimental process identification.** Conduct an open-loop step-response test on the inner process (F1_SP → Tin1_HE1) to extract the parameters of a First-Order Plus Time Delay (FOPTD) model. Use these parameters to calculate PI controller gains according to Internal Model Control (IMC) tuning rules, providing three levels of aggressiveness for the engineer to choose from.

**Objective 3 — Cascade control implementation and validation.** Implement a cascade controller in Python comprising: (a) an inner PI loop with proportional action on measurement, regulating Tin1_HE1 by manipulating F1_SP; and (b) an outer proportional controller, converting a Tout2_HE1 setpoint into a Tin1_HE1 setpoint. The implementation must include bumpless mode transfer, anti-windup, and a three-mode operating interface (Manual / Auto-Inner / Auto-Full).

## 1.4 Thesis Structure

**Chapter 2** describes the physical installation: the electric furnace, the plate heat exchanger, the instrumentation (temperature sensors, flow meters, valve actuators), and the control objectives derived from the process physics.

**Chapter 3** covers the Siemens S7-1500 PLC, its memory organization and scan cycle, TIA Portal V18 configuration (tag table, scaling functions, DB1), WinCC Unified on the 7" panel, the Open Pipe communication mechanism, and Industrial Edge deployment.

**Chapter 4** presents the software architecture: technology choices, the multi-threaded Flask application, the two PLC communication layers (Snap7 and Open Pipe), real-time data flow via Socket.IO, the REST API, and the four web interface pages.

**Chapter 5** develops the theory of FOPTD process identification by step response and IMC tuning, then presents the experimental protocol and results obtained from the installation.

**Chapter 6** details the cascade control design: justification of the cascade structure, the inner PI+P controller (velocity form, bumpless transfer, anti-windup), the outer proportional controller, the operating mode state machine, and experimental validation.

**Chapter 7** describes the supervision interface design: the panel-optimised P&ID synoptic, the cascade commissioning page, and real-time performance characteristics.

**Chapter 8** concludes with a summary of contributions, a critical assessment of results, current limitations, and perspectives for future work.

## 1.5 Scope and Limitations

This project focuses on the HE-001 plate heat exchanger installation at ICAM. The identification and control work is limited to the inner loop (F1_SP → Tin1_HE1). The outer loop uses a proportional controller whose gain is set manually; a full outer loop identification is left for future work.

The web application is implemented as a proof-of-concept demonstrator with an emphasis on functionality and real-time performance. It does not include industrial certification (IEC 61508/62061), formal safety interlocks, or redundancy mechanisms. The Open Pipe communication protocol is implemented based on the available documentation and confirmed with the laboratory supervisor; its full validation against the final WinCC Unified runtime is pending at the time of writing.

---

# Chapter 2 — The Thermal Process

## 2.1 Installation Overview

The installation studied in this project is a laboratory-scale thermal rig located at ICAM Engineering School. Its purpose is to provide a representative industrial thermal process for teaching automation and control engineering. The rig consists of three main sub-systems: an electric furnace, a plate heat exchanger, and two fluid circuits equipped with flow measurement and valve control.

**Electric furnace.** The furnace is an electrically-heated recirculation unit. It heats the hot fluid circuit (F1) to a controlled temperature and circulates it at a regulated flow rate. The furnace is switched on and off via a Boolean output signal (power, %Q0.3). Its outlet temperature, denoted T_hout (or equivalently Tin1_HE1 once the fluid reaches the exchanger), is the primary energy input to the heat exchanger. The furnace inlet temperature T_hin represents the return temperature of the hot circuit after the exchanger.

**Plate heat exchanger HE-001.** The heat exchanger is a gasketed plate-type unit. Hot fluid (F1) enters at Tin1_HE1, flows through the hot channels, and exits at Tout1_HE1. Cold fluid (F2) enters at Tin2_HE1 from the opposite end and exits at Tout2_HE1, in a counter-current configuration. This arrangement maximizes the temperature driving force and thermal efficiency of the exchange.

**Fluid circuits.** The hot circuit F1 is a closed loop: the furnace heats the fluid, which then passes through the hot side of HE-001 and returns to the furnace. The cold circuit F2 is a separate loop with its own flow control. Each circuit is equipped with an electromagnetic flow meter (outputs F1 and F2, in m³/h) and a proportional valve controlled by an analog output from the PLC (Valve_F1, %QW8; Valve_F2, %QW4).

The flow setpoints F1_SP and F2_SP are the primary operator inputs. Under cascade control, F1_SP becomes the output of the inner controller. F2_SP is manually set by the operator and kept constant during most experiments.

**Simplified P&ID:**

```
 [FURNACE]──────────────────────────────────────────────┐
     │  power(%Q0.3)                                     │
     │                                                   │
  T_hin(%MD16)                                      T_hout / Tin1_HE1(%MD12 / %MD48)
     ↑                                                   ↓
     └─────────────────────────────────────────────[HE-001]──→ Tout1_HE1(%MD44) → HOT OUT
                                                       ↑↓  (counter-current)
     COLD IN ← Tin2_HE1(%MD40) ←─────────────────[HE-001]──→ Tout2_HE1(%MD52)
                                                    F2(%MD32)
                                                 Valve_F2(%QW4)
```

The hot circuit flow is measured at F1 (%MD28) and controlled via F1_SP (%MD24) → Valve_F1 (%QW8).

## 2.2 Instrumentation and Signals

### 2.2.1 Temperature Sensors

Temperatures are measured by industrial sensors (thermocouple or PT100 resistance thermometer — exact type to be confirmed from the hardware configuration in TIA Portal). The sensor output is a 4–20 mA current signal, read by an analog input module on the S7-1500. The module converts the signal to a 16-bit integer in the range 0–27648, which is stored in a %IW address (Process Image Input Word).

A scaling function (FC) in OB1 converts this raw integer to a temperature value in °C using the linear formula:

```
T [°C] = (raw / 27648) × (T_max − T_min) + T_min
```

The result is stored in a %MD address (Merker Double-word, 32-bit floating point REAL).

For example, Tin1_HE1 is read from analog input %IW112 (raw integer, stored as Tin1_heat_exchanger1_scale), scaled, and written to %MD48 (Tin1_HE1 as a Real).

### 2.2.2 Flow Meters

The electromagnetic flow meters output a 4–20 mA signal proportional to the volumetric flow rate. The scaling function converts the raw ADC integer to m³/h. F1 is stored at %MD28 (from raw %IW316, F1_skal), and F2 at %MD32 (from raw %IW204, F2_skal).

### 2.2.3 Valve Actuators

The proportional valves accept a 0–20 mA (or 0–10 V, depending on the actuator) analog command. The PLC writes a Word value (0–27648) to the analog output address: Valve_F1 at %QW8 and Valve_F2 at %QW4. The scaling is: 0 = fully closed, 27648 = fully open. Flow setpoints F1_SP and F2_SP are Real values (m³/h) stored in %MD24 and %MD36 respectively; the OB1 program converts these setpoints to the appropriate Word output for the valve.

### 2.2.4 Complete Tag Table

| Tag | PLC Address | Type | Range | Unit | Description |
|-----|-------------|------|-------|------|-------------|
| T_hin | %MD16 | Real | 0–200 | °C | Furnace inlet temperature |
| T_hout | %MD12 | Real | 0–200 | °C | Furnace outlet temperature |
| T_we_rock_furnace | %IW300 | Int | 0–27648 | ADC | Furnace inlet raw signal |
| T_wy_Oven_scale | %IW304 | Int | 0–27648 | ADC | Furnace outlet raw signal |
| Tin1_HE1 | %MD48 | Real | 0–200 | °C | HE hot inlet temperature |
| Tout1_HE1 | %MD44 | Real | 0–200 | °C | HE hot outlet temperature |
| Tin2_HE1 | %MD40 | Real | 0–200 | °C | HE cold inlet temperature |
| Tout2_HE1 | %MD52 | Real | 0–200 | °C | HE cold outlet temperature |
| Tin1_heat_exchanger1_scale | %IW112 | Int | 0–27648 | ADC | Tin1 raw signal |
| Tout1_HE1_raw | %IW120 | Int | 0–27648 | ADC | Tout1 raw signal |
| Tin2_HE1_raw | %IW116 | Int | 0–27648 | ADC | Tin2 raw signal |
| Tout2_HE1_raw | %IW108 | Int | 0–27648 | ADC | Tout2 raw signal |
| F1 | %MD28 | Real | 0–10 | m³/h | Hot circuit flow rate |
| F1_SP | %MD24 | Real | 0–10 | m³/h | Hot circuit flow setpoint |
| F1_skal | %IW316 | Int | 0–27648 | ADC | F1 raw signal |
| Valve_F1 | %QW8 | Word | 0–27648 | — | Hot valve command |
| F2 | %MD32 | Real | 0–10 | m³/h | Cold circuit flow rate |
| F2_SP | %MD36 | Real | 0–10 | m³/h | Cold circuit flow setpoint |
| F2_skal | %IW204 | Int | 0–27648 | ADC | F2 raw signal |
| Valve_F2 | %QW4 | Int | 0–27648 | — | Cold valve command |
| power | %Q0.3 | Bool | 0–1 | — | Furnace power (ON/OFF) |

## 2.3 Process Physics

### 2.3.1 Heat Exchanger Thermal Model

The energy transfer in a counter-current plate heat exchanger is governed by Newton's law of cooling applied across the heat transfer surface:

```
Q = U × A × LMTD
```

where:
- Q [W] is the total heat transfer rate,
- U [W/(m²·K)] is the overall heat transfer coefficient (function of fluid properties and flow regimes),
- A [m²] is the total heat transfer area,
- LMTD [K] is the Log Mean Temperature Difference.

For a counter-current configuration, the LMTD is:

```
LMTD = (ΔT₁ − ΔT₂) / ln(ΔT₁ / ΔT₂)

where: ΔT₁ = Tin1_HE1 − Tout2_HE1   (hot inlet vs cold outlet)
       ΔT₂ = Tout1_HE1 − Tin2_HE1   (hot outlet vs cold inlet)
```

At steady state, the energy balance on the cold side gives:

```
Q = ṁ₂ × Cp₂ × (Tout2_HE1 − Tin2_HE1)
```

where ṁ₂ [kg/s] is the cold mass flow rate and Cp₂ [J/(kg·K)] is its specific heat capacity. This equation shows that Tout2 depends on both the heat transfer rate Q (which is driven by the hot inlet temperature Tin1) and the cold flow rate F2. An increase in Tin1 increases LMTD, increases Q, and therefore raises Tout2. An increase in F2, while holding Q constant, reduces the temperature rise, lowering Tout2.

### 2.3.2 Dynamic Behaviour and Cascade Motivation

From a control perspective, the important insight is the sequential nature of the dynamic path from the actuator (Valve_F1, and hence F1_SP) to the primary controlled variable (Tout2_HE1):

1. **F1_SP → Tin1_HE1 (inner dynamic):** Increasing F1_SP opens Valve_F1, increasing the hot flow rate. More hot fluid circulates through the furnace per unit time. The furnace raises this increased flow to its set temperature, and Tin1_HE1 responds with a rise that follows a first-order-like dynamic with a certain time constant τ₁ and dead time θ₁.

2. **Tin1_HE1 → Tout2_HE1 (outer dynamic):** The hotter fluid entering the heat exchanger increases the LMTD, which increases Q, which heats the cold fluid more strongly. Tout2_HE1 rises with its own time constant τ₂ > τ₁ (the exchanger integrates thermal energy over its surface area).

The combined transfer function from F1_SP to Tout2_HE1 is approximately the product of two first-order systems with time delays, producing a higher-order response with a large apparent dead time. A single PID controller closing the loop around this combined dynamics must be tuned conservatively to maintain stability, resulting in sluggish disturbance rejection.

Cascade control exploits the measurability of the intermediate variable Tin1_HE1. By regulating Tin1 with a fast inner PI loop, disturbances in the hot circuit (such as variations in furnace temperature or F1 flow deviations from the setpoint) are corrected before they reach Tout2. The outer proportional controller then only needs to handle the slower HE dynamics, operating at a much lower bandwidth.

### 2.3.3 Linearisation Around an Operating Point

For the purpose of controller design, the process is linearised around a nominal operating point. The inner process (F1_SP → Tin1_HE1) is approximated by a FOPTD model:

```
G_inner(s) = K · e^(−θs) / (τs + 1)
```

This approximation is valid in the neighbourhood of the operating point and for modest step amplitudes (< 20% of operating range). The parameters K, τ, θ are identified experimentally in Chapter 5.

## 2.4 Control Objectives

The control system must satisfy the following requirements:

**Primary objective:** Regulate Tout2_HE1 to a setpoint Tout2_SP (e.g., 45°C) with:
- Steady-state error: ≤ 1°C (with PI inner loop and trimmed outer setpoint)
- Settling time: practical limit given by the process time constant (target < 2τ₂)
- Overshoot: < 10% for inner loop; < 5% for Tout2

**Disturbance rejection:** Attenuate the effect of:
- Furnace temperature variations (changes in T_hin)
- Cold flow rate changes (F2 variations)

**Actuator constraints:**
- F1_SP must remain within the safe operating range [F1_min, F1_max] (exact values from installation specs)
- Valve commands must be smooth — rapid oscillations cause mechanical wear
- Mode transitions (Manual → Auto) must be bumpless to prevent process upsets

**Operating modes:**
- MANUAL: operator sets F1_SP directly (used for identification and commissioning)
- AUTO_INNER: inner loop active, operator sets Tin1_SP
- AUTO_FULL: full cascade active, operator sets Tout2_SP

## 2.5 Operating Point

*(This section will be completed with numerical values measured during the laboratory session.)*

The nominal operating conditions used for identification and controller tuning are:

| Variable | Nominal value | Unit | Notes |
|----------|--------------|------|-------|
| T_hin | TBD | °C | Measured at steady state |
| Tin1_HE1 | TBD | °C | Measured at steady state |
| Tout2_HE1 | TBD | °C | Target cold outlet temperature |
| F1 | TBD | m³/h | Hot circuit flow at operating point |
| F2 | TBD | m³/h | Cold circuit flow (held constant) |

---

# Chapter 3 — Siemens S7-1500 and TIA Portal

## 3.1 S7-1500 PLC Architecture

### 3.1.1 Overview

The Siemens S7-1500 is a high-performance PLC series introduced in 2013 as the successor to the S7-300/400 series. It is designed for demanding automation tasks requiring high processing speed, integrated motion control, and native PROFINET communication. The installation at ICAM uses an S7-1500 CPU with IP address 192.168.1.10.

The S7-1500 CPU executes a deterministic scan cycle:
1. **Input update phase:** Physical inputs (from I/O modules connected via backplane) are read into the Process Image Input (PII), a snapshot of all %I and %IW values at the start of the scan.
2. **Program execution phase:** The user program (OB1, FCs, FBs) runs, reading from PII, computing, and writing results to the Process Image Output (PIO) and to memory areas (%M, %DB).
3. **Output update phase:** PIO values are written to the physical output modules (%Q, %QW).

This three-phase structure guarantees that all logic within one scan cycle operates on a consistent, synchronised view of the I/O, preventing race conditions between input reading and output writing.

### 3.1.2 Memory Organisation

The S7-1500 memory is organised into several distinct areas, each serving a specific purpose:

| Area | Symbol | Type | Purpose |
|------|--------|------|---------|
| Process Image Input | %I, %IW, %IB | Read-only during scan | Snapshot of physical inputs |
| Process Image Output | %Q, %QW, %QB | Written by user program | Drives physical outputs |
| Bit Memory (Merkers) | %M, %MW, %MD | Read/write | Global variables, intermediate values |
| Data Blocks | %DBx.DBD, %DBx.DBW | Read/write | Structured data storage |
| Timers / Counters | %T, %C | Managed by system | Timing and counting |

For this project, the most important areas are:
- **%IW** (Analog input words): raw ADC values from temperature sensors and flow meters
- **%MD** (Merker double-words, 32-bit REAL): engineering-unit process values after scaling
- **%QW** (Analog output words): valve position commands
- **%Q** (Digital outputs): furnace power switch
- **%DB1** (Data block 1): structured block accessible via Snap7 for PC communication

The use of %MD (Merker area) for scaled values, rather than direct I/O, is a deliberate architectural choice: it allows both the OB1 program and external communication (Snap7, Open Pipe) to access the same variables, decoupling the scaling logic from the communication layer.

### 3.1.3 Communication

The S7-1500 communicates over PROFINET (Ethernet-based). The ISO-on-TCP connection on port 102 is the standard S7 communication protocol, used by Snap7 for data block access. The PLC IP address is configured in TIA Portal under the CPU network interface settings.

## 3.2 TIA Portal V18 Configuration

TIA Portal (Totally Integrated Automation Portal) is the unified Siemens engineering environment for programming and configuring S7 PLCs, WinCC HMI, and drive systems. The project uses TIA Portal V18.

### 3.2.1 Hardware Configuration

The hardware configuration defines the physical arrangement of CPU and I/O modules in the rack and assigns addresses to each module. The I/O addresses (%IW, %QW) depend directly on the physical slot position of each module: changing the slot order changes all downstream addresses. This makes the hardware configuration a critical foundation of the project — address changes in hardware require corresponding updates in the tag table and all code that references those addresses.

For the thermal rig, analog input modules (AI) occupy specific slots, determining the %IW addresses listed in the tag table. The analog output module occupies another slot, determining the %QW8 and %QW4 addresses for Valve_F1 and Valve_F2.

### 3.2.2 Tag Table (PLC Tags)

The tag table is the central register mapping symbolic names to memory addresses. It is the authoritative reference for all process variables. This project defines 21 process tags, retained after a review and cleanup that removed 25 intermediate, redundant, or test variables from an initial list of 46.

**Naming convention adopted:** English names with the suffix `_HE1` for heat exchanger variables. Examples: `Tin1_HE1` (hot inlet temperature), `Tout2_HE1` (cold outlet temperature), `Valve_F1` (hot valve command). Raw ADC signals are suffixed `_raw` or `_skal` to distinguish them from scaled engineering-unit values.

This naming convention was adopted after considering a Polish convention used by the previous user of the installation. English was chosen for consistency with the web application code and to make the thesis universally readable.

A key insight during TIA Portal setup is the difference between **Optimized block access** and **standard (non-optimized) block access** for Data Blocks:

- With **Optimized block access** (TIA Portal default): the compiler arranges data freely for performance; offsets are not visible in the DB editor and cannot be predicted. The Snap7 library, which relies on absolute byte offsets to read/write DB variables, cannot function with optimized blocks.
- With **Standard (non-optimized) block access**: variables are laid out in declaration order at fixed, visible byte offsets. Snap7 can address them by offset (DBD0, DBD4, etc.).

For DB1, optimized block access was **disabled** (Properties → Attributes → uncheck "Optimized block access") before compiling. This made the byte offsets visible in the DB editor and enabled Snap7 access.

### 3.2.3 OB1 and Scaling Function (FC)

OB1 (Organisation Block 1) is the main cyclic program, called every scan cycle. It contains the following logic for this project:

1. **Scaling FC calls:** For each analog input channel, a Function block reads the raw %IW value and computes the engineering-unit value using:
   ```
   value [EU] = (raw / 27648.0) × (range_max − range_min) + range_min
   ```
   The result is written to the corresponding %MD address. For example, the raw %IW112 integer (Tin1_heat_exchanger1_scale) is converted to °C and written to %MD48 (Tin1_HE1).

2. **Valve command computation:** F1_SP (m³/h, stored at %MD24) is converted to a Word output for %QW8:
   ```
   valve_cmd = REAL_TO_WORD((F1_SP / F1_max) × 27648.0)
   ```

3. **DB1 update FC:** A small Function copies the most important %MD values (Tin1_HE1, F1, F1_SP, Tout2_HE1, etc.) into DB1 at fixed offsets, making them readable by Snap7.

The scan cycle time is on the order of a few milliseconds — much faster than the 3-second poll rate of the web application — so from the application's perspective, PLC data is always current.

### 3.2.4 DB1 for Snap7 Access

DB1 is defined with non-optimized access and contains a small set of key variables:

| DB1 Offset | TIA Portal type | Tag name | Description |
|------------|-----------------|----------|-------------|
| DBD0 | REAL | temperature | Measured temperature (Tin1_HE1, °C) |
| DBD4 | REAL | flow_rate | Measured flow rate (F1, m³/h) |
| DBD8 | REAL | setpoint_temp | Temperature setpoint |
| DBD12 | REAL | setpoint_flow | Flow setpoint (F1_SP, m³/h) |
| DBW16 | INT | valve_state | Valve status (0=CLOSED, 1=OPEN, 2=PARTIAL) |

The Snap7 Python library reads these variables by specifying DB=1 and the byte offset. For REAL values, the read function returns 4 bytes and interprets them as IEEE 754 single-precision float.

DB1 serves as a compact "shared memory" interface between the PLC and the PC application for the Monitor and test pages. The full 21-tag interface uses Open Pipe instead (Section 3.3.2).

## 3.3 WinCC Unified and SIMATIC Panel 7"

### 3.3.1 WinCC Unified Runtime

WinCC Unified is Siemens' latest generation HMI software, designed for touchscreen panels and web browsers. The SIMATIC Unified 7" panel (IP: 192.168.1.200) runs WinCC Unified Runtime, which connects to the S7-1500 over PROFINET and maintains a local tag table mirroring the PLC variables.

The WinCC Unified tag table maps symbolic names (matching the PLC tag table names) to the corresponding PLC memory addresses. At runtime, WinCC continuously polls the PLC and updates its local tag cache. This tag cache is what the Open Pipe mechanism exposes to external applications running on the panel (such as our Docker container).

The panel's built-in screen displays a WinCC Unified project (distinct from the Flask web application). This project provides a local, always-on operator display that does not depend on the web application. The Flask web interface is a supplementary layer accessible from the panel's integrated web browser.

### 3.3.2 Open Pipe Communication

Open Pipe is a Siemens proprietary mechanism that allows external processes running on the same hardware as WinCC Unified (specifically, Docker containers deployed via Industrial Edge) to read and write WinCC tags via a Unix domain socket.

**Socket location:** `/tmp/siemens/automation/openpipe.sock` on the panel filesystem. When the Flask application runs in a Docker container on the panel, this socket is made accessible inside the container via a volume mount:

```yaml
volumes:
  - /tmp/siemens/automation:/tempcontainer/
```

Inside the container, the socket appears at `/tempcontainer/openpipe.sock`.

**Protocol:** The communication is JSON-based, using newline-delimited messages over a Unix SOCK_STREAM socket:

```json
// Read request:
{"action": "read", "tags": ["Tin1_HE1", "F1_SP", "Tout2_HE1"]}

// Response:
{"Tin1_HE1": 75.3, "F1_SP": 3.0, "Tout2_HE1": 42.1}

// Write request:
{"action": "write", "tag": "F1_SP", "value": 3.5}
```

**Advantages over Snap7:** Open Pipe uses tag names directly, matching the WinCC Unified tag table, rather than raw byte offsets. It requires no knowledge of DB structure or data types — the WinCC runtime handles all type conversion. It also benefits from WinCC's tag cache, so each request is served from memory rather than triggering a PLC poll.

**Simulation fallback:** When the socket file does not exist (e.g., during development on a PC), the `OpenPipeConnector` class automatically returns plausible simulated values for all 21 tags. This fallback mode, indicated by `source: "SIMULATION"` in the API response, allows the full web interface to be developed and tested without physical hardware.

### 3.3.3 Open Pipe vs Snap7: Coexistence

The project uses both protocols simultaneously:

| Protocol | Module | Tags | Used by |
|----------|--------|------|---------|
| Snap7 (TCP, port 102) | `plc_connector.py` | DB1 (5 vars) | Monitor page, CSV logger |
| Open Pipe (Unix socket) | `openpipe_connector.py` | 21 WinCC tags | Synoptique, Cascade, Process pages |

Snap7 provides direct, low-latency PLC access without WinCC mediation. Open Pipe provides access to the full WinCC tag set, including computed and derived values managed by WinCC scripts. The two connectors operate on independent threads and do not interfere with each other.

## 3.4 Industrial Edge Deployment

### 3.4.1 Industrial Edge Overview

Siemens Industrial Edge is a platform that enables Docker containers to run directly on compatible Siemens hardware, including the SIMATIC Unified 7" panel. From an engineering perspective, Industrial Edge turns the panel into an embedded Linux host running a Docker daemon, managed by the Siemens Edge Runtime service.

The deployment workflow introduces a specific packaging step: instead of deploying directly via `docker compose up`, the application must be packaged into a `.app` file using the Siemens Industrial Edge App Publisher desktop tool. This tool:
1. Reads the `docker-compose.yml` (specifically `docker-compose.edge.yml` for edge deployment)
2. Embeds the Docker image layers and configuration
3. Produces a single `.app` archive signed and formatted for the Edge Management console

The resulting `.app` file can then be uploaded to the Edge Management console (a web UI running on the panel or a central server) and deployed to the panel. Access to the console requires valid license credentials.

### 3.4.2 Docker Compose Configuration for Edge

The edge-specific `docker-compose.edge.yml` differs from the development configuration in several important ways:

```yaml
services:
  app:
    image: project-s7-app:latest
    restart: unless-stopped
    ports:
      - "30500:5000"
    environment:
      - FLASK_DEBUG=0
      - LOG_DIR=/app/logs
    mem_limit: 256m
    volumes:
      - /tmp/siemens/automation:/tempcontainer/
      - ie-databus:/app/logs
    networks:
      - ieguestnetwork
```

Key differences from the development configuration:

- **Port mapping:** External port 30500 (Industrial Edge requires ports in the range 30000–35000 for user applications) maps to the container's internal port 5000.
- **Memory limit:** `mem_limit: 256m` constrains the container to 256 MB of RAM, respecting the panel's limited hardware resources.
- **Volume mounts:** `/tmp/siemens/automation` provides access to the Open Pipe socket. `ie-databus` is a named volume for log persistence.
- **Network:** `ieguestnetwork` is the standard Industrial Edge guest network, providing connectivity to the panel's PROFINET interface.
- **No hot-reload:** `FLASK_DEBUG=0` disables Flask's auto-reloader, which is appropriate for production deployment.

### 3.4.3 Deployment Process

1. **Build on PC:** `docker compose -f docker-compose.edge.yml build` — produces the Docker image with all Python dependencies.
2. **Package with App Publisher:** Import `docker-compose.edge.yml` into the Siemens Industrial Edge App Publisher → validate → export as `.app` file.
3. **Upload to panel:** Log in to the Edge Management console at `http://192.168.1.200` with license credentials → upload `.app` → deploy.
4. **Access:** The application becomes available at `http://192.168.1.200:30500` from any device on the laboratory network.

### 3.4.4 Current Status

The `.app` file has been successfully generated by the App Publisher. Deployment on the panel is pending the acquisition of Industrial Edge license credentials. In the interim, the application runs on the development PC (port 5000) and is accessible from the panel's browser at `http://192.168.1.149:5000`. A Windows Firewall rule was added to allow inbound TCP connections on port 5000 from the local subnet.

---

# Chapter 4 — Software Architecture

## 4.1 Technology Stack

The web application is built on a deliberately lean technology stack, chosen for its ability to cover all functional requirements without unnecessary complexity.

**Python / Flask:** Flask is a lightweight Python web framework. Its minimal core and extensive ecosystem make it ideal for projects that require both a REST API and real-time WebSocket communication. The availability of a first-class Python binding for Snap7 (`python-snap7`) was a significant factor in choosing Python over alternatives such as Node.js. Flask also integrates cleanly with the `flask-socketio` extension, which wraps the Socket.IO protocol for real-time bidirectional communication.

**Socket.IO:** Rather than implementing a polling mechanism where the browser repeatedly requests updated data, Socket.IO maintains a persistent WebSocket connection. The server pushes new data to all connected clients as soon as it is available (every 3 seconds, when the poll loop fires). This reduces latency, eliminates redundant requests, and allows multiple browser windows to display the same live data simultaneously.

**Docker:** Containerisation provides a reproducible execution environment. The same Docker image runs on the development PC (Windows with Docker Desktop), on a Raspberry Pi (Linux ARM), and on the SIMATIC Unified 7" panel (Linux x86_64 via Industrial Edge). Dependencies are locked in `requirements.txt` and baked into the image at build time.

**Chart.js:** A JavaScript charting library that renders responsive, animated time-series charts directly in the browser without any server-side processing. The identification page uses a dual-Y-axis configuration (temperature on the left axis, F1_SP on the right) rendered with `animation: false` for smooth streaming updates.

**Comparison with classical SCADA:** A classical SCADA system for this installation would require a Siemens WinCC workstation licence (several thousand euros), a dedicated engineering workstation, and ongoing licence maintenance. The web-based approach uses only open-source software (zero licence cost) and runs on commodity hardware. The trade-off is the absence of industrial certification and built-in safety features — acceptable for a laboratory demonstrator, not for a production system.

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Web server | Flask (Python) | Lightweight, REST + SocketIO, Snap7 binding |
| Real-time push | Socket.IO | WebSocket with fallback, multi-client |
| PLC comm. (direct) | Snap7 | Open-source S7 TCP library |
| PLC comm. (tags) | Open Pipe | Native WinCC Unified tag interface |
| Frontend charts | Chart.js | Client-side rendering, no server overhead |
| Frontend layout | Bootstrap 5 | Responsive, touch-friendly |
| Containerisation | Docker | Cross-platform reproducibility |
| Data persistence | CSV (append-only) | Simple, portable, no database overhead |

## 4.2 Application Structure

The application is structured as a set of cooperating Python modules, each responsible for a single concern:

| Module | Responsibility |
|--------|----------------|
| `main.py` | Flask routes, Socket.IO events, background thread management |
| `plc_connector.py` | Snap7 TCP connection to S7-1500 DB1 |
| `openpipe_connector.py` | Open Pipe Unix socket → 21 WinCC tags |
| `cascade_controller.py` | PI+P inner loop + P outer loop, mode state machine |
| `identification.py` | Step test orchestration, FOPTD parameter extraction, IMC gains |
| `thermal_model.py` | Discrete-time simulation fallback (1st-order + P-controller) |
| `logger.py` | Append-only CSV writer |

### 4.2.1 Singleton Pattern

Each module exposes a single class that is instantiated once at application startup in `main.py`:

```python
plc      = PLCConnector()
openpipe = OpenPipeConnector()
cascade  = CascadeController()
ident    = StepIdentifier()
model    = ThermalProcessModel()
log      = DataLogger()
```

This singleton pattern ensures that all HTTP route handlers and background threads share the same state objects — critical for the cascade controller and step identifier, which maintain persistent state between poll cycles.

### 4.2.2 Threading Model

The application runs four concurrent threads:

| Thread | Period | Role |
|--------|--------|------|
| Flask/SocketIO (main) | event-driven | HTTP request handling, WebSocket dispatch |
| `sim-loop` (daemon) | 3 s | Advance thermal simulation model (fallback only) |
| `plc-poll` (daemon) | 3 s | Read DB1 via Snap7, emit `process_data` |
| `openpipe-poll` (daemon) | 3 s | Read 21 tags via Open Pipe, run cascade/identification, emit events |

**Thread safety:** Shared state objects (cascade controller, step identifier) are accessed from the `openpipe-poll` thread only. HTTP route handlers that modify controller state (e.g., mode changes, setpoint updates) do not call `controller.update()` directly; they only set parameters and flags that are read during the next poll cycle. This single-writer model avoids race conditions without requiring explicit locks on the control objects.

## 4.3 PLC Communication Layer

### 4.3.1 Snap7 — Direct DB Access

`plc_connector.py` wraps the `python-snap7` library, which implements the S7 Communication protocol (S7comm) over ISO-on-TCP (port 102). The connection is established with:

```python
client.connect(PLC_IP, rack=0, slot=1)  # slot=1 for all S7-1500 CPUs
```

Reading DB1 uses absolute byte offsets. The `read_process_data()` method reads a 20-byte block starting at DB1.DBD0 and interprets it according to the fixed structure:

```python
raw = client.db_read(db_number=1, start=0, size=20)
temperature  = snap7.util.get_real(raw, 0)   # DBD0
flow_rate    = snap7.util.get_real(raw, 4)   # DBD4
setpoint_T   = snap7.util.get_real(raw, 8)   # DBD8
setpoint_F   = snap7.util.get_real(raw, 12)  # DBD12
valve_state  = snap7.util.get_int(raw,  16)  # DBW16
```

Writing to DB1 uses the complementary `db_write()` method with a specific byte offset.

Connection failures are handled gracefully: if Snap7 cannot connect (PLC off, wrong IP, wrong slot), the connector sets `_connected = False` and the poll loop uses the simulation fallback instead.

### 4.3.2 Open Pipe — WinCC Tag Access

`openpipe_connector.py` communicates with the Open Pipe Unix socket using Python's standard `socket` library. Because Unix domain sockets are Linux-only, this code only functions inside the Docker container on the panel. On Windows, the socket file does not exist, so the connector automatically enters simulation mode.

The key method `read_all_tags()` sends a single JSON request listing all 21 tag names and receives a single JSON response with all values. This batched read is important for efficiency — it avoids the latency of 21 individual socket round-trips.

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

Writing is done tag by tag via `write_tag(name, value)`, since control outputs (F1_SP) are written one at a time.

## 4.4 Real-Time Data Flow

The `openpipe-poll` thread executes the following sequence every 3 seconds:

1. Call `openpipe.read_all_tags()` → receive dict of 21 tag values
2. Check if identification is running:
   - If yes: call `ident.feed(Tin1, Tout2, F1_SP)` → may return a new F1_SP to write
   - Write F1_SP if identification returned one
3. If identification is not running, check cascade mode:
   - If AUTO_INNER or AUTO_FULL: call `cascade.update(Tin1, Tout2)` → returns new F1_SP
   - Write F1_SP via `openpipe.write_tag('F1_SP', new_sp)`
4. Emit `process_tags` event to all Socket.IO clients (all 21 tags + source)
5. Emit `cascade_data` event (controller state: mode, setpoints, errors, output)
6. If identification active: emit `ident_update` event (status, progress, chart data point)

**Priority:** Identification takes precedence over cascade control. Both cannot run simultaneously; the identification API blocks mode changes to Manual while a test is in progress.

**Socket.IO events:**

| Event | Direction | Data |
|-------|-----------|------|
| `process_tags` | server → client | All 21 tags + source indicator |
| `process_data` | server → client | 5 DB1 variables (from plc-poll thread) |
| `cascade_data` | server → client | Controller mode, setpoints, errors, F1_SP output |
| `ident_update` | server → client | Step test status, progress %, chart data point, results |

Each page subscribes only to the events it needs: the Synoptique listens to `process_tags`; the Cascade page listens to all four events; the Monitor page listens to `process_data`.

## 4.5 REST API

The HTTP API provides a stateless interface for control actions and data queries. All endpoints use JSON for both request bodies and responses.

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Monitor page (HTML) |
| GET | `/schema` | Synoptique page (HTML) |
| GET | `/cascade` | Cascade identification and control page (HTML) |
| GET | `/process` | Process tag monitor page (HTML) |
| GET | `/api/data` | Current 5-variable snapshot (Snap7) |
| POST | `/api/setpoint` | Set temperature or flow setpoint (DB1) |
| GET | `/api/process/data` | All 21 WinCC tags (Open Pipe) |
| POST | `/api/process/write` | Write F1_SP or F2_SP |
| GET | `/api/cascade/status` | Cascade controller state |
| POST | `/api/cascade/mode` | Switch Manual / Auto-Inner / Auto-Full |
| POST | `/api/cascade/setpoint` | Set Tout2_SP or Tin1_SP |
| POST | `/api/cascade/params` | Set inner Kp/Ti and outer Kp |
| POST | `/api/identification/start` | Start step test |
| POST | `/api/identification/cancel` | Cancel, restore F1_SP |
| GET | `/api/identification/status` | Identification state + results |
| GET | `/api/export/csv` | Download complete CSV log |
| GET | `/health` | Docker healthcheck (`{"status": "ok"}`) |

## 4.6 Data Persistence

`logger.py` implements an append-only CSV logger. Each poll cycle (both Snap7 and Open Pipe), a new row is written to `/app/logs/process_data.csv` containing a timestamp, all key process variables, and the `source` field indicating data origin.

The log file is written to a Docker volume (`./logs:/app/logs`), ensuring it persists across container restarts and image rebuilds. The `GET /api/export/csv` endpoint streams the file directly with a timestamped filename (`process_data_YYYYMMDD_HHMMSS.csv`), allowing an engineer to download a complete session record without accessing the Docker host.

## 4.7 Web Interface Pages

### 4.7.1 Synoptique (`/schema`) — Primary Panel Display

The Synoptique is the main operator display, designed for the SIMATIC Unified 7" touchscreen (800×480 pixels). It features an SVG-based P&ID diagram of the installation, with animated flow lines (orange for the hot circuit, blue for the cold circuit) and live value overlay cards.

Ten values are displayed in real time: T_hin, T_hout, Tin1_HE1, Tout1_HE1, Tin2_HE1, Tout2_HE1, F1, F2, Valve_F1 status, and Valve_F2 status. A coloured dot and text indicator shows whether the furnace is ON or OFF.

Touch-sensitive increment/decrement buttons allow the operator to adjust F1_SP and F2_SP in 0.1 m³/h steps without a keyboard. Each button press calls `POST /api/process/write`.

The page subscribes to `process_tags` Socket.IO events and updates all values every 3 seconds, with no manual refresh required.

### 4.7.2 Cascade (`/cascade`) — Engineering Tool

The Cascade page is intended for use by an engineer on a PC (or on the panel browser for commissioning). It is organised into two tabs:

**Tab 1 — Identification:**
- A form to configure the step test (base F1_SP auto-filled from current PLC value, amplitude, duration)
- A live Chart.js dual-axis chart: temperature (Tin1 in red, Tout2 in orange dashed) on the left Y-axis, F1_SP step (blue stepped line) on the right Y-axis
- A progress bar showing the pre-step baseline phase and the step phase
- On completion: KPI cards for K, τ, θ and a three-row IMC tuning table (Aggressive / Normal / Conservative) with individual "Apply & Switch" buttons that load the gains into the controller and activate the Cascade tab

**Tab 2 — Cascade Control:**
- A visual block diagram of the cascade structure: Tout2_SP → [P] → Tin1_SP → [PI+P] → F1_SP
- Parameter input forms for inner loop (Kp, Ti) and outer loop (Kp_ext)
- Three mode buttons: MANUAL, AUTO INNER, AUTO FULL, with the active mode highlighted
- A live status grid showing: Tin1 (current/setpoint/error) and Tout2 (current/setpoint/error), plus the current F1_SP output

### 4.7.3 Process (`/process`) — Debug Tag Monitor

The Process page displays all 21 WinCC tags organised in three sections: Furnace, HE1 Hot Side, and HE1 Cold Side. Values are updated in real time via `process_tags` Socket.IO events. Valve tags display a colour-coded badge (green OPEN, yellow PARTIAL, red CLOSED) based on the numeric value.

This page is primarily a debugging and commissioning tool, used to verify that all tags are reading correctly before starting identification or control tests.

### 4.7.4 Monitor (`/`) — Historical Chart

The Monitor page provides a scrolling time-series Chart.js chart of temperature and flow rate, using data from the Snap7 poll (DB1 values). It includes basic alarm logic (threshold colour change) and setpoint control for DB1 variables. A "Download CSV" button triggers `GET /api/export/csv`.

---

# Chapter 5 — Process Identification

## 5.1 Theoretical Background

### 5.1.1 The FOPTD Model

A large class of industrial processes — including thermal systems — can be adequately described, in the neighbourhood of an operating point, by a First-Order Plus Time Delay (FOPTD) transfer function:

```
G(s) = K · e^(−θs) / (τs + 1)
```

where:
- **K** [output unit / input unit] is the static gain: the ratio of the steady-state output change to the input step amplitude
- **τ** [s] is the time constant: the time for the output to reach 63.2% of its final value after a step, measured from the moment the response begins to rise
- **θ** [s] is the dead time (or transport delay): the time from the input step to the first measurable response of the output

For the inner process of this installation:
- Input: F1_SP [m³/h] (hot flow setpoint)
- Output: Tin1_HE1 [°C] (hot inlet temperature to the heat exchanger)
- **K** has units of °C/(m³/h): a step of +0.5 m³/h in F1_SP that produces a final Tin1 rise of +7.5°C gives K = 15 °C/(m³/h)

**Justification of the FOPTD model:** The furnace dynamics dominate the F1_SP → Tin1_HE1 path. The furnace is essentially a thermally well-mixed chamber with energy input proportional to power and heat removal proportional to the outgoing flow. This single-dominant-lag structure is well-approximated by a first-order system. The dead time θ captures the transport delay as fluid travels from the valve to the temperature sensor.

Higher-order effects (e.g., the finite dynamics of the temperature sensor itself, or the secondary thermal mass of the heat exchanger shell) are present but minor compared to the furnace lag; they are absorbed into the effective τ and θ.

### 5.1.2 Step Response Characterization

Given a step input ΔF1_SP applied at time t₀, the FOPTD step response is:

```
ΔTin1(t) = 0                                              for t < t₀ + θ
ΔTin1(t) = K × ΔF1_SP × (1 − e^(−(t − t₀ − θ)/τ))     for t ≥ t₀ + θ
```

The three parameters are extracted graphically from the experimental step response:

**Static gain K:**
```
K = ΔTin1_∞ / ΔF1_SP
```
where ΔTin1_∞ is the measured steady-state change in Tin1 after the transient has settled, and ΔF1_SP is the known step amplitude.

**Time constant τ:**
The point at which the response reaches 63.2% of its final value determines τ. In the experimental curve, this is the time t₆₃ (measured from t₀ + θ) at which:
```
Tin1(t₆₃) = Tin1_base + 0.632 × ΔTin1_∞
```
Therefore: **τ = t₆₃ − (t₀ + θ)**

**Dead time θ:**
θ is identified as the delay before the first measurable departure from the pre-step baseline. Practically, this is defined as the time from the step application t₀ to the first sample at which the absolute change exceeds 2% of the total expected step amplitude:
```
θ ≈ t_first_response − t₀   where |Tin1 − Tin1_base| > 0.02 × ΔTin1_∞
```

**Figure: Ideal FOPTD step response**

```
Tin1
  │
  │          Tin1_base + ΔTin1_∞ ·····················
  │                                 /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
  │          Tin1_base + 0.632 × ΔTin1_∞ ·····/
  │                                     /
  │                               /
  │                          /
  │         Tin1_base ─────/·····························
  │                ↑    ↑  ↑
  │               t₀  t₀+θ t₆₃                      t
                         ←→ θ
                            ←———— τ ————→
```

### 5.1.3 IMC Tuning Rules

Internal Model Control (IMC) is a model-based controller design method that provides an explicit and intuitive relationship between the desired closed-loop speed of response and the controller gains. For a FOPTD process, the IMC-derived PI controller has the following gains:

```
Kp = τ / (K × (λ + θ))
Ti = τ
```

where **λ** [s] is the closed-loop time constant — the only free tuning parameter. A smaller λ gives a faster, more aggressive response; a larger λ gives a slower, more robust response.

**Choice of λ:** Three pre-defined tuning levels are provided:

| Level | λ | Behaviour |
|-------|---|-----------|
| Aggressive | 0.5 × τ | Fast response, ~10% overshoot possible |
| Normal (recommended) | τ | Balanced — good starting point |
| Conservative | 2 × τ | Slow, robust — use if oscillations appear |

A practical lower bound is λ ≥ θ; setting λ < θ creates a closed-loop time constant shorter than the process dead time, which is physically unrealisable with a PI controller.

**Why IMC rather than Ziegler-Nichols?** Ziegler-Nichols rules are derived empirically for a particular response criterion (1/4 decay ratio) and can produce aggressive tuning with significant overshoot. IMC rules have a clear physical interpretation: the parameter λ directly corresponds to the desired closed-loop response time. Detuning is trivial — simply increase λ by a factor.

## 5.2 Experimental Protocol

### 5.2.1 Pre-Test Conditions

Before starting the step test, the following conditions must be verified:

1. **Steady-state reached:** The furnace must have been running for at least 30 minutes with stable F1_SP and F2_SP. Stability criterion: Tin1_HE1 drift < 0.5°C over 5 minutes (verified on the Process page).
2. **Manual mode active:** The cascade controller must be in MANUAL mode. The identification API call will be rejected if mode ≠ MANUAL.
3. **Know the operating point:** Read the current F1_SP value from the PLC (auto-filled in the identification form). Record Tin1_HE1, Tout2_HE1, F1, F2, and T_hin as the baseline operating point.

### 5.2.2 Step Amplitude and Duration Selection

**Amplitude selection:** The step amplitude should be 10–20% of the F1 operating range to ensure a measurable signal-to-noise ratio while remaining within the linear region of the process. For a nominal F1 ≈ 3.0 m³/h with a range of approximately 0–5 m³/h, an amplitude of +0.5 m³/h (approximately 10% of range) is appropriate.

- Too small: temperature rise buried in sensor noise (sensor resolution ≈ 0.1–0.5°C)
- Too large: exceeds the linear operating region, identified parameters will not be representative

**Duration:** Identification requires observing the complete transient to steady state. A minimum duration of 3 × τ is theoretically needed (output reaches 95% of final value). For an estimated τ of 30–120 s, a duration of 180 s (3 minutes) is chosen as a conservative default. The step test can be cancelled early if the transient is clearly complete.

### 5.2.3 Acquisition

The `StepIdentifier` class in `identification.py` orchestrates the step test. Internally, the test passes through three phases:

**PRE_STEP phase (15 s — 5 samples):** The identifier records the baseline. F1_SP is held at its current value. The baseline Tin1 value is computed as the average of the 5 pre-step samples, filtering out slow sensor drift.

**STEP phase (duration_s — configurable):** At the first poll cycle after PRE_STEP completes, F1_SP is set to `base_F1_SP + amplitude`. The identifier records all (Tin1, Tout2, F1_SP, timestamp) samples. Progress is reported as a percentage of total step duration via the `ident_update` Socket.IO event.

**Analysis and restoration:** At the end of the STEP phase, `_analyze()` is called automatically. F1_SP is restored to the baseline value. Results (K, τ, θ, IMC gains) are stored and displayed on the `/cascade` page.

The sampling period is determined by the Open Pipe poll rate: currently 3 seconds. This means the identification resolution is limited to ±3 s for both τ and θ, and the minimum observable dead time is approximately 3–6 s. For thermal processes with τ >> θ, this is acceptable for PI tuning purposes.

### 5.2.4 Safety Checks

- If the step test is cancelled mid-way (`POST /api/identification/cancel`), F1_SP is immediately restored to the baseline value.
- If F1_SP would exceed the configured `F1_max` (default: 10.0 m³/h), the step is clamped automatically.
- The cascade mode cannot be switched out of MANUAL during a running identification test.

## 5.3 Identification Results

*(This section will be completed after the experimental session on 2026-05-19 with Michal.)*

### 5.3.1 Raw Step Response Curves

*[Figure placeholder: Time-series chart with F1_SP step on right Y-axis (blue), Tin1_HE1 on left Y-axis (red), Tout2_HE1 on left Y-axis (orange dashed). X-axis: time in seconds from step application.]*

### 5.3.2 Extracted Parameters

| Parameter | Value | Unit | Notes |
|-----------|-------|------|-------|
| F1_SP base | TBD | m³/h | Operating point |
| ΔF1_SP | TBD | m³/h | Step amplitude |
| ΔTin1_∞ | TBD | °C | Steady-state change |
| K | TBD | °C/(m³/h) | Static gain |
| τ | TBD | s | 63.2% crossing |
| θ | TBD | s | First measurable response |

### 5.3.3 IMC Gain Calculations

*(To be completed once K, τ, θ are available from experimental session)*

| Tuning level | λ | Kp | Ti (s) |
|---|---|---|---|
| Aggressive | 0.5 × τ | TBD | TBD |
| Normal | τ | TBD | TBD |
| Conservative | 2 × τ | TBD | TBD |

### 5.3.4 Model Validation

*(Discussion of FOPTD fit quality and validity of extracted parameters — to be completed after session)*

---

# Chapter 6 — Cascade Control Implementation

## 6.1 Why Cascade Control

### 6.1.1 Limitation of Single-Loop Control on Tout2

A direct single-loop PID controller regulating Tout2_HE1 by manipulating F1_SP faces the following challenges:

1. **Slow dynamics:** The path from F1_SP to Tout2_HE1 passes through the furnace (τ₁) and then the heat exchanger (τ₂). The total apparent time constant τ_total ≈ τ₁ + τ₂ is substantially longer than τ₁ alone. This forces the controller to have a long integral time, resulting in sluggish setpoint tracking.

2. **Disturbance propagation:** A change in furnace temperature (T_hin disturbance) first affects Tin1_HE1 and then, after passing through the exchanger dynamics, affects Tout2_HE1. A single-loop controller cannot distinguish between the source of the disturbance — it simply reacts to the Tout2 error after both dynamics have been traversed. By the time Tout2 deviates significantly, the disturbance has been acting on the process for a time equal to τ₂.

3. **Stability constraint:** The combined transfer function G_Tout2(s) = G₁(s)·G₂(s) has a more complex frequency response than either first-order system alone. Achieving aggressive tuning (short closed-loop time constant) without oscillation requires a careful gain margin analysis. In practice, the achievable bandwidth is limited by the phase delay introduced by the cascade of dynamics.

### 6.1.2 Cascade Principle

Cascade control addresses these limitations by adding an intermediate measurement loop:

```
Tout2_SP ──→ [C_outer] ──→ Tin1_SP ──→ [C_inner] ──→ F1_SP ──→ G₁(s) ──→ Tin1 ──→ G₂(s) ──→ Tout2
                ↑                            ↑
            Tout2_HE1                    Tin1_HE1
```

The inner loop (C_inner + G₁) regulates Tin1_HE1 to a setpoint, using F1_SP as the manipulated variable. Because Tin1 responds to F1_SP much faster than Tout2 does, the inner loop can be tuned aggressively (short τ_cl,inner). The outer loop (C_outer) then only needs to handle the G₂ dynamics (Tin1 → Tout2), operating at a bandwidth commensurate with τ₂.

**Key requirement:** The inner loop bandwidth must be at least 3 to 5 times higher than the outer loop bandwidth. If this condition is not met, the cascade offers no advantage and may even destabilise the system. For this installation, Tin1 responds to F1_SP faster than Tout2 responds to Tin1 (the furnace is a direct thermal source; the heat exchanger has distributed thermal mass), so the condition is satisfied.

**Benefit:** Disturbances entering at the inner process (e.g., valve calibration drift, furnace temperature fluctuations) are corrected by C_inner before they propagate to G₂ and reach Tout2. This is the primary advantage of cascade over single-loop control.

### 6.1.3 Applicability to This Installation

The cascade structure is applicable here because:
- Tin1_HE1 is a measurable intermediate variable that causally influences Tout2_HE1
- The inner dynamic (F1_SP → Tin1) is faster than the outer dynamic (Tin1 → Tout2)
- F1_SP is a suitable manipulated variable: it is continuous, actuated by a proportional valve, and controllable within a meaningful range

## 6.2 Inner Loop — PI+P Controller

### 6.2.1 Discrete-Time PI with Proportional Action on Measurement

The inner loop controller is a discrete-time PI with proportional action on the measurement (P-on-M), also called PI+P or velocity-form PI. The controller update equation is:

```
Δu[k] = −Kp × (y[k] − y[k−1]) + (Kp / Ti) × e[k] × Ts
u[k]  = u[k−1] + Δu[k]
u[k]  = clamp(u[k], F1_min, F1_max)
```

where:
- `y[k]` = Tin1_HE1 (measurement), `y[k−1]` = previous measurement
- `e[k]` = Tin1_SP − Tin1_HE1 (error at current step)
- `Ts` = sampling period (3 s)
- `u[k]` = F1_SP (controller output, m³/h)

This is equivalent to the position-form PI in steady state, but the velocity form avoids computing absolute values of the error integral, which is susceptible to initialisation issues and windup.

### 6.2.2 Comparison: Standard PI vs PI+P

| Property | Standard PI (position form) | PI+P (velocity form) |
|----------|----------------------------|----------------------|
| Setpoint step | Proportional kick in output | No kick (P acts on measurement change only) |
| Disturbance rejection | Good | Identical to standard PI |
| Integral term | Explicit sum of errors | Implicit in incremental form |
| Bumpless transfer | Requires separate tracking logic | Natural: initialise `u[k−1]` and `y[k−1]` |
| Anti-windup | Requires back-calculation or clamping | Implicit: output clamped each step |

The proportional term acts on `y[k] − y[k−1]` (the measurement change) rather than `e[k] − e[k−1]` (the error change). For a step in setpoint (Tin1_SP), `y` does not change instantaneously — only `e` does. Therefore, the proportional contribution at the moment of the setpoint step is zero: there is no proportional kick. This prevents the abrupt F1_SP jump that a standard PI would produce, resulting in smoother valve actuation.

### 6.2.3 Anti-Windup

In the velocity form, output clamping provides natural anti-windup protection. At each time step, after computing `u[k] = u[k−1] + Δu[k]`, the output is clamped to `[F1_min, F1_max]`:

```python
clamped = max(self.out_min, min(self.out_max, raw))
self.last_output = clamped   # next u[k-1] is the CLAMPED value
```

Because `last_output` is updated to the clamped value, the increment at the next step (`u[k+1] = clamped + Δu[k+1]`) is computed from the physically actuated output rather than a hypothetical unclamped value. This prevents the accumulation of "windup" that would occur if `last_output` were allowed to grow beyond the saturation limits.

If the process is in saturation (F1_SP at maximum, Tin1 still below setpoint), the integral contribution Δu[k] will be positive but bounded by the clamping, and `last_output` will not increase beyond `F1_max`. As soon as Tin1 rises above the setpoint, `e[k]` becomes negative, Δu[k] becomes negative, and the output begins to decrease — there is no delayed recovery due to windup.

### 6.2.4 Bumpless Transfer

When the operator switches from MANUAL to AUTO_INNER mode, the inner PI+P controller must begin at the current manual F1_SP value with no step discontinuity. This is achieved by the `init_output()` method:

```python
def init_output(self, current_output: float, current_meas: float):
    self.last_output = current_output
    self._last_meas  = current_meas
```

At the first controller cycle after `init_output()`:
- `u[k−1]` = current manual F1_SP (the value the operator had set)
- `y[k−1]` = current Tin1 (so the proportional term Δu[k] = −Kp × (y[k] − y[k−1]) ≈ 0)
- The integral term `(Kp/Ti) × e[k] × Ts` will be small (if the current Tin1 is close to the setpoint)

The first F1_SP output from the controller will therefore be very close to the manual value, with no bump.

### 6.2.5 Implementation

The `PIplusP` class in `cascade_controller.py` implements this controller:

```python
class PIplusP:
    def __init__(self, Kp=1.0, Ti=60.0, out_min=0.0, out_max=10.0, dt=3.0):
        self.Kp = Kp
        self.Ti = Ti
        self.out_min = out_min
        self.out_max = out_max
        self.dt = dt
        self.last_output = 0.0
        self._last_meas = None

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

    def init_output(self, current_output: float, current_meas: float):
        self.last_output = current_output
        self._last_meas = current_meas
```

## 6.3 Outer Loop — Proportional Controller

### 6.3.1 Structure

The outer loop translates the cold outlet temperature setpoint (Tout2_SP) into a target hot inlet temperature setpoint (Tin1_SP_cmd):

```
Tin1_SP_cmd = Tin1_SP_base + Kp_ext × (Tout2_SP − Tout2_HE1)
```

where:
- `Tout2_SP` is the operator-defined setpoint for the cold outlet
- `Tout2_HE1` is the measured cold outlet temperature
- `Tin1_SP_base` is an operator-defined base setpoint that sets the nominal operating temperature of the hot inlet
- `Kp_ext` is the outer proportional gain [°C / °C]

The output `Tin1_SP_cmd` is passed as the setpoint input to the inner PI+P controller, replacing the operator-set Tin1_SP when the system is in AUTO_FULL mode.

### 6.3.2 Steady-State Analysis and Offset

With a purely proportional outer controller, there will in general be a non-zero steady-state offset in Tout2. At steady state, the inner loop ensures Tin1 = Tin1_SP_cmd exactly (because the inner PI includes integral action). Substituting into the outer loop equation:

```
Tin1_ss = Tin1_SP_base + Kp_ext × (Tout2_SP − Tout2_ss)
```

If the relationship between Tin1 and Tout2 at steady state is approximately linear with gain K₂:
```
Tout2_ss = K₂ × Tin1_ss + d
```

Solving for Tout2_ss:
```
Tout2_ss = (K₂ × (Tin1_SP_base + Kp_ext × Tout2_SP) + d) / (1 + K₂ × Kp_ext)
```

The error |Tout2_SP − Tout2_ss| = |Tout2_SP − (K₂ × Tin1_SP_base + d)| / (1 + K₂ × Kp_ext).

The offset decreases as Kp_ext increases, but an overly large Kp_ext can destabilise the outer loop. In practice, the operator can eliminate the offset by adjusting `Tin1_SP_base` to the value that drives Tout2 to the desired setpoint at the current operating conditions — treating it as a manual feedforward trim.

### 6.3.3 P vs PI Outer Loop

Adding integral action to the outer loop (replacing P with PI) would eliminate the steady-state offset in Tout2 without manual trimming. However, this requires:
- Identification of the outer process (Tin1 → Tout2): a separate step-response experiment
- Careful tuning of the outer PI gains to maintain the required bandwidth separation from the inner loop

For this project, the outer loop uses proportional control only in the first phase, with a plan to upgrade to PI after validating the inner loop. This is the recommended commissioning sequence: stabilise and validate the inner loop before adding outer loop integral action.

## 6.4 Control Modes and State Machine

The `CascadeController` class implements a three-mode state machine:

| Mode | Constant | Inner loop | Outer loop | Operator input |
|------|----------|-----------|-----------|----------------|
| Manual | `MODE_MANUAL` | OFF | OFF | F1_SP set directly from UI |
| Auto Inner | `MODE_AUTO_INNER` | ON | OFF | Tin1_SP set by operator |
| Auto Full | `MODE_AUTO_FULL` | ON | ON | Tout2_SP set by operator |

**Mode transitions:**

```
MANUAL ──────────────────────────────→ AUTO_INNER
    set_mode(): init_output(F1_SP_current, Tin1_current) → bumpless

AUTO_INNER ──────────────────────────→ AUTO_FULL
    Outer loop activates: possible small bump if Tout2 error ≠ 0 at transition

Any AUTO mode ───────────────────────→ MANUAL
    Controller stops writing F1_SP; current value held at last output
    No explicit bumpless transfer needed (manual mode does not write F1_SP)
```

The transition MANUAL → AUTO_INNER calls `inner.init_output(current_F1_SP, current_Tin1)` to initialise the velocity form controller at the current physical state, ensuring the first controller output equals the current manual F1_SP.

**Identification interlock:** The identification step test is only permitted when the controller is in MANUAL mode. The `/api/identification/start` endpoint returns an error if `mode != MANUAL`. Conversely, the `/api/cascade/mode` endpoint refuses mode transitions while a step test is running (`state != IDLE` and `state != DONE`).

## 6.5 Experimental Validation

*(This section will be completed after closed-loop tests with Michal.)*

### 6.5.1 Inner Loop — Setpoint Step Response

*[Figure placeholder: Tin1_HE1 response to a step in Tin1_SP (e.g., +5°C), with F1_SP output on right axis. Both Normal and Aggressive tuning to be compared.]*

Metrics to be reported: rise time (10%–90%), settling time (±2%), overshoot percentage, steady-state error.

### 6.5.2 Inner Loop — Disturbance Rejection

*[Figure placeholder: Response of Tin1_HE1 and Tout2_HE1 to a furnace power change (T_hin disturbance), comparing open-loop (MANUAL) vs. closed inner loop (AUTO_INNER).]*

The key metric is the reduction in Tout2_HE1 deviation: with the inner loop active, a T_hin disturbance that would have caused a +X°C excursion in Tout2 should be reduced to a smaller deviation.

### 6.5.3 Full Cascade — Tout2 Setpoint Step

*[Figure placeholder: Tout2_HE1 and Tin1_HE1 responses to a step in Tout2_SP. Shows outer P controller driving Tin1_SP upward, inner PI+P executing the setpoint change.]*

Expected observation: Tout2_HE1 tracks Tout2_SP with a steady-state error consistent with the P-outer analysis. Tin1 reaches its commanded setpoint accurately (I term in inner loop).

### 6.5.4 Discussion

*(To be completed after experimental results.)*

Discussion points to address:
- Magnitude of steady-state offset in Tout2 and whether it is operationally acceptable
- Tuning level selected (Aggressive/Normal/Conservative) and rationale
- Observed inner loop settling time vs. expected τ
- Any oscillations or stability issues encountered

---

# Chapter 7 — Supervision Interface

## 7.1 Design Principles

The web interface serves two distinct user profiles with different needs:

**Panel operator (SIMATIC Unified 7" touchscreen):** An operator standing at the process, monitoring temperatures and flow rates, occasionally adjusting setpoints. Key needs: at-a-glance process state, large readable values, touch-friendly controls, no need for a keyboard. Screen constraint: 800×480 pixels (approximately 7-inch diagonal at 115 dpi). Typical viewing distance: 0.5–1.5 m.

**Process engineer (PC browser):** An engineer commissioning the cascade controller, running identification tests, analysing results, and tuning gains. Key needs: detailed process data, parameter entry forms, live trend charts, export capability. No screen size constraint.

These two profiles led to designing separate primary interfaces: the **Synoptique** (`/schema`) for the panel, and the **Cascade** (`/cascade`) for the engineer. Both share the same Socket.IO backend and update every 3 seconds.

Common visual design choices across all pages:
- Dark header with product identification and data source indicator (OPENPIPE / SIMULATION)
- Monospaced font for numerical values (prevents layout shifts when digits change)
- Coloured badges for discrete states (valve positions, controller mode)
- Minimal dependencies: Bootstrap 5 for layout, Chart.js for charts, no front-end framework

## 7.2 Synoptique — Panel Display

The Synoptique is a full-screen P&ID (Piping and Instrumentation Diagram) rendered as an inline SVG. The diagram shows the process layout: furnace on the left, heat exchanger in the centre, hot circuit flowing left-to-right at the top, cold circuit flowing right-to-left at the bottom.

**Animated flow lines:** CSS-animated dashed strokes create a visual flow indication. The hot circuit uses orange strokes, the cold circuit uses blue strokes. The animation runs continuously regardless of actual flow rate (a limitation: no flow-rate-proportional animation speed).

**Live value overlays:** Ten `<foreignObject>` elements (HTML islands inside SVG) display live values as styled cards. Each card shows the tag name, current value (monospaced, large font), and unit. These cards are positioned over the corresponding points on the P&ID diagram. The JavaScript Socket.IO handler updates each card's value every time a `process_tags` event arrives.

**Furnace power indicator:** A coloured dot (green = ON, red = OFF) and text label positioned next to the furnace symbol, driven by the `power` tag.

**Setpoint controls:** Two sets of increment/decrement buttons for F1_SP and F2_SP. Each button is sized for touch interaction (minimum 44×44 px per iOS HIG guidelines). Each press sends a REST call to `POST /api/process/write` with the tag name and delta. The current setpoint value is displayed between the buttons and updated via Socket.IO.

**Source indicator:** A badge in the top bar shows whether data is coming from OPENPIPE (green, real hardware) or SIMULATION (yellow, fallback). This prevents operators from mistaking simulated values for real ones.

## 7.3 Cascade Page — Engineering Tool

### 7.3.1 Identification Tab

The identification tab provides the full workflow from step test configuration to IMC gain application.

**Step test form:** Three inputs:
1. *Base F1_SP* (m³/h): auto-filled from the current PLC value when the tab loads; can be overridden
2. *Amplitude* (m³/h): the step size, with a sensible default of 0.5 m³/h
3. *Duration* (s): step test length, default 180 s

A "Start Test" button calls `POST /api/identification/start`. The button is disabled if the cascade is not in MANUAL mode (shown with a tooltip explaining the requirement).

**Progress display:** A two-phase progress bar shows the current state:
- Phase 1 — PRE-STEP (grey): 15 s baseline recording, fills at 20% per second
- Phase 2 — STEP (blue): the active step, fills proportionally over the configured duration

Below the progress bar, a status text shows the current phase and elapsed time.

**Live chart:** A Chart.js dual-axis line chart begins recording from the start of the test. The left Y-axis shows Tin1_HE1 (red solid) and Tout2_HE1 (orange dashed). The right Y-axis shows F1_SP (blue stepped). The X-axis shows elapsed seconds since step application. New data points are appended on each `ident_update` event.

**Results display:** When the test completes, a results section appears below the chart:
- Three KPI cards: K (with unit °C/(m³/h)), τ (s), θ (s)
- An IMC tuning table with three rows (Aggressive, Normal, Conservative), showing Kp and Ti for each λ level
- Each row has an "Apply & Switch" button that: loads the gains into the cascade controller via `POST /api/cascade/params`, then activates the Cascade Control tab

### 7.3.2 Cascade Control Tab

The cascade control tab provides the operator interface for commissioning and operating the cascade controller.

**Block diagram:** A CSS-styled diagram visually represents the cascade structure. Each block (C_outer, C_inner) shows its current gain values. Signal lines are styled with arrows indicating data direction.

**Parameter forms:** Two forms:
1. *Inner loop*: Kp and Ti inputs (pre-filled from current controller params)
2. *Outer loop*: Kp_ext input, Tin1_SP_base input

A "Set Parameters" button applies changes via `POST /api/cascade/params`. Changes take effect at the next poll cycle.

**Mode buttons:** Three large buttons for MANUAL, AUTO INNER, and AUTO FULL. The active mode is highlighted. Mode changes call `POST /api/cascade/mode`. A confirmation dialog warns before switching from AUTO back to MANUAL (to prevent accidental deactivation).

**Status grid:** A 2×3 table showing live controller state:

| | Inner loop (Tin1) | Outer loop (Tout2) |
|---|---|---|
| Setpoint | Tin1_SP | Tout2_SP |
| Measured | Tin1_HE1 | Tout2_HE1 |
| Error | e_inner | e_outer |

The F1_SP output (current controller output or manual value) is shown below the grid. All values update on each `cascade_data` Socket.IO event.

## 7.4 Real-Time Performance

**Socket.IO latency:** On a local Ethernet network (192.168.1.x subnet), the end-to-end latency from PLC poll to browser display is dominated by the 3-second poll period. The Socket.IO push itself adds < 10 ms of network latency on the lab network. The perceived update rate is 1 update every 3 seconds — adequate for a thermal process with time constants of tens of seconds.

**Chart.js rendering:** The identification chart accumulates up to 200 data points (10 minutes at 3 s/sample) without performance degradation, using `animation: false` to prevent re-rendering the full chart on each update. Only the new data point is appended via `chart.data.datasets[i].data.push(newPoint); chart.update('none')`.

**Panel browser compatibility:** The Flask web application has been tested in the Chromium-based browser embedded in the SIMATIC Unified 7" panel runtime. Bootstrap 5 and Chart.js 4 are compatible with this browser. Socket.IO WebSocket connections function correctly over the panel's local network interface.

## 7.5 Deployment Summary

| Environment | URL | Status |
|-------------|-----|--------|
| Development PC (localhost) | `http://localhost:5000` | Active |
| PC → Panel (lab network) | `http://192.168.1.149:5000` | Active (firewall rule added) |
| Panel Edge (target) | `http://192.168.1.200:30500` | Pending (licence required) |

The `.app` file has been generated with Siemens App Publisher and is ready for deployment. The only remaining step is obtaining Industrial Edge licence credentials to access the panel's Edge Management console.

---

# Chapter 8 — Conclusion

## 8.1 Summary of Contributions

This project has delivered three interconnected contributions to the supervision and control of the ICAM thermal process installation.

**Real-time web supervision system.** A Docker-based Flask application communicates with the Siemens S7-1500 PLC via two complementary protocols: Snap7 for direct data block access (DB1) and the Siemens Open Pipe mechanism for WinCC Unified tag exchange. The application provides four web pages accessible on the laboratory network: a P&ID synoptique optimised for the 7" SIMATIC Unified touch panel, a cascade engineering page for identification and commissioning, a process tag monitor for debugging, and a historical chart with CSV export. Socket.IO delivers real-time updates to all clients every 3 seconds without explicit polling.

**Experimental process identification.** An open-loop step-response identification experiment has been designed, implemented, and (results pending) conducted on the inner process (F1_SP → Tin1_HE1). The `StepIdentifier` class automates the three-phase test (baseline, step, analysis), extracts the FOPTD parameters K, τ, θ by the 63.2% method, and immediately calculates IMC-tuned PI gains at three aggressiveness levels. The engineer can apply any tuning level with a single click, which loads the gains into the cascade controller and activates the control tab.

**Cascade PI+P controller.** A cascade controller has been implemented in Python with: an inner PI loop using the velocity form with proportional action on measurement (P-on-M) for bumpless transfer and implicit anti-windup; an outer proportional controller driving the cold outlet temperature setpoint; and a three-mode state machine (Manual / Auto-Inner / Auto-Full) with safe mode transitions. The entire controller runs in a background thread, writing F1_SP to the PLC via Open Pipe every 3 seconds.

## 8.2 Results Assessment

*(To be completed after experimental session and closed-loop validation)*

**Identification:** The extracted parameters K, τ, θ will characterise the inner process dynamic and confirm the applicability of the FOPTD model. The quality of the step response curve (noise level, clean transient) will validate the 3-second sampling period as adequate for identification.

**Controller performance:** The IMC-tuned PI+P inner loop is expected to regulate Tin1_HE1 with a settling time of approximately 2τ and negligible steady-state error (I term). The P outer loop will exhibit a residual offset in Tout2_HE1, quantifiable from the steady-state analysis.

**Interface:** The Synoptique page has been tested on the panel browser via the PC's local IP address, confirming rendering, layout, and Socket.IO connectivity. The Cascade page's identification workflow has been functionally verified in simulation mode.

## 8.3 Limitations

**Sampling period:** The 3-second poll rate, dictated by the Open Pipe implementation and the decision to avoid overloading the panel's WinCC Unified runtime, limits the identification resolution to ±3 s on both τ and θ. For processes with dead times shorter than approximately 6 s, this resolution may be inadequate for accurate IMC tuning. The thermal process under study has a dead time significantly larger than this (estimated 5–15 s), so the limitation is not critical in this case.

**P outer loop offset:** The outer proportional controller introduces a non-zero steady-state error in Tout2_HE1. For precise temperature regulation, the operator must adjust `Tin1_SP_base` manually or the outer loop must be upgraded to PI. This is identified as the primary performance limitation of the cascade implementation.

**Open Pipe validation:** The Open Pipe communication is implemented based on documented protocol structure and laboratory tests in simulation mode. Full validation against the WinCC Unified runtime on the SIMATIC Unified panel requires the Industrial Edge deployment, which is pending licence credentials. Until deployed on the panel, the Open Pipe path has not been tested end-to-end with real WinCC tag exchange.

**No safety interlocks:** The web application does not implement PLC-level safety interlocks (high-temperature cutoff, flow-loss detection). Process safety relies entirely on the TIA Portal program. This is appropriate for a laboratory demonstrator but would need to be addressed for any production use.

## 8.4 Perspectives

**Outer loop PI upgrade:** Once the inner loop is validated in closed loop, an identification experiment on the outer process (Tin1 → Tout2) should be conducted to extract K₂, τ₂, θ₂. These parameters enable IMC tuning of a PI outer controller, eliminating the steady-state Tout2 offset.

**Faster sampling:** The Open Pipe poll rate could be reduced from 3 s to 1 s by offloading the cascade controller computation to a separate thread and accepting a slightly higher load on the panel. This would improve both identification resolution and controller bandwidth.

**Alarm management:** The web application currently has no process alarms. Adding configurable thresholds (high T_hin, low F1, valve fault detection) with Socket.IO alarm events would improve operator safety awareness.

**Complete Edge deployment:** Obtaining Industrial Edge licence credentials and completing the panel deployment would realise the original vision of an embedded supervision interface, independent of the development PC.

**Data analytics:** The append-only CSV log provides raw data but no analysis. Adding a lightweight analytics endpoint (trend statistics, energy balance computation, identification quality metrics) would increase the value of the logged data for the engineering team.

---

# References

1. Seborg, D.E., Edgar, T.F., Mellichamp, D.A., Doyle III, F.J. *Process Dynamics and Control*, 4th edition. Wiley, 2017.

2. Rivera, D.E., Morari, M., Skogestad, S. "Internal model control — 4. PID controller design." *Industrial & Engineering Chemistry Process Design and Development*, 25(1), pp. 252–265, 1986.

3. Morari, M., Zafiriou, E. *Robust Process Control*. Prentice Hall, 1989.

4. Åström, K.J., Hägglund, T. *Advanced PID Control*. ISA, 2006.

5. Siemens AG. *SIMATIC S7-1500 System Manual*. Nürnberg: Siemens, 2023. [Online, requires Siemens ID login]

6. Siemens AG. *TIA Portal V18 — Programming Guideline for S7-1500*. Nürnberg: Siemens, 2023.

7. Siemens AG. *WinCC Unified — Open Pipe Functionality*. Siemens Industry Support documentation, 2022.

8. Siemens AG. *Industrial Edge — App Developer Guide*. Siemens, 2023.

9. Gijsbers, A. python-snap7 — Python wrapper for the Snap7 S7 communication library. Available at: https://github.com/gijzelaerr/python-snap7

10. Pallets Project. *Flask Documentation*, v3.0. Available at: https://flask.palletsprojects.com

11. Socket.IO. *Socket.IO Documentation*, v4.x. Available at: https://socket.io/docs

12. Chart.js. *Chart.js Documentation*, v4.x. Available at: https://www.chartjs.org/docs

---

# Appendix A — WinCC Unified Tag Table (21 Tags)

| Tag name | Type | PLC Address | Raw address | Range | Unit | Description |
|----------|------|-------------|-------------|-------|------|-------------|
| T_hin | Real | %MD16 | %IW300 | 0–200 | °C | Furnace inlet temperature |
| T_hout | Real | %MD12 | %IW304 | 0–200 | °C | Furnace outlet temperature |
| T_we_rock_furnace | Int | — | %IW300 | 0–27648 | ADC | Furnace inlet raw ADC |
| T_wy_Oven_scale | Int | — | %IW304 | 0–27648 | ADC | Furnace outlet raw ADC |
| Tin1_HE1 | Real | %MD48 | %IW112 | 0–200 | °C | HE hot inlet temperature |
| Tout1_HE1 | Real | %MD44 | %IW120 | 0–200 | °C | HE hot outlet temperature |
| Tin2_HE1 | Real | %MD40 | %IW116 | 0–200 | °C | HE cold inlet temperature |
| Tout2_HE1 | Real | %MD52 | %IW108 | 0–200 | °C | HE cold outlet temperature |
| Tin1_heat_exchanger1_scale | Int | — | %IW112 | 0–27648 | ADC | Tin1 raw ADC |
| Tout1_HE1_raw | Int | — | %IW120 | 0–27648 | ADC | Tout1 raw ADC |
| Tin2_HE1_raw | Int | — | %IW116 | 0–27648 | ADC | Tin2 raw ADC |
| Tout2_HE1_raw | Int | — | %IW108 | 0–27648 | ADC | Tout2 raw ADC |
| F1 | Real | %MD28 | %IW316 | 0–10 | m³/h | Hot circuit flow rate |
| F1_SP | Real | %MD24 | — | 0–10 | m³/h | Hot circuit flow setpoint |
| F1_skal | Int | — | %IW316 | 0–27648 | ADC | F1 raw ADC |
| Valve_F1 | Word | %QW8 | — | 0–27648 | — | Hot valve command word |
| F2 | Real | %MD32 | %IW204 | 0–10 | m³/h | Cold circuit flow rate |
| F2_SP | Real | %MD36 | — | 0–10 | m³/h | Cold circuit flow setpoint |
| F2_skal | Int | — | %IW204 | 0–27648 | ADC | F2 raw ADC |
| Valve_F2 | Int | %QW4 | — | 0–27648 | — | Cold valve command |
| power | Bool | %Q0.3 | — | 0–1 | — | Furnace power (ON=1) |

---

# Appendix B — DB1 Structure for Snap7 Access

DB1 must be configured with **Optimized block access disabled** in TIA Portal (Properties → Attributes).

| Byte offset | TIA Portal type | Variable name | Description |
|-------------|-----------------|---------------|-------------|
| DBD0 | REAL | temperature | Measured temperature — Tin1_HE1 (°C) |
| DBD4 | REAL | flow_rate | Measured flow rate — F1 (m³/h) |
| DBD8 | REAL | setpoint_temp | Temperature setpoint (°C) |
| DBD12 | REAL | setpoint_flow | Flow setpoint — F1_SP (m³/h) |
| DBW16 | INT | valve_state | 0 = CLOSED, 1 = OPEN, 2 = PARTIAL |

**Reading with Snap7 (Python):**
```python
raw = client.db_read(db_number=1, start=0, size=20)
temperature  = snap7.util.get_real(raw, 0)
flow_rate    = snap7.util.get_real(raw, 4)
setpoint_T   = snap7.util.get_real(raw, 8)
setpoint_F   = snap7.util.get_real(raw, 12)
valve_state  = snap7.util.get_int(raw,  16)
```

---

# Appendix C — Key Code Extracts

## C.1 PI+P Velocity Form (`cascade_controller.py`)

```python
def update(self, setpoint: float, measurement: float) -> float:
    """
    Velocity-form PI with proportional on measurement.
    Bumpless: no kick on setpoint change.
    Anti-windup: implicit via output clamping.
    """
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

def init_output(self, current_output: float, current_meas: float):
    """Initialize for bumpless transfer from manual to auto."""
    self.last_output = current_output
    self._last_meas = current_meas
```

## C.2 IMC Gain Calculation (`identification.py`)

```python
def _compute_imc(self, K: float, tau: float, theta: float) -> dict:
    """
    IMC tuning for PI controller.
    Returns three gain sets: aggressive (lambda=0.5*tau),
    normal (lambda=tau), conservative (lambda=2*tau).
    """
    results = {}
    for label, factor in [('aggressive', 0.5), ('normal', 1.0), ('conservative', 2.0)]:
        lam = max(factor * tau, theta)  # lambda >= theta (physical lower bound)
        Kp  = round(tau / (K * (lam + theta)), 4) if K != 0 else 0.0
        Ti  = round(tau, 1)
        results[label] = {'Kp': Kp, 'Ti': Ti, 'lambda': round(lam, 1)}
    return results
```

## C.3 Open Pipe Read (`openpipe_connector.py`)

```python
def _read_via_socket(self, tag_names: list) -> dict:
    """Read multiple WinCC Unified tags via Open Pipe Unix socket."""
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

## C.4 Cascade Poll Loop Excerpt (`main.py`)

```python
def _openpipe_poll_loop():
    while True:
        tags = openpipe.read_all_tags()
        Tin1  = tags.get('Tin1_HE1',  0.0)
        Tout2 = tags.get('Tout2_HE1', 0.0)

        # Identification takes priority over cascade control
        new_sp = ident.feed(Tin1, Tout2, tags.get('F1_SP', 0.0))
        if new_sp is not None:
            openpipe.write_tag('F1_SP', new_sp)
        elif cascade.mode != CascadeController.MODE_MANUAL:
            ctrl_sp = cascade.update(Tin1, Tout2)
            if ctrl_sp is not None:
                openpipe.write_tag('F1_SP', ctrl_sp)

        socketio.emit('process_tags', tags)
        socketio.emit('cascade_data', cascade.get_status())
        if ident.state not in ('idle', 'done'):
            socketio.emit('ident_update', ident.get_status())

        time.sleep(3.0)
```

---

# Appendix D — Step Response Experimental Results

*(To be completed after experimental session on 2026-05-19)*

**D.1 Raw data table** — Time, Tin1_HE1, Tout2_HE1, F1_SP at each 3-second sample

**D.2 Identification chart** — Step response curves with K, τ, θ annotations

**D.3 IMC gain table** — Calculated values for Aggressive, Normal, Conservative levels

---

# Appendix E — User Manual (Supervision Interface)

## E.1 Accessing the Interface

From any browser on the laboratory network (192.168.1.x):
- **Synoptique (panel view):** `http://192.168.1.149:5000/schema`
- **Cascade (engineering tool):** `http://192.168.1.149:5000/cascade`
- **Process tags (debug):** `http://192.168.1.149:5000/process`

Replace `192.168.1.149` with the IP of the PC running the application (or `192.168.1.200:30500` once Edge is deployed).

The top bar shows a green "OPENPIPE" badge when connected to real hardware, or a yellow "SIMULATION" badge in simulation mode.

## E.2 Running an Identification Test

1. Ensure the furnace has been running for at least 30 minutes and process is at steady state
2. Navigate to `/cascade` → Identification tab
3. Confirm that the cascade controller is in **MANUAL** mode (check the Cascade Control tab)
4. On the Identification tab, verify the auto-filled Base F1_SP value; adjust Amplitude (default: 0.5 m³/h) and Duration (default: 180 s)
5. Press **Start Test** — the chart begins recording and a progress bar tracks the test
6. Wait for the test to complete automatically (F1_SP is restored automatically at the end)
7. Review the results: K, τ, θ cards and IMC table
8. Press **Apply & Switch** on the desired tuning level (Normal recommended for first test)

## E.3 Commissioning the Cascade Controller

1. After applying IMC gains from the identification, the Cascade Control tab opens automatically
2. Verify the inner loop gains (Kp, Ti) and outer loop gain (Kp_ext = 2.0 default)
3. Set the Inner Tin1_SP to approximately the current Tin1_HE1 value (read from the status grid)
4. Press **AUTO INNER** — the inner loop activates with bumpless transfer
5. Observe Tin1_HE1: it should hold at the Tin1_SP setpoint with < 2°C steady-state error
6. Adjust Tin1_SP upward or downward to test the inner loop step response
7. Once the inner loop is validated, set Tout2_SP to the desired cold outlet temperature
8. Press **AUTO FULL** — the outer loop activates, adjusting Tin1_SP to drive Tout2 toward Tout2_SP
9. If Tout2 does not reach Tout2_SP exactly (P outer offset), trim Tin1_SP_base to compensate

To return to manual: press **MANUAL** (a confirmation dialog will appear).
