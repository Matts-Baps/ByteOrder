#!/bin/bash
# byteorder-firstboot.sh
# Runs once on first boot to pull the ByteOrder print-service container image
# so that subsequent service starts don't need internet access at the point
# Docker begins the container.
#
# This script is called by byteorder-print.service's ExecStartPre directive;
# it can also be invoked manually: sudo /usr/local/sbin/byteorder-firstboot.sh

set -euo pipefail

IMAGE="ghcr.io/matts-baps/byteorder/print-service:latest"

log() { echo "[byteorder-firstboot] $*" | tee -a /var/log/byteorder-firstboot.log; }

log "Pulling ByteOrder print-service container image..."
if docker pull "$IMAGE"; then
    log "Successfully pulled $IMAGE"
else
    log "WARNING: could not pull $IMAGE — service will retry on next start"
fi
