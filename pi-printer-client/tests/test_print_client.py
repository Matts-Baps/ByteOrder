from unittest.mock import MagicMock, patch
import requests
from byteorder_printer.print_client import _format_order, run


# ── _format_order ─────────────────────────────────────────────────────────────

def test_format_order_uses_order_number():
    order = {"order_number": "0042", "customer_name": "Alice", "items": []}
    receipt = _format_order(order)
    assert "ORDER #0042" in receipt


def test_format_order_falls_back_to_order_id():
    order = {"order_id": 7, "customer_name": "Bob", "items": []}
    receipt = _format_order(order)
    assert "ORDER #7" in receipt


def test_format_order_includes_customer_and_items():
    order = {
        "order_number": "0001",
        "customer_name": "Carol",
        "items": [{"name": "Burger", "quantity": 1}],
    }
    receipt = _format_order(order)
    assert "Customer: Carol" in receipt
    assert "1x Burger" in receipt


# ── run — reconnect behaviour ─────────────────────────────────────────────────

def _mock_sse_response(events_data):
    """Build a fake requests.Response + SSEClient that yields given event data strings."""
    mock_events = []
    for data in events_data:
        e = MagicMock()
        e.data = data
        mock_events.append(e)

    mock_sse = MagicMock()
    mock_sse.events.return_value = iter(mock_events)
    return mock_sse


def test_run_sleeps_after_clean_stream_end():
    """If the SSE stream ends without an exception, still sleep before reconnecting."""
    # First iteration: stream ends cleanly. Second: raise to exit the loop.
    call_count = 0

    def fake_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise KeyboardInterrupt  # break out of while True
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        return resp

    with patch("byteorder_printer.print_client.requests.get", side_effect=fake_get), \
         patch("byteorder_printer.print_client.SSEClient") as mock_sse_cls, \
         patch("byteorder_printer.print_client.time") as mock_time:

        mock_sse_cls.return_value.events.return_value = iter([])  # empty stream

        try:
            run("http://test", "AA:BB:CC:DD:EE:FF")
        except KeyboardInterrupt:
            # Expected: used to break out of run()'s infinite loop during testing.
            pass

    # sleep must have been called after the clean stream end
    mock_time.sleep.assert_called()
    assert mock_time.sleep.call_args[0][0] == 5


def test_run_sleeps_after_connection_error():
    """Connection errors also trigger the reconnect sleep."""
    call_count = 0

    def fake_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise KeyboardInterrupt
        raise requests.RequestException("connection refused")

    with patch("byteorder_printer.print_client.requests.get", side_effect=fake_get), \
         patch("byteorder_printer.print_client.time") as mock_time:

        try:
            run("http://test", "AA:BB:CC:DD:EE:FF")
        except KeyboardInterrupt:
            # Expected: used to break out of run()'s infinite loop during testing.
            pass

    mock_time.sleep.assert_called()
