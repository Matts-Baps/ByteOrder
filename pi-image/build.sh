#!/bin/bash -e
# Build the ByteOrder Pi image locally.
# Must be run from the repo root: sudo bash pi-image/build.sh
#
# Dependencies (Ubuntu/Debian):
#   sudo apt-get install qemu-user-static binfmt-support xz-utils parted \
#                        e2fsprogs wget bc curl

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK_DIR="${WORK_DIR:-/tmp/byteorder-pi-build}"
IMAGE_SRC="$WORK_DIR/raspios.img"
BLE_DIR="$WORK_DIR/ble-print-server"
MNT="/mnt/pi"

# ── Colour helpers ─────────────────────────────────────────────────────────────
info()  { echo -e "\033[1;34m==> $*\033[0m"; }
ok()    { echo -e "\033[1;32m    OK\033[0m"; }
die()   { echo -e "\033[1;31mERROR: $*\033[0m" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run as root: sudo bash pi-image/build.sh"
cd "$REPO_ROOT"

# ── 0. Dependencies ────────────────────────────────────────────────────────────
info "Checking dependencies…"
MISSING=()
for pkg in qemu-user-static binfmt-support xz-utils parted e2fsprogs wget bc curl; do
  dpkg -s "$pkg" &>/dev/null || MISSING+=("$pkg")
done
if [[ ${#MISSING[@]} -gt 0 ]]; then
  info "Installing missing packages: ${MISSING[*]}"
  apt-get install -y --no-install-recommends "${MISSING[@]}"
fi
ok

mkdir -p "$WORK_DIR"

# ── 1. Download Pi OS ──────────────────────────────────────────────────────────
if [[ ! -f "$IMAGE_SRC" ]]; then
  info "Downloading Raspberry Pi OS Lite (arm64)…"
  wget -q --show-progress \
    https://downloads.raspberrypi.com/raspios_lite_arm64_latest \
    -O "$IMAGE_SRC.xz"
  xz --decompress "$IMAGE_SRC.xz"
else
  info "Using cached image: $IMAGE_SRC"
fi

# ── 2. Expand root partition ───────────────────────────────────────────────────
info "Expanding root partition by 1.5 GB…"
dd if=/dev/zero bs=1M count=1536 >> "$IMAGE_SRC"
parted "$IMAGE_SRC" --script resizepart 2 100%
LOOP=$(losetup --find --show --partscan "$IMAGE_SRC")
e2fsck -f -y "${LOOP}p2"
resize2fs "${LOOP}p2"
losetup --detach "$LOOP"
ok

# ── 3. Mount ───────────────────────────────────────────────────────────────────
info "Mounting image…"
mkdir -p "$MNT"
LOOP=$(losetup --find --show --partscan "$IMAGE_SRC")
mount "${LOOP}p2" "$MNT"
mkdir -p "$MNT/boot/firmware"
mount "${LOOP}p1" "$MNT/boot/firmware"
mount --bind /dev     "$MNT/dev"
mount --bind /dev/pts "$MNT/dev/pts"
mount --bind /proc    "$MNT/proc"
mount --bind /sys     "$MNT/sys"

cleanup() {
  info "Unmounting…"
  umount "$MNT/sys"          || true
  umount "$MNT/proc"         || true
  umount "$MNT/dev/pts"      || true
  umount "$MNT/dev"          || true
  umount "$MNT/boot/firmware" || true
  umount "$MNT"              || true
  losetup --detach "$LOOP"   || true
}
trap cleanup EXIT

# ── 4. Download ble-print-server ───────────────────────────────────────────────
info "Downloading ble-printer-server…"
rm -rf "$BLE_DIR" && mkdir "$BLE_DIR"
curl -fsSL https://github.com/proffalken/ble-printer-server/archive/refs/heads/main.tar.gz \
  | tar -xz -C "$BLE_DIR" --strip-components=1
ok

# ── 5. Inject files ────────────────────────────────────────────────────────────
info "Injecting ByteOrder printer client…"
mkdir -p "$MNT/opt/byteorder-printer"
cp -r pi-printer-client/byteorder_printer "$MNT/opt/byteorder-printer/byteorder_printer"
cp pi-printer-client/requirements.txt     "$MNT/opt/byteorder-printer/requirements.txt"

mkdir -p "$MNT/opt/ble-print-server"
cp -r "$BLE_DIR/." "$MNT/opt/ble-print-server/"

cp pi-printer-client/systemd/byteorder-print-client.service \
   "$MNT/etc/systemd/system/byteorder-print-client.service"
cp pi-printer-client/systemd/byteorder-ble-printer.service \
   "$MNT/etc/systemd/system/byteorder-ble-printer.service"

mkdir -p "$MNT/etc/byteorder-printer"
touch "$MNT/boot/firmware/ssh"
ok

# ── 6. Chroot ──────────────────────────────────────────────────────────────────
info "Running chroot setup (this takes a few minutes)…"
cp pi-image/scripts/install-chroot.sh "$MNT/tmp/install-chroot.sh"
cp /usr/bin/qemu-aarch64-static        "$MNT/usr/bin/"
chroot "$MNT" /bin/bash /tmp/install-chroot.sh
rm "$MNT/tmp/install-chroot.sh" "$MNT/usr/bin/qemu-aarch64-static"
ok

# ── 7. Repack ──────────────────────────────────────────────────────────────────
VERSION="$(git rev-parse --short HEAD)"
DEST="$WORK_DIR/byteorder-pi-${VERSION}.img"

info "Unmounting before repack…"
cleanup
trap - EXIT  # disable trap — cleanup already done

info "Repacking image → $DEST.xz"
cp "$IMAGE_SRC" "$DEST"
xz --compress --threads 0 "$DEST"

echo ""
echo -e "\033[1;32mDone! Image: ${DEST}.xz\033[0m"
echo "Flash with: sudo dd if=${DEST}.xz | xz -d | sudo dd of=/dev/sdX bs=4M status=progress"
