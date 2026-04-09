#!/bin/bash
# setup_pi.sh — Run this ON the Raspberry Pi Zero 2W
# Sets up Python environment, installs dependencies, and registers systemd service

set -e

APP_DIR="$HOME/app"
LOG_DIR="$APP_DIR/logs"
SERVICE_NAME="s7-monitor"

echo "========================================="
echo "  S7-1500 Monitor — Pi Zero 2W Setup"
echo "========================================="

# --- System update ---
echo ""
echo "[1/5] Updating system packages..."
sudo apt update -qq && sudo apt install -y python3 python3-pip python3-venv git

# --- Python virtual environment ---
echo ""
echo "[2/5] Creating Python virtual environment..."
python3 -m venv "$APP_DIR/.venv"
source "$APP_DIR/.venv/bin/activate"

# --- Python dependencies ---
echo ""
echo "[3/5] Installing Python dependencies..."
pip install --upgrade pip -q
pip install flask==3.0.3 python-snap7==1.3 "flask-socketio==5.3.6" -q

echo "      Installed packages:"
pip show flask python-snap7 flask-socketio | grep -E "^(Name|Version)"

# --- Logs directory ---
echo ""
echo "[4/5] Creating logs directory..."
mkdir -p "$LOG_DIR"

# --- Check .env ---
if [ ! -f "$APP_DIR/.env" ]; then
    echo ""
    echo "  WARNING: No .env file found at $APP_DIR/.env"
    echo "  Creating a default one — edit PLC_IP before running the app."
    cat > "$APP_DIR/.env" <<EOF
PLC_IP=192.168.1.100
PLC_RACK=0
PLC_SLOT=1
PLC_DB=1
FLASK_DEBUG=0
LOG_DIR=$LOG_DIR
PORT=5000
EOF
    echo "  Created: $APP_DIR/.env"
fi

# --- Systemd service ---
echo ""
echo "[5/5] Registering systemd service '$SERVICE_NAME'..."

sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=S7-1500 Thermal Process Monitor
After=network.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/python main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}.service

echo ""
echo "========================================="
echo "  Setup complete!"
echo ""
echo "  Commands:"
echo "    Start app :  sudo systemctl start $SERVICE_NAME"
echo "    Stop app  :  sudo systemctl stop $SERVICE_NAME"
echo "    View logs :  journalctl -u $SERVICE_NAME -f"
echo "    Manual run:  source $APP_DIR/.venv/bin/activate && cd $APP_DIR && python main.py"
echo ""
echo "  Edit PLC IP in: $APP_DIR/.env"
echo "  Dashboard at :  http://$(hostname -I | awk '{print $1}'):5000"
echo "========================================="
