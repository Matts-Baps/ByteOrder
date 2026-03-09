from app import models


def _make_ingredient(db, name="Tomato", active=True):
    ing = models.Ingredient(kitchen_id="test-kitchen", name=name, active=active)
    db.add(ing)
    db.commit()
    db.refresh(ing)
    return ing


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_ingredients_empty(client):
    response = client.get("/ingredients/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_ingredients_returns_all_by_default(client, db):
    _make_ingredient(db, name="Lettuce", active=True)
    _make_ingredient(db, name="Onion", active=False)
    response = client.get("/ingredients/")
    assert response.status_code == 200
    names = [i["name"] for i in response.json()]
    assert "Lettuce" in names
    assert "Onion" in names


def test_list_ingredients_active_only(client, db):
    _make_ingredient(db, name="Cheese", active=True)
    _make_ingredient(db, name="Pickle", active=False)
    response = client.get("/ingredients/?active_only=true")
    assert response.status_code == 200
    names = [i["name"] for i in response.json()]
    assert "Cheese" in names
    assert "Pickle" not in names


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_ingredient(client):
    response = client.post("/ingredients/", json={"name": "Ketchup", "active": True})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Ketchup"
    assert data["active"] is True


def test_create_ingredient_defaults_active(client):
    response = client.post("/ingredients/", json={"name": "Mustard"})
    assert response.status_code == 201
    assert response.json()["active"] is True


# ── Update ────────────────────────────────────────────────────────────────────

def test_update_ingredient(client, db):
    ing = _make_ingredient(db, name="Mayo")
    response = client.put(f"/ingredients/{ing.id}", json={"name": "Light Mayo", "active": False})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Light Mayo"
    assert data["active"] is False


def test_update_ingredient_not_found(client):
    response = client.put("/ingredients/99999", json={"name": "Ghost", "active": True})
    assert response.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_ingredient(client, db):
    ing = _make_ingredient(db, name="Jalapeño")
    response = client.delete(f"/ingredients/{ing.id}")
    assert response.status_code == 204


def test_delete_ingredient_not_found(client):
    response = client.delete("/ingredients/99999")
    assert response.status_code == 404
