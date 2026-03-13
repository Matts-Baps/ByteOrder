#!/bin/bash -e
# Runs inside the aarch64 chroot on the Pi image rootfs.
# Called via: sudo chroot /mnt/pi /bin/bash /tmp/install-chroot.sh

apt-get update -qq
apt-get install -y --no-install-recommends \
  python3-venv python3-pip \
  network-manager \
  bluetooth bluez \
  rfkill

# Create the byteorder user (auto-assigned UID, locked password).
# Any UID >= 1000 user suppresses Pi OS's first-boot username wizard.
useradd --create-home --shell /bin/bash --groups dialout byteorder
passwd -l byteorder

# ble-print-server venv (uses pyproject.toml, not requirements.txt)
python3 -m venv /opt/ble-print-server/venv
/opt/ble-print-server/venv/bin/pip install --no-cache-dir /opt/ble-print-server

# pi-printer-client venv
python3 -m venv /opt/byteorder-printer/venv
/opt/byteorder-printer/venv/bin/pip install --no-cache-dir \
  -r /opt/byteorder-printer/requirements.txt

# Disable first-boot username wizard; enable SSH and printer services
systemctl disable userconfig || true
systemctl enable ssh
systemctl enable byteorder-ble-printer.service
systemctl enable byteorder-print-client.service
