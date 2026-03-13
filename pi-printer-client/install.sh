#!/usr/bin/env bash
# ByteOrder Printer Client — installer for Raspberry Pi OS Bookworm (Lite)
# Run as root: sudo bash install.sh
set -euo pipefail

INSTALL_DIR=/opt/byteorder-printer
BLE_DIR=/opt/ble-print-server
SYSTEMD_DIR=/etc/systemd/system

echo "==> ByteOrder Printer Client installer"

# ── Dependencies ──────────────────────────────────────────────────────────────
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    network-manager \
    bluetooth bluez \
    git

# ── ble-print-server ──────────────────────────────────────────────────────────
if [[ ! -d "$BLE_DIR" ]]; then
    echo "==> Cloning ble-print-server…"
    git clone https://github.com/proffalken/ble-printer-server.git "$BLE_DIR"
fi

python3 -m venv "$BLE_DIR/venv"
"$BLE_DIR/venv/bin/pip" install -q -r "$BLE_DIR/requirements.txt"

# ── ByteOrder print client ─────────────────────────────────────────────────────
mkdir -p "$INSTALL_DIR"
cp -r byteorder_printer "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"

python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"

# ── Config directory ───────────────────────────────────────────────────────────
mkdir -p /etc/byteorder-printer

# ── Systemd units ──────────────────────────────────────────────────────────────
cp systemd/byteorder-ble-printer.service   "$SYSTEMD_DIR/"
cp systemd/byteorder-print-client.service  "$SYSTEMD_DIR/"

systemctl daemon-reload
systemctl enable byteorder-ble-printer
systemctl enable byteorder-print-client
systemctl start  byteorder-ble-printer
systemctl start  byteorder-print-client

echo ""
echo "==> Installation complete!"
echo "    Check status with: journalctl -u byteorder-print-client -f"
echo ""
echo "    First run: the Pi will broadcast a 'ByteOrder-XXXXXX' WiFi network."
echo "    Connect your phone to it and follow the setup steps."
