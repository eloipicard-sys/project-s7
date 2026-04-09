"""
Flask application — Siemens S7-1500 Thermal Process Monitoring

Architecture:
  - plc_connector.py : Snap7 interface (real PLC, Friday)
  - thermal_model.py : first-order simulation (until PLC is connected)
  - logger.py        : CSV data persistence
  - templates/       : Jinja2 HTML templates (index.html, test.html)
"""

from flask import Flask, jsonify, render_template, request, send_file
from flask_socketio import SocketIO
import time
import os
import logging
import threading

from plc_connector  import PLCConnector
from thermal_model  import ThermalProcessModel
from logger         import init_logger, log_sample, get_log_path, get_log_stats

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ── Singletons ────────────────────────────────────────────────────────────────
plc   = PLCConnector()
model = ThermalProcessModel(dt=3.0, tau_T=45.0, K_proc=220.0, T_init=20.0)
init_logger()

# Attempt PLC connection at startup (non-blocking)
plc.connect()

# In-memory setpoints (used by simulation; overridden by PLC values when connected)
process_setpoints = {
    "temperature": 200.0,
    "flow_rate":   3.5,
}
_setpoints_lock = threading.Lock()

# ── Background simulation thread ──────────────────────────────────────────────
# The simulation advances on its own timer (every model.dt seconds), independent
# of HTTP polling. Multiple clients or the 1-second /test page cannot skew the
# simulation clock. get_plc_data() just reads the latest cached result.
_sim_lock  = threading.Lock()
_last_sim: dict = {}


def _simulation_loop():
    """Daemon thread: advance thermal model every dt seconds."""
    global _last_sim
    while True:
        time.sleep(model.dt)
        if plc.is_connected():
            continue  # real PLC active — skip simulation step
        with _setpoints_lock:
            sp_t = process_setpoints["temperature"]
            sp_f = process_setpoints["flow_rate"]
        step = model.step(sp_t, sp_f)
        valve = ("OPEN"    if step["u_percent"] > 66 else
                 "PARTIAL" if step["u_percent"] > 10 else "CLOSED")
        result = {
            "temperature":   step["temperature"],
            "flow_rate":     step["flow_rate"],
            "setpoint_temp": sp_t,
            "setpoint_flow": sp_f,
            "valve_state":   valve,
            "timestamp":     time.strftime("%Y-%m-%d %H:%M:%S"),
            "plc_ip":        os.getenv("PLC_IP", "not configured"),
            "source":        "SIMULATION",
        }
        with _sim_lock:
            _last_sim = result
        log_sample(result)
        socketio.emit('process_data', result)


threading.Thread(target=_simulation_loop, daemon=True, name="sim-loop").start()


def _plc_poll_loop():
    """Daemon thread: poll PLC and broadcast via Socket.IO when connected."""
    while True:
        time.sleep(model.dt)
        if not plc.is_connected():
            continue
        try:
            d = plc.read_process_data()
            d.update({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "plc_ip": plc.plc_ip,
                      "source": "PLC"})
            with _setpoints_lock:
                process_setpoints["temperature"] = d["setpoint_temp"]
                process_setpoints["flow_rate"]   = d["setpoint_flow"]
            log_sample(d)
            with _sim_lock:
                _last_sim = d
            socketio.emit('process_data', d)
        except Exception as exc:
            logging.warning(f"PLC broadcast failed: {exc}")

threading.Thread(target=_plc_poll_loop, daemon=True, name="plc-poll").start()


def get_plc_data() -> dict:
    """
    Return the latest process data sample.
    Priority: real PLC → cached simulation result.
    """
    if plc.is_connected():
        try:
            d = plc.read_process_data()
            d.update({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "plc_ip": plc.plc_ip,
                      "source": "PLC"})
            with _setpoints_lock:
                process_setpoints["temperature"] = d["setpoint_temp"]
                process_setpoints["flow_rate"]   = d["setpoint_flow"]
            log_sample(d)
            return d
        except Exception as exc:
            logging.warning(f"PLC read failed, falling back to simulation: {exc}")

    # Return latest cached simulation result
    with _sim_lock:
        if _last_sim:
            return dict(_last_sim)

    # Sim thread hasn't produced a result yet — return initial model state
    with _setpoints_lock:
        sp_t = process_setpoints["temperature"]
        sp_f = process_setpoints["flow_rate"]
    return {
        "temperature":   model.temperature,
        "flow_rate":     model.flow_rate,
        "setpoint_temp": sp_t,
        "setpoint_flow": sp_f,
        "valve_state":   "CLOSED",
        "timestamp":     time.strftime("%Y-%m-%d %H:%M:%S"),
        "plc_ip":        os.getenv("PLC_IP", "not configured"),
        "source":        "SIMULATION",
    }


# ── Web routes ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    with _setpoints_lock:
        sp_temp = process_setpoints["temperature"]
        sp_flow = process_setpoints["flow_rate"]
    return render_template("index.html", sp_temp=sp_temp, sp_flow=sp_flow)


@app.route("/api/data")
def api_data():
    """JSON endpoint — real-time process data."""
    return jsonify(get_plc_data())


@app.route("/api/setpoint", methods=["POST"])
def set_setpoint():
    """
    Update process setpoints.
    Writes to PLC DB if connected; otherwise updates in-memory simulation setpoints.
    """
    data = request.get_json(force=True)
    updated = []

    if "temperature" in data:
        val = float(data["temperature"])
        if not (0 <= val <= 500):
            return jsonify({"error": "Temperature setpoint out of range (0–500 deg C)"}), 400
        with _setpoints_lock:
            process_setpoints["temperature"] = val
        if plc.is_connected():
            plc.write_temperature_setpoint(val)
        updated.append(f"temperature -> {val} deg C")

    if "flow_rate" in data:
        val = float(data["flow_rate"])
        if not (0 <= val <= 20):
            return jsonify({"error": "Flow rate setpoint out of range (0–20 m3/h)"}), 400
        with _setpoints_lock:
            process_setpoints["flow_rate"] = val
        if plc.is_connected():
            plc.write_flow_setpoint(val)
        updated.append(f"flow rate -> {val} m3/h")

    if not updated:
        return jsonify({"error": "No valid setpoint provided"}), 400

    with _setpoints_lock:
        current = dict(process_setpoints)
    return jsonify({
        "message": "Setpoint applied: " + ", ".join(updated),
        "setpoints": current,
        "plc_write": plc.is_connected()
    })


@app.route("/api/export/csv")
def export_csv():
    """Download the full process log as a CSV file."""
    log_path = get_log_path()
    if not log_path.exists():
        return jsonify({"error": "No log data available yet"}), 404
    filename = f"process_log_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    return send_file(str(log_path), mimetype="text/csv",
                     as_attachment=True, download_name=filename)


@app.route("/api/status")
def status():
    """System status: PLC connection, data source, log stats."""
    stats = get_log_stats()
    return jsonify({
        "plc_connected": plc.is_connected(),
        "plc_ip":        plc.plc_ip or "not configured",
        "data_source":   "PLC" if plc.is_connected() else "SIMULATION",
        "log":           stats,
    })


@app.route("/health")
def health():
    """Docker healthcheck endpoint."""
    return jsonify({"status": "ok", "service": "s7-thermal-app"}), 200


# ══════════════════════════════════════════════════════════════════════════════
# TEST INTERFACE — V1 BOOL / V2–V9 INT / counter INT (read-only)
# DB number configured via PLC_TEST_DB env var (default: 1)
# TIA Portal DB layout: 20 bytes total (see plc_connector.py)
# ⚠ DB must have "Optimized block access" DISABLED in TIA Portal properties
# ══════════════════════════════════════════════════════════════════════════════

TEST_DB = int(os.getenv("PLC_TEST_DB", 1))


@app.route("/test")
def test_interface():
    connected = plc.is_connected()
    return render_template("test.html",
                           test_db=TEST_DB,
                           connected=connected,
                           plc_ip=plc.plc_ip or "not configured")


@app.route("/api/test/read")
def test_read():
    """Read all test variables from DB (V1 BOOL, V2–V9 INT, counter INT)."""
    if not plc.is_connected():
        return jsonify({"connected": False, "error": "PLC not connected"}), 503
    try:
        data = plc.read_test_vars(TEST_DB)
        data["connected"] = True
        data["db"] = TEST_DB
        return jsonify(data)
    except Exception as exc:
        logging.error(f"[TEST] read failed: {exc}")
        return jsonify({"connected": False, "error": str(exc)}), 500


@app.route("/api/test/write", methods=["POST"])
def test_write():
    """Write V1 (BOOL) or V2–V9 (INT) to the test DB."""
    if not plc.is_connected():
        return jsonify({"ok": False, "error": "PLC not connected"}), 503
    data = request.get_json(force=True)
    variable = data.get("variable", "").upper()
    try:
        if variable == "V1":
            value = bool(data["value"])
            plc.write_test_v1(TEST_DB, value)
            return jsonify({"ok": True, "variable": "V1", "value": value})
        elif variable in ("V2","V3","V4","V5","V6","V7","V8","V9"):
            value = int(data["value"])
            plc.write_test_int(TEST_DB, variable, value)
            return jsonify({"ok": True, "variable": variable, "value": value})
        else:
            return jsonify({"ok": False, "error": "Unknown variable (use V1 or V2–V9)"}), 400
    except Exception as exc:
        logging.error(f"[TEST] write {variable} failed: {exc}")
        return jsonify({"ok": False, "error": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    print(f"Flask started on port {port}")
    print(f"PLC target: {os.getenv('PLC_IP', 'not configured')}")
    socketio.run(app, host="0.0.0.0", port=port, debug=debug, use_reloader=False, allow_unsafe_werkzeug=True)
