"""
Connects to the ByteOrder backend SSE stream and forwards print jobs to the
local ble-print-server running on localhost:8080.
"""
import json
import logging
import time

import requests
from sseclient import SSEClient

log = logging.getLogger(__name__)

BLE_PRINT_URL = "http://localhost:8080/print"
RECONNECT_DELAY = 5  # seconds between SSE reconnect attempts


def _format_order(order: dict) -> str:
    """Convert an order dict to a plain-text receipt string."""
    lines = []
    lines.append("=" * 32)
    # Redis payload uses order_number; fall back to order_id then unknown
    order_ref = order.get("order_number") or str(order.get("order_id", "?"))
    lines.append(f"ORDER #{order_ref}")
    lines.append("=" * 32)

    customer = order.get("customer_name") or order.get("customer_phone") or ""
    if customer:
        lines.append(f"Customer: {customer}")

    items = order.get("items") or []
    for item in items:
        name = item.get("name", "?")
        qty = item.get("quantity", 1)
        notes = item.get("notes") or ""
        lines.append(f"  {qty}x {name}")
        if notes:
            lines.append(f"     * {notes}")

    if order.get("notes"):
        lines.append("")
        lines.append(f"Note: {order['notes']}")

    lines.append("=" * 32)
    lines.append("")
    return "\n".join(lines)


def _send_to_printer(text: str) -> None:
    resp = requests.post(BLE_PRINT_URL, json={"text": text}, timeout=10)
    resp.raise_for_status()
    log.info("Print job sent (%d bytes)", len(text))


def run(api_base: str, mac_address: str) -> None:
    """
    Stream SSE events from the backend and print each new order.
    Reconnects automatically on error or if the stream ends.
    """
    url = f"{api_base}/orders/printers/stream"
    headers = {"Authorization": f"Bearer {mac_address}"}

    log.info("Connecting to print stream: %s", url)

    while True:
        try:
            response = requests.get(url, headers=headers, stream=True, timeout=None)
            if response.status_code == 401:
                log.error("Printer not claimed — waiting for claim before retrying")
                time.sleep(30)
                continue
            response.raise_for_status()

            client = SSEClient(response)
            for event in client.events():
                if not event.data or event.data == ":keepalive":
                    continue
                try:
                    order = json.loads(event.data)
                    text = _format_order(order)
                    _send_to_printer(text)
                except (json.JSONDecodeError, requests.RequestException) as exc:
                    log.error("Print error: %s", exc)

            log.warning("SSE stream ended cleanly, reconnecting in %ds", RECONNECT_DELAY)

        except requests.RequestException as exc:
            log.warning("SSE connection lost (%s), retrying in %ds", exc, RECONNECT_DELAY)

        time.sleep(RECONNECT_DELAY)
