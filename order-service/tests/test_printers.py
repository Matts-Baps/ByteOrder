# ── Register ──────────────────────────────────────────────────────────────────

def test_register_new_printer(client):
    resp = client.post("/orders/printers/register", json={"mac_address": "aa:bb:cc:dd:ee:ff"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["claim_code"] == "DDEEFF"
    assert data["claimed"] is False
    assert data["kitchen_id"] is None


def test_register_includes_ip_address(client):
    resp = client.post(
        "/orders/printers/register",
        json={"mac_address": "aa:bb:cc:dd:ee:ff", "ip_address": "192.168.1.42"},
    )
    assert resp.status_code == 200


def test_register_idempotent_updates_last_seen(client):
    client.post("/orders/printers/register", json={"mac_address": "aa:bb:cc:dd:ee:ff"})
    resp = client.post("/orders/printers/register", json={"mac_address": "aa:bb:cc:dd:ee:ff"})
    assert resp.status_code == 200


def test_register_updates_ip_address(client):
    client.post(
        "/orders/printers/register",
        json={"mac_address": "aa:bb:cc:dd:ee:ff", "ip_address": "10.0.0.1"},
    )
    resp = client.post(
        "/orders/printers/register",
        json={"mac_address": "aa:bb:cc:dd:ee:ff", "ip_address": "10.0.0.2"},
    )
    assert resp.status_code == 200


def test_register_without_ip_address(client):
    """ip_address is optional — existing Pi firmware with no IP field still works."""
    resp = client.post("/orders/printers/register", json={"mac_address": "11:22:33:44:55:66"})
    assert resp.status_code == 200


# ── Claim + list ──────────────────────────────────────────────────────────────

def test_claim_printer_exposes_ip_address(client):
    client.post(
        "/orders/printers/register",
        json={"mac_address": "aa:bb:cc:dd:ee:ff", "ip_address": "192.168.1.99"},
    )
    client.post("/orders/printers/claim", json={"claim_code": "DDEEFF", "name": "Bar Printer"})
    resp = client.get("/orders/printers/")
    assert resp.status_code == 200
    printers = resp.json()
    assert len(printers) == 1
    assert printers[0]["ip_address"] == "192.168.1.99"


def test_list_printer_ip_address_none_when_not_provided(client):
    client.post("/orders/printers/register", json={"mac_address": "aa:bb:cc:dd:ee:ff"})
    client.post("/orders/printers/claim", json={"claim_code": "DDEEFF", "name": "Bar Printer"})
    resp = client.get("/orders/printers/")
    assert resp.status_code == 200
    assert resp.json()[0]["ip_address"] is None
