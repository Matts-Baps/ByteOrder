#!/bin/bash -e
# Runs inside the aarch64 chroot on the Pi image rootfs.
# Called via: sudo chroot /mnt/pi /bin/bash /tmp/install-chroot.sh

apt-get install -y --no-install-recommends \
  python3-venv python3-pip python3-psycopg2 libpq5

pip3 install --no-cache-dir uv

uv venv --system-site-packages /opt/byteorder-print/venv

/opt/byteorder-print/venv/bin/uv pip install --no-cache-dir \
  -r /opt/byteorder-print/requirements-pi.txt

systemctl enable byteorder-print.service
