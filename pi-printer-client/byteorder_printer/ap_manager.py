import subprocess
import logging

log = logging.getLogger(__name__)

AP_CONN_NAME = "byteorder-ap"
AP_IP = "192.168.4.1"


def _find_wifi_interface() -> str:
    """Return the name of the first WiFi interface NM knows about."""
    out = subprocess.run(
        ["nmcli", "-t", "-f", "DEVICE,TYPE", "device", "status"],
        capture_output=True, text=True,
    ).stdout
    for line in out.splitlines():
        device, _, dev_type = line.partition(":")
        if dev_type.strip() == "wifi":
            return device.strip()
    raise RuntimeError("No WiFi interface found")
DNS_CONF = "/etc/NetworkManager/dnsmasq-shared.d/byteorder-captive.conf"


def start_ap(ssid: str) -> None:
    """
    Bring up a NetworkManager WiFi hotspot with the given SSID and install
    a dnsmasq config that redirects all DNS to this host (captive portal).
    """
    # Tear down any existing AP profile
    stop_ap()

    # Log all network devices so we can see what's actually available
    dev_status = subprocess.run(
        ["nmcli", "device", "status"], capture_output=True, text=True
    )
    log.info("Network devices:\n%s", dev_status.stdout)

    iface = _find_wifi_interface()
    log.info("Using WiFi interface: %s", iface)

    # Ensure WiFi radio is unblocked (Pi OS sometimes soft-blocks on first boot)
    subprocess.run(["rfkill", "unblock", "wifi"], capture_output=True)

    # Set regulatory domain — required before the radio can transmit.
    subprocess.run(["iw", "reg", "set", "GB"], capture_output=True)

    # Ensure NM is managing the interface
    subprocess.run(
        ["nmcli", "device", "set", iface, "managed", "yes"],
        capture_output=True,
    )

    # Wait until NM considers the device available (not rfkill-blocked)
    import time
    for attempt in range(30):
        state = subprocess.run(
            ["nmcli", "-t", "-f", "STATE", "device", "show", iface],
            capture_output=True, text=True,
        ).stdout
        log.info("wlan state (attempt %d): %s", attempt + 1, state.strip())
        if "unavailable" not in state:
            break
        time.sleep(1)
    else:
        raise RuntimeError(f"Device {iface} still unavailable after 30s")

    # Create hotspot
    result = subprocess.run(
        [
            "nmcli", "device", "wifi", "hotspot",
            "ifname", iface,
            "con-name", AP_CONN_NAME,
            "ssid", ssid,
            "band", "bg",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to start AP: {result.stderr.strip()}")

    # Install captive-portal DNS redirect so iOS/Android detect the portal
    _install_dns_redirect()

    log.info("AP '%s' started on %s", ssid, AP_INTERFACE)


def stop_ap() -> None:
    """Tear down the hotspot and remove the DNS redirect config."""
    subprocess.run(
        ["nmcli", "connection", "delete", AP_CONN_NAME],
        capture_output=True,
    )
    _remove_dns_redirect()


def _install_dns_redirect() -> None:
    import os
    os.makedirs("/etc/NetworkManager/dnsmasq-shared.d", exist_ok=True)
    with open(DNS_CONF, "w") as f:
        # Redirect every DNS query to this host so clients see the captive portal
        f.write(f"address=/#/{AP_IP}\n")
    # Reload NM so dnsmasq picks up the new config
    subprocess.run(["nmcli", "general", "reload"], capture_output=True)


def _remove_dns_redirect() -> None:
    import os
    try:
        os.remove(DNS_CONF)
        subprocess.run(["nmcli", "general", "reload"], capture_output=True)
    except FileNotFoundError:
        pass
