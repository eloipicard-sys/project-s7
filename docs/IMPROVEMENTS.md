# Interface Improvement Notes
## Thermal Process Monitor — S7-1500

Suggested enhancements for future iterations, ordered by academic relevance.

---

## 1. Performance Indices (high priority — thesis)

Add IAE, ISE and ITAE computed client-side in JavaScript, accumulated from
the moment a setpoint change is detected and reset on each new step.

| Index | Formula | Characteristic |
|---|---|---|
| IAE | sum \|e[k]\| · T | Balanced, most common |
| ISE | sum e[k]² · T | Penalises large deviations heavily |
| ITAE | sum k·T·\|e[k]\| · T | Penalises errors that persist — rewards speed |

Display as a small table below the PID metrics, reset automatically on each
setpoint change. Export values alongside the CSV log.

---

## 2. Step Response Metrics (high priority — thesis)

Detect setpoint changes automatically and measure:

- **Rise time** — time to reach 90% of the new setpoint
- **Overshoot** — maximum exceedance above setpoint (%)
- **Settling time** — time to remain within ±5% of setpoint
- **Steady-state error** — residual error after settling

Display as a summary card that appears after each step, useful for
comparing PID tuning configurations in the thesis.

---

## 3. Control Output u(t) Chart

A second Chart.js chart showing the heater output u(t) (0–100%) over time,
displayed below or alongside the PV vs SP chart. Essential for discussing
controller behaviour, especially integrator windup and derivative kick.

---

## 4. Error Evolution Chart e(t)

Dedicated chart for e(t) = SP − PV over time. Visualises convergence to
zero and makes overshoot immediately readable. Useful for comparing
different Kp/Ki/Kd settings side by side in the thesis figures.

---

## 5. Alarm Bands on Temperature Chart

Overlay configurable horizontal bands on the PV/SP chart:

- Warning band (e.g. ±10°C from setpoint) — light yellow fill
- Critical band (e.g. ±25°C) — light red fill

Bands remain visible when the process is within normal range, providing
immediate context for deviations.

---

## 6. Phase Portrait e(t) vs de/dt

A scatter/line chart with error on the X axis and its derivative on the Y
axis, updated in real time. The trajectory spirals toward (0, 0) for a
stable, well-tuned controller. A classic academic visualisation for control
system analysis.

---

## 7. Valve Position Gauge

Replace the text card (OPEN / CLOSED / PARTIAL) with a visual arc gauge
(0–100%) reflecting the inferred valve opening derived from u(t). More
intuitive for live demonstrations.

---

## 8. PLC / Simulation Status Badge

Prominent header badge showing the current data source:
- `SIMULATION` — grey, neutral
- `PLC CONNECTED` — dark, filled

Should update dynamically by polling `/api/status` every 10 seconds,
without requiring a page reload.

---

## Implementation Notes

- All chart additions should use the existing Chart.js 4.4.0 import.
- Performance indices (IAE, ISE, ITAE) and step metrics are purely
  client-side — no server changes required.
- Alarm thresholds could be exposed as configurable fields in the
  Setpoint Control panel and stored in `.env` for persistence.
- The phase portrait requires storing the last two error values to
  compute the derivative; minimal state overhead.
