import subprocess
import time
import logging

log = logging.getLogger(__name__)

CONNECT_TIMEOUT = 30  # seconds to wait for association


def connect(ssid: str, psk: str) -> bool:
    """
    Connect wlan0 to the given SSID using NetworkManager (nmcli).
    Returns True on success, False if the connection fails or times out.
    """
    conn_name = f"byteorder-{ssid}"

    # Delete any stale connection profile with this name
    subprocess.run(
        ["nmcli", "connection", "delete", conn_name],
        capture_output=True,
    )

    from .ap_manager import _find_wifi_interface
    try:
        iface = _find_wifi_interface()
    except RuntimeError:
        iface = "wlan0"

    # Add and activate the connection
    result = subprocess.run(
        [
            "nmcli", "device", "wifi", "connect", ssid,
            "password", psk,
            "name", conn_name,
            "ifname", iface,
        ],
        capture_output=True,
        text=True,
        timeout=CONNECT_TIMEOUT + 5,
    )

    if result.returncode != 0:
        log.error("nmcli connect failed: %s", result.stderr.strip())
        return False

    # Wait for actual IP
    for _ in range(CONNECT_TIMEOUT):
        time.sleep(1)
        out = subprocess.run(
            ["nmcli", "-t", "-f", "GENERAL.STATE", "device", "show", iface],
            capture_output=True, text=True,
        ).stdout
        if "100 (connected)" in out:
            return True

    log.error("Timed out waiting for WiFi connection")
    return False


def current_ssid() -> str | None:
    """Return the SSID wlan0 is currently connected to, or None."""
    out = subprocess.run(
        ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
        capture_output=True, text=True,
    ).stdout
    for line in out.splitlines():
        if line.startswith("yes:"):
            return line.split(":", 1)[1] or None
    return None
