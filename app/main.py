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

from plc_connector      import PLCConnector
from thermal_model      import ThermalProcessModel
from logger             import init_logger, log_sample, get_log_path, get_log_stats
from openpipe_connector import OpenPipeConnector
from cascade_controller import CascadeController
from identification     import StepIdentifier

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ── Singletons ────────────────────────────────────────────────────────────────
plc          = PLCConnector()
model        = ThermalProcessModel(dt=3.0, tau_T=45.0, K_proc=220.0, T_init=20.0)
openpipe     = OpenPipeConnector()
cascade_ctrl = CascadeController()
step_ident   = StepIdentifier()
init_logger()

# Attempt PLC connection at startup (non-blocking)
plc.connect()
openpipe.set_snap7_fallback(plc)

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
            log_sample(d)
            with _sim_lock:
                _last_sim = d
            socketio.emit('process_tags', d)
        except Exception as exc:
            logging.warning(f"PLC broadcast failed: {exc}")

threading.Thread(target=_plc_poll_loop, daemon=True, name="plc-poll").start()


def _openpipe_poll_loop():
    """Daemon thread: poll Open Pipe tags every 3 s, run cascade/identification, broadcast."""
    while True:
        time.sleep(3)
        try:
            data = openpipe.read_all_tags()
            data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

            Tin1        = data.get('Tin1_HE1', 0.0)
            Tout2       = data.get('Tout2_HE1', 0.0)
            T_hout      = data.get('T_hout', 0.0)     # small-furnace outlet (smallOutlet)
            F1          = data.get('F1', 2.0)          # measured flow (L/min)
            PWM_current = data.get('HeaterLarge_PWM', 50.0)

            # Identification takes priority over cascade auto-control
            ident_write = step_ident.feed(Tin1, Tout2, PWM_current, T_hout)
            if ident_write is not None:
                openpipe.write_tag('HeaterLarge_PWM', ident_write)
            elif cascade_ctrl.mode != CascadeController.MODE_MANUAL:
                pwm_new = cascade_ctrl.update(Tin1, Tout2, F1)
                if pwm_new is not None:
                    openpipe.write_tag('HeaterLarge_PWM', pwm_new)
            else:
                cascade_ctrl.update(Tin1, Tout2, F1)

            socketio.emit('process_tags', data)

            ident_st = step_ident.get_status()
            socketio.emit('ident_update', {
                'status': ident_st,
                'chart':  step_ident.get_chart_data() if ident_st['state'] != StepIdentifier.IDLE else [],
            })

            cascade_st = cascade_ctrl.get_status()
            cascade_st['timestamp'] = data['timestamp']
            socketio.emit('cascade_data', cascade_st)

        except Exception as exc:
            logging.warning(f"Open Pipe poll failed: {exc}")

threading.Thread(target=_openpipe_poll_loop, daemon=True, name="openpipe-poll").start()


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


@app.route("/process")
def process_page():
    return render_template("process.html",
                           openpipe_available=openpipe.is_available())


@app.route("/schema")
def schema_page():
    return render_template("schema.html")


@app.route("/api/process/data")
def process_data():
    """JSON endpoint — all 21 WinCC Unified tags."""
    data = openpipe.read_all_tags()
    data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return jsonify(data)


@app.route("/api/process/write", methods=["POST"])
def process_write():
    """Write a writable tag (F1_SP, F2_SP) via Open Pipe."""
    data = request.get_json(force=True)
    tag   = data.get("tag", "")
    value = data.get("value")
    if tag not in ("F1_SP", "F2_SP", "HeaterLarge_PWM"):
        return jsonify({"ok": False, "error": "Only F1_SP, F2_SP and HeaterLarge_PWM are writable"}), 400
    try:
        ok = openpipe.write_tag(tag, float(value))
        return jsonify({"ok": ok, "tag": tag, "value": value})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


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


# ══════════════════════════════════════════════════════════════════════════════
# CASCADE CONTROL & IDENTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/cascade")
def cascade_page():
    return render_template("cascade.html")


@app.route("/api/cascade/status")
def cascade_status():
    return jsonify(cascade_ctrl.get_status())


@app.route("/api/cascade/mode", methods=["POST"])
def cascade_mode():
    data  = request.get_json(force=True)
    mode  = data.get("mode", "")
    tags        = openpipe.read_all_tags()
    current_PWM = tags.get("HeaterLarge_PWM", 50.0)
    Tin1        = tags.get("Tin1_HE1", 0.0)
    try:
        cascade_ctrl.set_mode(mode, current_PWM=current_PWM, current_Tin1=Tin1)
        return jsonify({"ok": True, "mode": mode})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/cascade/setpoint", methods=["POST"])
def cascade_setpoint():
    data = request.get_json(force=True)
    if "Tout2_SP" in data:
        cascade_ctrl.set_Tout2_SP(float(data["Tout2_SP"]))
    if "Tin1_SP" in data:
        cascade_ctrl.set_Tin1_SP(float(data["Tin1_SP"]))
    return jsonify({"ok": True, **cascade_ctrl.get_status()})


@app.route("/api/cascade/params", methods=["POST"])
def cascade_params():
    data = request.get_json(force=True)
    if "inner_Kp" in data and "inner_Ti" in data:
        cascade_ctrl.set_inner_params(float(data["inner_Kp"]), float(data["inner_Ti"]))
    if "outer_Kp" in data:
        cascade_ctrl.set_outer_params(float(data["outer_Kp"]))
    return jsonify({"ok": True, **cascade_ctrl.get_status()})


@app.route("/api/identification/start", methods=["POST"])
def ident_start():
    if cascade_ctrl.mode != CascadeController.MODE_MANUAL:
        return jsonify({"ok": False, "error": "Mettre la cascade en MANUEL avant d'identifier"}), 400
    data       = request.get_json(force=True)
    tags       = openpipe.read_all_tags()
    base_F1    = float(data.get("base_F1_SP", tags.get("F1_SP", 2.0)))
    amplitude  = float(data.get("amplitude", 0.5))
    duration_s = float(data.get("duration_s", 120))
    step_ident.start(base_F1, amplitude, duration_s)
    return jsonify({"ok": True, "base_F1_SP": base_F1, "step_F1_SP": base_F1 + amplitude})


@app.route("/api/identification/cancel", methods=["POST"])
def ident_cancel():
    restore = step_ident.cancel()
    if restore is not None:
        openpipe.write_tag('F1_SP', restore)
    return jsonify({"ok": True, "restored_F1_SP": restore})


@app.route("/api/identification/status")
def ident_status_route():
    return jsonify(step_ident.get_status())


@app.route("/api/identification/data")
def ident_data_route():
    return jsonify({"data": step_ident.get_chart_data()})


@app.route("/api/identification/push_params", methods=["POST"])
def ident_push_params():
    """Write identified krPI and TiPI to PLC DB (DBD56, DBD60) and update cascade gains."""
    st     = step_ident.get_status()
    result = st.get('result', {})
    krPI   = result.get('krPI')
    TiPI   = result.get('TiPI')
    if krPI is None or TiPI is None:
        return jsonify({"ok": False,
                        "error": "No krPI/TiPI available — run identification first"}), 400
    # Always update the in-memory cascade controller
    cascade_ctrl.set_inner_params(krPI, TiPI)
    if not plc.is_connected():
        return jsonify({"ok": True, "krPI": krPI, "TiPI": TiPI,
                        "plc_written": False, "note": "PLC not connected — cascade updated only"})
    try:
        plc.write_pi_params(krPI, TiPI)
        return jsonify({"ok": True, "krPI": krPI, "TiPI": TiPI, "plc_written": True})
    except Exception as exc:
        logging.error(f"PI params PLC write failed: {exc}")
        return jsonify({"ok": False, "error": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    print(f"Flask started on port {port}")
    print(f"PLC target: {os.getenv('PLC_IP', 'not configured')}")
    socketio.run(app, host="0.0.0.0", port=port, debug=debug, use_reloader=False, allow_unsafe_werkzeug=True)
