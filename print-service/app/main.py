import ipaddress
import json
import logging
import os
import time
from urllib.parse import urlparse

import requests
import redis
from sqlalchemy import create_engine, text
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("print-service")

# OpenTelemetry setup
_otel_exporter_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
if _otel_exporter_endpoint or settings.otel_endpoint:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource

    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    if _otel_exporter_endpoint:
        exporter = OTLPSpanExporter()
    else:
        exporter = OTLPSpanExporter(endpoint=f"{settings.otel_endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(__name__)
else:
    tracer = None

engine = create_engine(settings.database_url)

_BLOCKED_PRINTER_HOSTS = {
    "localhost", "postgres", "redis", "menu-service", "order-service",
    "admin", "print-service", "metadata.google.internal",
}


def _is_safe_printer_url(url: str) -> bool:
    """Return True only if url is a safe http/https URL not pointing to internal resources."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = (parsed.hostname or "").lower()
        if not host or host in _BLOCKED_PRINTER_HOSTS:
            return False
        try:
            addr = ipaddress.ip_address(host)
            # Allow private LAN IPs — printer lives on the local network.
            # Block loopback and link-local (169.254.x — cloud metadata endpoints) only.
            if addr.is_loopback or addr.is_link_local:
                return False
        except ValueError:
            pass
        return True
    except Exception:
        return False


def get_printer_url() -> str | None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT value FROM settings WHERE key = 'printer_url'")).fetchone()
    return row[0] if row and row[0] else None


def get_kitchen_name() -> str:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT value FROM settings WHERE key = 'kitchen_name'")).fetchone()
    return row[0] if row and row[0] else "ByteOrder Kitchen"


def format_order(order: dict) -> dict:
    kitchen = get_kitchen_name()
    lines = [
        f"{kitchen}",
        f"Order: {order['order_number']}",
        f"Name:  {order['customer_name']}",
        "",
    ]

    for item in order["items"]:
        lines.append(f">> {item['name']}")

        included = [i["name"] for i in item.get("ingredients", []) if i["included"]]
        excluded = [i["name"] for i in item.get("ingredients", []) if not i["included"]]

        if included:
            lines.append(f"   With: {', '.join(included)}")
        if excluded:
            lines.append(f"   NO:   {', '.join(excluded)}")

        options_by_group: dict[str, list[str]] = {}
        for opt in item.get("options", []):
            options_by_group.setdefault(opt["group"], []).append(opt["name"])
        for group, opts in options_by_group.items():
            lines.append(f"   {group}: {', '.join(opts)}")

        lines.append("")

    return {"text": "\n".join(lines)}


def send_to_printer(payload: dict, printer_url: str) -> bool:
    try:
        resp = requests.post(f"{printer_url.rstrip('/')}/print", json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        log.error("Failed to send to printer: %s", e)
        return False


def process_order(message_data: bytes):
    try:
        order = json.loads(message_data)
    except json.JSONDecodeError:
        log.error("Invalid JSON in order message")
        return

    log.info("Processing order %s for %s", order.get("order_number"), order.get("customer_name"))

    printer_url = get_printer_url()
    if not printer_url:
        log.warning("No printer URL configured — order %s not printed", order.get("order_number"))
        return
    if not _is_safe_printer_url(printer_url):
        log.error("Printer URL is not a safe external URL — refusing to connect for order %s", order.get("order_number"))
        return

    payload = format_order(order)

    if tracer:
        with tracer.start_as_current_span("print_order") as span:
            span.set_attribute("order.number", order.get("order_number", ""))
            span.set_attribute("order.customer", order.get("customer_name", ""))
            success = send_to_printer(payload, printer_url)
            span.set_attribute("print.success", success)
    else:
        send_to_printer(payload, printer_url)


def main():
    log.info("Print service starting, connecting to Redis at %s", settings.redis_url)

    r = redis.from_url(settings.redis_url, decode_responses=False)
    pubsub = r.pubsub()
    pubsub.subscribe("new_orders")

    log.info("Subscribed to new_orders channel, waiting for orders...")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue
        process_order(message["data"])


if __name__ == "__main__":
    # Brief delay to allow Redis to be ready on cold start
    time.sleep(2)
    main()
