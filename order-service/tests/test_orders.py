import pytest


MINIMAL_ORDER = {
    "customer_name": "Alice",
    "items": [
        {
            "menu_item_id": 1,
            "menu_item_name": "Cheeseburger",
            "ingredients": [],
            "options": [],
        }
    ],
}

ORDER_WITH_EXTRAS = {
    "customer_name": "Bob",
    "items": [
        {
            "menu_item_id": 2,
            "menu_item_name": "Veggie Wrap",
            "ingredients": [
                {"ingredient_id": 10, "ingredient_name": "Lettuce", "included": True},
                {"ingredient_id": 11, "ingredient_name": "Onion", "included": False},
            ],
            "options": [
                {"option_id": 5, "option_name": "Large", "group_name": "Size"},
            ],
        }
    ],
}


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_order_minimal(client):
    response = client.post("/orders/", json=MINIMAL_ORDER)
    assert response.status_code == 201
    data = response.json()
    assert data["customer_name"] == "Alice"
    assert data["status"] == "pending"
    assert "public_id" in data
    assert "order_number" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["menu_item_name"] == "Cheeseburger"


def test_create_order_with_ingredients_and_options(client):
    response = client.post("/orders/", json=ORDER_WITH_EXTRAS)
    assert response.status_code == 201
    data = response.json()
    assert data["customer_name"] == "Bob"
    item = data["items"][0]
    assert len(item["ingredients"]) == 2
    assert len(item["options"]) == 1
    excluded = [i for i in item["ingredients"] if not i["included"]]
    assert excluded[0]["ingredient_name"] == "Onion"


def test_create_order_publishes_to_redis(client, mock_redis):
    client.post("/orders/", json=MINIMAL_ORDER)
    assert mock_redis.publish.called


# ── Get by ID ─────────────────────────────────────────────────────────────────

def test_get_order_by_id(client):
    create_resp = client.post("/orders/", json=MINIMAL_ORDER)
    order_id = create_resp.json()["id"]

    response = client.get(f"/orders/{order_id}")
    assert response.status_code == 200
    assert response.json()["id"] == order_id


def test_get_order_by_id_not_found(client):
    response = client.get("/orders/99999")
    assert response.status_code == 404


# ── Get by public_id (track) ──────────────────────────────────────────────────

def test_get_order_by_public_id(client):
    create_resp = client.post("/orders/", json=MINIMAL_ORDER)
    public_id = create_resp.json()["public_id"]

    response = client.get(f"/orders/track/{public_id}")
    assert response.status_code == 200
    assert response.json()["public_id"] == public_id


def test_get_order_by_public_id_not_found(client):
    response = client.get("/orders/track/nonexistent-uuid-here")
    assert response.status_code == 404


# ── Queue ─────────────────────────────────────────────────────────────────────

def test_get_queue_empty(client):
    response = client.get("/orders/queue")
    assert response.status_code == 200
    assert response.json() == []


def test_get_queue_contains_pending_orders(client):
    client.post("/orders/", json=MINIMAL_ORDER)
    response = client.get("/orders/queue")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    statuses = [o["status"] for o in response.json()]
    for s in statuses:
        assert s in ("pending", "in_progress", "ready")


# ── Update status ─────────────────────────────────────────────────────────────

def test_update_status_valid(client):
    create_resp = client.post("/orders/", json=MINIMAL_ORDER)
    order_id = create_resp.json()["id"]

    for status in ("in_progress", "ready", "completed"):
        response = client.put(f"/orders/{order_id}/status", json={"status": status})
        assert response.status_code == 200, f"Failed for status={status}"
        assert response.json()["status"] == status


def test_update_status_invalid(client):
    create_resp = client.post("/orders/", json=MINIMAL_ORDER)
    order_id = create_resp.json()["id"]

    response = client.put(f"/orders/{order_id}/status", json={"status": "flying"})
    assert response.status_code == 400


def test_update_status_not_found(client):
    response = client.put("/orders/99999/status", json={"status": "ready"})
    assert response.status_code == 404


# ── History ───────────────────────────────────────────────────────────────────

def test_get_history_returns_completed_orders(client):
    create_resp = client.post("/orders/", json=MINIMAL_ORDER)
    order_id = create_resp.json()["id"]
    client.put(f"/orders/{order_id}/status", json={"status": "completed"})

    response = client.get("/orders/history")
    assert response.status_code == 200
    ids = [o["id"] for o in response.json()]
    assert order_id in ids


def test_get_history_empty_by_default(client):
    # No completed orders in a fresh transaction
    response = client.get("/orders/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
