import pytest
from app import models


def _make_category(db, name="Burgers", active=True, sort_order=0):
    cat = models.Category(
        kitchen_id="test-kitchen",
        name=name,
        description=f"{name} description",
        sort_order=sort_order,
        active=active,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_categories_empty(client):
    response = client.get("/categories/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_categories_returns_active_by_default(client, db):
    _make_category(db, name="Active Cat", active=True)
    _make_category(db, name="Inactive Cat", active=False)
    response = client.get("/categories/")
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert "Active Cat" in names
    assert "Inactive Cat" not in names


def test_list_categories_active_only_false(client, db):
    _make_category(db, name="Visible", active=True)
    _make_category(db, name="Hidden", active=False)
    response = client.get("/categories/?active_only=false")
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert "Visible" in names
    assert "Hidden" in names


def test_list_categories_sorted(client, db):
    _make_category(db, name="Second", sort_order=2)
    _make_category(db, name="First", sort_order=1)
    response = client.get("/categories/")
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert names.index("First") < names.index("Second")


# ── Get ───────────────────────────────────────────────────────────────────────

def test_get_category_found(client, db):
    cat = _make_category(db, name="Drinks")
    response = client.get(f"/categories/{cat.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Drinks"


def test_get_category_not_found(client):
    response = client.get("/categories/99999")
    assert response.status_code == 404


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_category(client):
    payload = {"name": "Sides", "description": "Side dishes", "sort_order": 3, "active": True}
    response = client.post("/categories/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Sides"
    assert data["sort_order"] == 3
    assert data["active"] is True


def test_create_category_minimal(client):
    response = client.post("/categories/", json={"name": "Desserts"})
    assert response.status_code == 201
    assert response.json()["name"] == "Desserts"


# ── Update ────────────────────────────────────────────────────────────────────

def test_update_category(client, db):
    cat = _make_category(db, name="Old Name")
    payload = {"name": "New Name", "description": "updated", "sort_order": 5, "active": True}
    response = client.put(f"/categories/{cat.id}", json=payload)
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["sort_order"] == 5


def test_update_category_not_found(client):
    payload = {"name": "Ghost", "description": None, "sort_order": 0, "active": True}
    response = client.put("/categories/99999", json=payload)
    assert response.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_category(client, db):
    cat = _make_category(db, name="To Delete")
    response = client.delete(f"/categories/{cat.id}")
    assert response.status_code == 204
    # Verify it's gone
    response = client.get(f"/categories/{cat.id}")
    assert response.status_code == 404


def test_delete_category_not_found(client):
    response = client.delete("/categories/99999")
    assert response.status_code == 404
