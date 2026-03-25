"""
SIK Radio Configurator - Web UI backend (Flask)
Serves a modern browser-based configurator, similar in style to Betaflight / INAV.
"""

import os
import sys
import json
import logging
import webbrowser
import threading

from flask import Flask, request, jsonify, send_from_directory

sys.path.insert(0, os.path.dirname(__file__))

import serial.tools.list_ports
from src.serial_protocol import SIKRadioProtocol
from src.config_manager import RadioConfiguration

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(32))

# ── global state ─────────────────────────────────────────────────────────────
protocol: SIKRadioProtocol | None = None
config = RadioConfiguration()


# ── helpers ──────────────────────────────────────────────────────────────────
def _err(msg: str, code: int = 400):
    return jsonify({"success": False, "error": msg}), code


def _ok(payload: dict | None = None):
    return jsonify({"success": True, **(payload or {})})


# ── static / root ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(TEMPLATE_DIR, "index.html")


# ── serial ports ─────────────────────────────────────────────────────────────
@app.route("/api/ports")
def get_ports():
    ports = [
        {"device": p.device, "description": p.description or p.device}
        for p in serial.tools.list_ports.comports()
    ]
    return jsonify(ports)


# ── connection ───────────────────────────────────────────────────────────────
@app.route("/api/connect", methods=["POST"])
def connect():
    global protocol
    data = request.get_json(force=True, silent=True) or {}
    port = data.get("port", "").strip()
    baud = int(data.get("baud", 57600))

    if protocol and protocol.is_connected():
        protocol.disconnect()

    if not port:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports:
            return _err("No serial ports found")
        port = ports[0]

    protocol = SIKRadioProtocol(port, baudrate=baud)
    if protocol.connect():
        logger.info(f"Connected to {port} @ {baud}")
        return _ok({"port": port, "baud": baud})

    protocol = None
    return _err(f"Failed to connect to {port}")


@app.route("/api/disconnect", methods=["POST"])
def disconnect():
    global protocol
    if protocol:
        protocol.disconnect()
        protocol = None
    return _ok()


@app.route("/api/status")
def get_status():
    connected = protocol is not None and protocol.is_connected()
    info = {}
    if connected:
        info = {"port": protocol.port, "baud": protocol.baudrate}
    return jsonify({"connected": connected, **info})


# ── parameters ────────────────────────────────────────────────────────────────
@app.route("/api/parameters")
def get_parameters():
    global config
    if not protocol or not protocol.is_connected():
        return _err("Not connected", 400)

    remote = request.args.get("remote", "false").lower() == "true"
    try:
        raw = protocol.get_all_parameters(remote=remote)
        config.load_parameters_from_dict(raw, remote=remote)

        result = []
        for param_id, defn in RadioConfiguration.PARAMETER_DEFINITIONS.items():
            info = raw.get(param_id, {})
            result.append({
                "id":          param_id,
                "name":        defn["name"],
                "value":       info.get("value", defn.get("default", "")),
                "type":        defn.get("type", "string"),
                "options":     defn.get("options"),
                "min_value":   defn.get("min_value"),
                "max_value":   defn.get("max_value"),
                "description": defn.get("description", ""),
            })
        return jsonify(result)
    except Exception as exc:
        logger.exception("get_parameters failed")
        return _err(str(exc), 500)


@app.route("/api/parameters", methods=["POST"])
def write_parameters():
    global config
    if not protocol or not protocol.is_connected():
        return _err("Not connected", 400)

    data = request.get_json(force=True, silent=True) or {}
    remote = bool(data.get("remote", False))
    parameters: dict = data.get("parameters", {})

    try:
        for param_id, value in parameters.items():
            is_valid, msg = config.validate_parameter(param_id, str(value))
            if not is_valid:
                return _err(f"{param_id}: {msg}")
            protocol.set_parameter(param_id, str(value), remote=remote)

        protocol.save_parameters(remote=remote)
        return _ok()
    except Exception as exc:
        logger.exception("write_parameters failed")
        return _err(str(exc), 500)


# ── AT terminal ───────────────────────────────────────────────────────────────
@app.route("/api/command", methods=["POST"])
def send_command():
    if not protocol or not protocol.is_connected():
        return _err("Not connected", 400)

    data = request.get_json(force=True, silent=True) or {}
    command = data.get("command", "").strip()
    if not command:
        return _err("No command provided")

    try:
        protocol._send_command(command)
        response = protocol._read_response()
        return jsonify({"response": response})
    except Exception as exc:
        return _err(str(exc), 500)


# ── radio info ────────────────────────────────────────────────────────────────
@app.route("/api/info")
def get_info():
    if not protocol or not protocol.is_connected():
        return _err("Not connected", 400)
    try:
        return jsonify({
            "info":      protocol.get_radio_info(),
            "board":     protocol.get_board_info(),
            "frequency": protocol.get_frequency_info(),
        })
    except Exception as exc:
        return _err(str(exc), 500)


# ── reboot / factory reset ────────────────────────────────────────────────────
@app.route("/api/reboot", methods=["POST"])
def reboot():
    if not protocol or not protocol.is_connected():
        return _err("Not connected", 400)
    data = request.get_json(force=True, silent=True) or {}
    try:
        protocol.reboot_radio(remote=bool(data.get("remote", False)))
        return _ok()
    except Exception as exc:
        return _err(str(exc), 500)


@app.route("/api/factory_reset", methods=["POST"])
def factory_reset():
    if not protocol or not protocol.is_connected():
        return _err("Not connected", 400)
    data = request.get_json(force=True, silent=True) or {}
    try:
        protocol.factory_reset(remote=bool(data.get("remote", False)))
        return _ok()
    except Exception as exc:
        return _err(str(exc), 500)


# ── radio recovery (stuck / red LED) ─────────────────────────────────────────
@app.route("/api/recover", methods=["POST"])
def recover_radio():
    global protocol
    data = request.get_json(force=True, silent=True) or {}
    port = data.get("port", "").strip()

    if not port:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports:
            return _err("No serial ports found")
        port = ports[0]

    if protocol and protocol.is_connected():
        protocol.disconnect()
        protocol = None

    p = SIKRadioProtocol(port, baudrate=57600)
    try:
        import serial as _serial
        p.ser = _serial.Serial(port, 57600, timeout=1.0, write_timeout=1.0)
    except Exception as exc:
        return _err(f"Cannot open port {port}: {exc}")

    result = p.recover()

    if result["success"] and result.get("working_baud"):
        protocol = p
    else:
        p.disconnect()

    return jsonify(result)


# ── health check ─────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok", "connected": protocol is not None and protocol.is_connected()})


# ── config export / import ────────────────────────────────────────────────────
@app.route("/api/export")
def export_config():
    remote = request.args.get("remote", "false").lower() == "true"
    return jsonify(config.export_config(remote=remote))


@app.route("/api/import", methods=["POST"])
def import_config():
    data = request.get_json(force=True, silent=True) or {}
    remote = bool(data.get("remote", False))
    cfg = data.get("config", {})
    try:
        config.import_config(cfg, remote=remote)
        return _ok()
    except Exception as exc:
        return _err(str(exc), 500)


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port_num = int(os.environ.get("PORT", 5000))

    def _open():
        import time
        time.sleep(1.2)
        webbrowser.open(f"http://localhost:{port_num}")

    threading.Thread(target=_open, daemon=True).start()
    print(f"\n  SIK Radio Configurator  →  http://localhost:{port_num}\n")
    app.run(host="0.0.0.0", port=port_num, debug=False, use_reloader=False)
