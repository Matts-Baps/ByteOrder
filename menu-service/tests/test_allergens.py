"""Allergen data on ingredients and menu items (#72)."""
from app import models
from app.allergens import ALLERGENS


def _ingredient(db, name, allergens=(), checked=True, active=True):
    ing = models.Ingredient(kitchen_id="test-kitchen", name=name, active=active, allergens_checked=checked)
    ing.allergens = list(allergens)
    db.add(ing)
    db.commit()
    db.refresh(ing)
    return ing


def _item(db, links):
    """links: list of (ingredient, is_default)."""
    cat = models.Category(kitchen_id="test-kitchen", name="Food", sort_order=0, active=True)
    db.add(cat)
    db.commit()
    item = models.MenuItem(kitchen_id="test-kitchen", category_id=cat.id, name="Burger", active=True, sort_order=0)
    db.add(item)
    db.commit()
    for ing, is_default in links:
        db.add(models.MenuItemIngredient(menu_item_id=item.id, ingredient_id=ing.id, is_default=is_default))
    db.commit()
    db.refresh(item)
    return item


# ── The list ──────────────────────────────────────────────────────────────────

def test_the_14_uk_major_allergens():
    assert ALLERGENS == (
        "celery", "gluten", "crustaceans", "eggs", "fish", "lupin", "milk",
        "molluscs", "mustard", "tree_nuts", "peanuts", "sesame", "soya", "sulphites",
    )


def test_the_list_is_served_with_labels(client):
    response = client.get("/allergens/")
    assert response.status_code == 200
    data = response.json()
    assert [a["id"] for a in data] == list(ALLERGENS)
    assert {"id": "gluten", "label": "Cereals containing gluten"} in data
    assert {"id": "tree_nuts", "label": "Tree nuts"} in data


# ── Ingredients ───────────────────────────────────────────────────────────────

def test_new_ingredients_are_unchecked_with_no_allergens(client):
    data = client.post("/ingredients/", json={"name": "Bun"}).json()
    assert data["allergens"] == []
    assert data["allergens_checked"] is False


def test_create_with_allergens(client):
    response = client.post("/ingredients/", json={
        "name": "Bun", "allergens": ["sesame", "gluten"], "allergens_checked": True,
    })
    assert response.status_code == 201
    data = response.json()
    # Always returned in the list's order, whatever order they were sent in.
    assert data["allergens"] == ["gluten", "sesame"]
    assert data["allergens_checked"] is True


def test_duplicates_are_dropped(client):
    data = client.post("/ingredients/", json={"name": "Bun", "allergens": ["gluten", "gluten"]}).json()
    assert data["allergens"] == ["gluten"]


def test_unknown_allergens_are_rejected(client):
    response = client.post("/ingredients/", json={"name": "Bun", "allergens": ["nuts"]})
    assert response.status_code == 422


def test_listing_includes_allergens(client, db):
    _ingredient(db, "Cheese", ["milk"])
    data = client.get("/ingredients/").json()
    assert data[0]["allergens"] == ["milk"]
    assert data[0]["allergens_checked"] is True


def test_update_replaces_allergens(client, db):
    ing = _ingredient(db, "Bun", ["gluten", "sesame"])
    data = client.put(f"/ingredients/{ing.id}", json={"name": "Bun", "allergens": ["gluten"]}).json()
    assert data["allergens"] == ["gluten"]


def test_update_without_allergen_fields_keeps_them(client, db):
    # Older clients only send name and active; that mustn't wipe allergen data.
    ing = _ingredient(db, "Bun", ["gluten"], checked=True)
    data = client.put(f"/ingredients/{ing.id}", json={"name": "Brioche bun", "active": True}).json()
    assert data["allergens"] == ["gluten"]
    assert data["allergens_checked"] is True


def test_update_can_mark_checked(client, db):
    ing = _ingredient(db, "Lettuce", checked=False)
    data = client.put(f"/ingredients/{ing.id}", json={"name": "Lettuce", "allergens_checked": True}).json()
    assert data["allergens_checked"] is True
    assert data["allergens"] == []


def test_delete_removes_allergen_rows(client, db):
    ing = _ingredient(db, "Bun", ["gluten"])
    assert client.delete(f"/ingredients/{ing.id}").status_code == 204
    assert db.query(models.IngredientAllergen).count() == 0


# ── Menu items ────────────────────────────────────────────────────────────────

def test_item_allergens_split_defaults_from_extras(client, db):
    bun = _ingredient(db, "Bun", ["gluten", "sesame"])
    cheese = _ingredient(db, "Cheese", ["milk"])
    mayo = _ingredient(db, "Mayo", ["eggs", "milk"])
    item = _item(db, [(bun, True), (cheese, True), (mayo, False)])

    allergens = client.get(f"/items/{item.id}").json()["allergens"]
    assert allergens["contains"] == ["gluten", "milk", "sesame"]
    # Only what the extras would add on top.
    assert allergens["in_extras"] == ["eggs"]
    assert allergens["confirmed"] is True


def test_item_is_unconfirmed_if_any_ingredient_is_unchecked(client, db):
    bun = _ingredient(db, "Bun", ["gluten"])
    sauce = _ingredient(db, "Secret sauce", checked=False)
    item = _item(db, [(bun, True), (sauce, False)])
    assert client.get(f"/items/{item.id}").json()["allergens"]["confirmed"] is False


def test_item_with_no_ingredients_is_unconfirmed(client, db):
    item = _item(db, [])
    allergens = client.get(f"/items/{item.id}").json()["allergens"]
    assert allergens == {"contains": [], "in_extras": [], "confirmed": False}


def test_inactive_ingredients_are_ignored(client, db):
    bun = _ingredient(db, "Bun", ["gluten"])
    old = _ingredient(db, "Old sauce", ["mustard"], checked=False, active=False)
    item = _item(db, [(bun, True), (old, True)])
    allergens = client.get(f"/items/{item.id}").json()["allergens"]
    assert allergens["contains"] == ["gluten"]
    assert allergens["confirmed"] is True


def test_categories_include_item_and_ingredient_allergens(client, db):
    bun = _ingredient(db, "Bun", ["gluten"])
    _item(db, [(bun, True)])
    item = client.get("/categories/").json()[0]["items"][0]
    assert item["allergens"]["contains"] == ["gluten"]
    assert item["item_ingredients"][0]["ingredient"]["allergens"] == ["gluten"]
