#!/bin/bash
# deploy_fast.sh — Push app changes to Pi and restart service
# Usage: bash scripts/deploy_fast.sh [pi-ip]

PI_USER="${PI_USER:-loi}"
PI_HOST="${1:-192.168.1.227}"
APP_DIR="/home/$PI_USER/app"

echo "Deploying to $PI_USER@$PI_HOST..."

scp app/main.py \
    app/thermal_model.py \
    app/plc_connector.py \
    app/logger.py \
    "$PI_USER@$PI_HOST:$APP_DIR/"

scp app/templates/index.html \
    app/templates/test.html \
    "$PI_USER@$PI_HOST:$APP_DIR/templates/"

ssh "$PI_USER@$PI_HOST" "sudo systemctl restart s7-monitor && sleep 1 && sudo systemctl is-active s7-monitor"
