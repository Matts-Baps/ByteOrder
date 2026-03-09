import json
import os
from unittest.mock import MagicMock, patch

import pytest

# Set DATABASE_URL before importing app.main to avoid needing a real postgres at import time.
# SQLAlchemy create_engine is lazy and won't connect until the engine is used.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_print.db")

from app.main import _is_safe_printer_url, format_order, process_order


# ── _is_safe_printer_url ──────────────────────────────────────────────────────

def test_safe_url_http():
    assert _is_safe_printer_url("http://192.168.1.100/print") is True


def test_safe_url_https():
    assert _is_safe_printer_url("https://printer.local/print") is True


def test_blocked_hostname_localhost():
    assert _is_safe_printer_url("http://localhost/print") is False


def test_blocked_hostname_postgres():
    assert _is_safe_printer_url("http://postgres/print") is False


def test_blocked_hostname_redis():
    assert _is_safe_printer_url("http://redis/print") is False


def test_blocked_hostname_internal_service():
    assert _is_safe_printer_url("http://menu-service/print") is False


def test_blocked_loopback_ip():
    assert _is_safe_printer_url("http://127.0.0.1/print") is False


def test_blocked_link_local_ip():
    assert _is_safe_printer_url("http://169.254.169.254/print") is False


def test_empty_string():
    assert _is_safe_printer_url("") is False


def test_non_http_scheme():
    assert _is_safe_printer_url("ftp://printer.local/print") is False


def test_private_lan_ip_allowed():
    # Private LAN IPs (e.g. 192.168.x.x, 10.x.x.x) should be allowed —
    # the printer lives on the local network.
    assert _is_safe_printer_url("http://192.168.1.50/print") is True
    assert _is_safe_printer_url("http://10.0.0.5/print") is True


# ── format_order ──────────────────────────────────────────────────────────────

def test_format_order_basic():
    order = {
        "order_number": "BO-20260101-001",
        "customer_name": "Alice",
        "items": [
            {"name": "Cheeseburger", "ingredients": [], "options": []},
        ],
    }
    with patch("app.main.get_kitchen_name", return_value="Test Kitchen"):
        result = format_order(order, "test-kitchen")

    assert "text" in result
    text = result["text"]
    assert "Test Kitchen" in text
    assert "BO-20260101-001" in text
    assert "Alice" in text
    assert "Cheeseburger" in text


def test_format_order_with_ingredients():
    order = {
        "order_number": "BO-001",
        "customer_name": "Bob",
        "items": [
            {
                "name": "Salad",
                "ingredients": [
                    {"name": "Lettuce", "included": True},
                    {"name": "Onion", "included": False},
                ],
                "options": [],
            }
        ],
    }
    with patch("app.main.get_kitchen_name", return_value="Kitchen"):
        result = format_order(order, "k1")

    text = result["text"]
    assert "Lettuce" in text
    assert "Onion" in text
    assert "With:" in text
    assert "NO:" in text


def test_format_order_with_options():
    order = {
        "order_number": "BO-002",
        "customer_name": "Carol",
        "items": [
            {
                "name": "Burger",
                "ingredients": [],
                "options": [
                    {"group": "Size", "name": "Large"},
                    {"group": "Size", "name": "Extra Sauce"},
                ],
            }
        ],
    }
    with patch("app.main.get_kitchen_name", return_value="Kitchen"):
        result = format_order(order, "k1")

    text = result["text"]
    assert "Size" in text
    assert "Large" in text
    assert "Extra Sauce" in text


# ── process_order ─────────────────────────────────────────────────────────────

def test_process_order_invalid_json():
    """Bad JSON should return early without raising."""
    process_order(b"not valid json {{{")  # must not raise


def test_process_order_no_kitchen_id():
    """Missing kitchen_id should return early without calling send_to_printer."""
    message = json.dumps({"order_number": "BO-001", "customer_name": "Alice", "items": []})
    with patch("app.main.send_to_printer") as mock_send:
        process_order(message.encode())
        mock_send.assert_not_called()


def test_process_order_no_printer_url():
    """No printer URL configured — should skip printing."""
    message = json.dumps({
        "kitchen_id": "test-kitchen",
        "order_number": "BO-001",
        "customer_name": "Alice",
        "items": [],
    })
    with patch("app.main.get_printer_url", return_value=None) as mock_url, \
         patch("app.main.send_to_printer") as mock_send:
        process_order(message.encode())
        mock_url.assert_called_once_with("test-kitchen")
        mock_send.assert_not_called()


def test_process_order_unsafe_url():
    """Unsafe printer URL — should refuse to connect."""
    message = json.dumps({
        "kitchen_id": "test-kitchen",
        "order_number": "BO-001",
        "customer_name": "Alice",
        "items": [],
    })
    with patch("app.main.get_printer_url", return_value="http://localhost/print"), \
         patch("app.main.send_to_printer") as mock_send:
        process_order(message.encode())
        mock_send.assert_not_called()


def test_process_order_success():
    """Happy path: valid URL calls send_to_printer."""
    message = json.dumps({
        "kitchen_id": "test-kitchen",
        "order_number": "BO-001",
        "customer_name": "Alice",
        "items": [{"name": "Burger", "ingredients": [], "options": []}],
    })
    with patch("app.main.get_printer_url", return_value="http://192.168.1.100/print"), \
         patch("app.main.get_kitchen_name", return_value="Test Kitchen"), \
         patch("app.main.send_to_printer", return_value=True) as mock_send:
        process_order(message.encode())
        mock_send.assert_called_once()
        # Verify payload contains the expected text key
        call_args = mock_send.call_args
        payload = call_args[0][0]
        assert "text" in payload
