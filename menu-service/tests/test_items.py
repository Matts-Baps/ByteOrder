from app import models


def _make_category(db, name="Food"):
    cat = models.Category(kitchen_id="test-kitchen", name=name, sort_order=0, active=True)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def _make_ingredient(db, name="Cheese"):
    ing = models.Ingredient(kitchen_id="test-kitchen", name=name, active=True)
    db.add(ing)
    db.commit()
    db.refresh(ing)
    return ing


def _make_item(db, category_id, name="Cheeseburger", active=True):
    item = models.MenuItem(
        kitchen_id="test-kitchen",
        category_id=category_id,
        name=name,
        description="Tasty",
        active=active,
        sort_order=0,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_items_empty(client):
    response = client.get("/items/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_items_with_category_filter(client, db):
    cat1 = _make_category(db, "Cat1")
    cat2 = _make_category(db, "Cat2")
    _make_item(db, cat1.id, "Item A")
    _make_item(db, cat2.id, "Item B")
    response = client.get(f"/items/?category_id={cat1.id}")
    assert response.status_code == 200
    names = [i["name"] for i in response.json()]
    assert "Item A" in names
    assert "Item B" not in names


def test_list_items_active_only(client, db):
    cat = _make_category(db)
    _make_item(db, cat.id, "Active Item", active=True)
    _make_item(db, cat.id, "Inactive Item", active=False)
    response = client.get("/items/")
    names = [i["name"] for i in response.json()]
    assert "Active Item" in names
    assert "Inactive Item" not in names


# ── Get ───────────────────────────────────────────────────────────────────────

def test_get_item_found(client, db):
    cat = _make_category(db)
    item = _make_item(db, cat.id, "Hotdog")
    response = client.get(f"/items/{item.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Hotdog"


def test_get_item_not_found(client):
    response = client.get("/items/99999")
    assert response.status_code == 404


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_item(client, db):
    cat = _make_category(db)
    payload = {"category_id": cat.id, "name": "Pizza", "description": "Cheesy", "active": True, "sort_order": 1}
    response = client.post("/items/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Pizza"
    assert data["category_id"] == cat.id


# ── Update ────────────────────────────────────────────────────────────────────

def test_update_item(client, db):
    cat = _make_category(db)
    item = _make_item(db, cat.id, "Wrap")
    payload = {"category_id": cat.id, "name": "Veggie Wrap", "description": "Fresh", "active": True, "sort_order": 2}
    response = client.put(f"/items/{item.id}", json=payload)
    assert response.status_code == 200
    assert response.json()["name"] == "Veggie Wrap"


def test_update_item_not_found(client, db):
    cat = _make_category(db)
    payload = {"category_id": cat.id, "name": "Ghost", "description": None, "active": True, "sort_order": 0}
    response = client.put("/items/99999", json=payload)
    assert response.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_item(client, db):
    cat = _make_category(db)
    item = _make_item(db, cat.id, "Delete Me")
    response = client.delete(f"/items/{item.id}")
    assert response.status_code == 204
    assert client.get(f"/items/{item.id}").status_code == 404


def test_delete_item_not_found(client):
    response = client.delete("/items/99999")
    assert response.status_code == 404


# ── Ingredients on an item ────────────────────────────────────────────────────

def test_add_and_list_item_ingredients(client, db):
    cat = _make_category(db)
    item = _make_item(db, cat.id, "Salad")
    ing = _make_ingredient(db, "Croutons")

    # Add
    response = client.post(f"/items/{item.id}/ingredients", json={"ingredient_id": ing.id, "is_default": True})
    assert response.status_code == 201
    assert response.json()["ingredient"]["id"] == ing.id

    # List
    response = client.get(f"/items/{item.id}/ingredients")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["ingredient"]["name"] == "Croutons"


def test_remove_item_ingredient(client, db):
    cat = _make_category(db)
    item = _make_item(db, cat.id, "Bowl")
    ing = _make_ingredient(db, "Dressing")
    client.post(f"/items/{item.id}/ingredients", json={"ingredient_id": ing.id, "is_default": True})

    response = client.delete(f"/items/{item.id}/ingredients/{ing.id}")
    assert response.status_code == 204

    response = client.get(f"/items/{item.id}/ingredients")
    assert response.json() == []


# ── Option groups ─────────────────────────────────────────────────────────────

def test_create_and_list_option_groups(client, db):
    cat = _make_category(db)
    item = _make_item(db, cat.id, "Burger")

    payload = {"name": "Size", "required": True, "min_select": 1, "max_select": 1}
    response = client.post(f"/items/{item.id}/option-groups", json=payload)
    assert response.status_code == 201
    group_id = response.json()["id"]

    response = client.get(f"/items/{item.id}/option-groups")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Size"

    return group_id


def test_delete_option_group(client, db):
    cat = _make_category(db)
    item = _make_item(db, cat.id, "Taco")

    r = client.post(f"/items/{item.id}/option-groups", json={"name": "Extras", "required": False, "min_select": 0, "max_select": 3})
    group_id = r.json()["id"]

    response = client.delete(f"/items/{item.id}/option-groups/{group_id}")
    assert response.status_code == 204

    response = client.get(f"/items/{item.id}/option-groups")
    assert response.json() == []


# ── Options within a group ────────────────────────────────────────────────────

def test_add_and_delete_option(client, db):
    cat = _make_category(db)
    item = _make_item(db, cat.id, "Sub")

    r = client.post(f"/items/{item.id}/option-groups", json={"name": "Bread", "required": True, "min_select": 1, "max_select": 1})
    group_id = r.json()["id"]

    # Add option
    r = client.post(f"/items/{item.id}/option-groups/{group_id}/options", json={"name": "White"})
    assert r.status_code == 201
    option_id = r.json()["id"]
    assert r.json()["name"] == "White"

    # Delete option
    r = client.delete(f"/items/{item.id}/option-groups/{group_id}/options/{option_id}")
    assert r.status_code == 204
