"""
ByteOrder Printer Client — entrypoint.

Boot logic:
  1. Load config from /etc/byteorder-printer/config.json
  2. Determine MAC address of wlan0
  3. If no WiFi credentials are saved  → enter AP/setup mode
  4. Connect to WiFi; if that fails     → fall back to AP/setup mode
  5. Register with backend (idempotent) → start SSE print loop
"""
import logging
import sys
import threading
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


def _wait_for_ntp(timeout: int = 60) -> None:
    """Wait for systemd-timesyncd to sync the clock before making TLS connections.

    Pi has no RTC — clock starts wrong on first boot. TLS cert validation
    fails with 'not yet valid' until NTP corrects the time.
    """
    import subprocess
    log.info("Waiting for NTP time sync…")
    for elapsed in range(timeout):
        out = subprocess.run(
            ["timedatectl", "show", "--property=NTPSynchronized", "--value"],
            capture_output=True, text=True,
        ).stdout.strip()
        if out == "yes":
            log.info("NTP sync confirmed after %ds", elapsed)
            return
        time.sleep(1)
    log.warning("NTP sync timed out after %ds — TLS connections may fail", timeout)


def _register(api_base: str, mac: str) -> bool:
    """POST /orders/printers/register — idempotent. Returns True on success."""
    import requests
    from .mac_utils import derive_claim_code

    try:
        resp = requests.post(
            f"{api_base}/orders/printers/register",
            json={"mac_address": mac, "claim_code": derive_claim_code(mac)},
            timeout=10,
        )
        resp.raise_for_status()
        log.info("Registered with backend (claim code: %s)", derive_claim_code(mac))
        return True
    except requests.RequestException as exc:
        log.error("Registration failed: %s", exc)
        return False


def _enter_ap_mode(cfg, mac: str) -> None:
    """Start AP, serve setup portal, handle submission."""
    from . import ap_manager, setup_server, wifi_manager, config as cfg_mod
    from .mac_utils import derive_claim_code

    ap_ssid = f"ByteOrder-{mac.replace(':', '')[-6:]}"
    log.info("Entering AP setup mode — SSID: %s", ap_ssid)

    try:
        ap_manager.start_ap(ap_ssid)
    except RuntimeError as exc:
        log.error("Could not start AP: %s", exc)
        sys.exit(1)

    submitted = threading.Event()
    saved_params = {}

    def on_submit(ssid: str, psk: str, api_base: str) -> None:
        """Called (in a background thread) when the user submits the setup form."""
        log.info("Setup form submitted — SSID: %s, API: %s", ssid, api_base)

        # Save immediately so config survives a crash during connect
        cfg.wifi_ssid = ssid
        cfg.wifi_psk = psk
        cfg.api_base = api_base
        cfg_mod.save(cfg)

        # Give the browser time to receive the "Connecting…" page before the AP drops
        time.sleep(2)
        ap_manager.stop_ap()

        if wifi_manager.connect(ssid, psk):
            log.info("WiFi connected, registering…")
            _wait_for_ntp()
            _register(api_base, mac)
            saved_params["ok"] = True
        else:
            log.error("WiFi connect failed — reverting to AP mode")
            saved_params["ok"] = False

        submitted.set()

    # Run the Flask server in this thread; on_submit fires in a background thread
    server_thread = threading.Thread(
        target=setup_server.run,
        kwargs={
            "claim_code": derive_claim_code(mac),
            "api_base": cfg.api_base,
            "on_submit": on_submit,
        },
        daemon=True,
    )
    server_thread.start()

    submitted.wait()  # Block until the user completes setup

    if not saved_params.get("ok"):
        log.info("Retrying AP mode after failed WiFi connect…")
        _enter_ap_mode(cfg, mac)  # recurse — try again
    else:
        _start_print_loop(cfg, mac)


def _start_print_loop(cfg, mac: str) -> None:
    from . import print_client

    log.info("Starting print loop (API: %s)", cfg.api_base)
    while True:
        try:
            print_client.run(cfg.api_base, mac)
        except Exception as exc:
            log.error("Print loop crashed: %s — restarting in 10s", exc)
            time.sleep(10)


def main() -> None:
    from . import config as cfg_mod, wifi_manager
    from .mac_utils import get_mac

    cfg = cfg_mod.load()

    try:
        mac = get_mac("wlan0")
    except RuntimeError as exc:
        log.error("Cannot get MAC address: %s", exc)
        sys.exit(1)

    cfg.mac_address = mac
    cfg_mod.save(cfg)

    log.info("ByteOrder Printer Client starting — MAC: %s", mac)

    # No WiFi credentials yet → go straight to setup
    if not cfg.wifi_ssid:
        _enter_ap_mode(cfg, mac)
        return

    # Try to connect with saved credentials
    log.info("Connecting to WiFi: %s", cfg.wifi_ssid)
    if wifi_manager.connect(cfg.wifi_ssid, cfg.wifi_psk or ""):
        _wait_for_ntp()
        if _register(cfg.api_base, mac):
            _start_print_loop(cfg, mac)
            return
        else:
            log.warning("Backend unreachable — check API base URL via setup portal")
    else:
        log.warning("WiFi connect failed with saved credentials — entering AP mode")

    _enter_ap_mode(cfg, mac)


if __name__ == "__main__":
    main()
