#!/bin/bash
# deploy_to_pi.sh — Run this ON YOUR PC (Git Bash / WSL)
# Transfers the project to the Pi and launches setup

PI_USER="${PI_USER:-eloip}"
PI_HOST="${1:-raspberrypi.local}"   # pass IP as argument if .local doesn't resolve
APP_DIR="$HOME/app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "========================================="
echo "  Deploying to $PI_USER@$PI_HOST"
echo "========================================="

# --- Check Pi is reachable ---
echo ""
echo "[1/4] Checking connection to Pi..."
if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" exit 2>/dev/null; then
    echo "  ERROR: Cannot reach $PI_HOST"
    echo "  Tips:"
    echo "    - Check Pi is powered and on the same network"
    echo "    - Try passing the IP directly: bash deploy_to_pi.sh 192.168.x.x"
    echo "    - Make sure SSH is enabled on the Pi"
    exit 1
fi
echo "  Connected."

# --- Transfer app files ---
echo ""
echo "[2/4] Transferring app files..."
ssh "$PI_USER@$PI_HOST" "mkdir -p ~/app/logs"
scp -r "$PROJECT_DIR/app/." "$PI_USER@$PI_HOST:~/app/"
echo "  App files transferred."

# --- Transfer .env ---
echo ""
echo "[3/4] Transferring .env..."
if [ -f "$PROJECT_DIR/.env" ]; then
    scp "$PROJECT_DIR/.env" "$PI_USER@$PI_HOST:~/app/.env"
    echo "  .env transferred."
else
    echo "  WARNING: No .env found in project root — setup will create a default one."
fi

# --- Run setup on Pi ---
echo ""
echo "[4/4] Running setup on Pi..."
scp "$SCRIPT_DIR/setup_pi.sh" "$PI_USER@$PI_HOST:~/setup_pi.sh"
ssh "$PI_USER@$PI_HOST" "chmod +x ~/setup_pi.sh && ~/setup_pi.sh"

echo ""
echo "========================================="
echo "  Deployment done."
echo "  To start: ssh $PI_USER@$PI_HOST"
echo "            sudo systemctl start s7-monitor"
echo "========================================="
