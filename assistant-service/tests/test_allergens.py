"""The assistant's view of allergen data, and the guard on draft orders (#74)."""
import pytest

from app.allergens import ALLERGENS
from app.menu import Menu
from app import tools


def _ing(ing_id, name, allergens=(), checked=True, default=True):
    return {
        "ingredient": {"id": ing_id, "name": name, "active": True,
                       "allergens": list(allergens), "allergens_checked": checked},
        "is_default": default,
    }


def _item(item_id, name, ingredients):
    return {"id": item_id, "name": name, "description": None, "active": True,
            "sort_order": item_id, "item_ingredients": ingredients}


@pytest.fixture
def menu():
    return Menu.from_categories([{
        "id": 1, "name": "Food", "active": True, "items": [
            _item(10, "Burger", [
                _ing(1, "Bun", ["gluten", "sesame"]),
                _ing(2, "Cheddar", ["milk"]),
                _ing(3, "Lettuce"),
                _ing(4, "Peanut Sauce", ["peanuts"], default=False),
            ]),
            _item(11, "Mystery Wrap", [
                _ing(5, "Wrap", ["gluten"]),
                _ing(6, "Secret Sauce", checked=False, default=False),
            ]),
            _item(12, "Cola", []),
        ],
    }])


def propose(menu, items, avoid=None):
    args = {"items": items}
    if avoid is not None:
        args["avoid_allergens"] = avoid
    return tools.execute("propose_order", args, menu)


def test_same_14_allergens_as_the_menu_service():
    assert ALLERGENS == (
        "celery", "gluten", "crustaceans", "eggs", "fish", "lupin", "milk",
        "molluscs", "mustard", "tree_nuts", "peanuts", "sesame", "soya", "sulphites",
    )


# ── What the model sees ──────────────────────────────────────────────────────

def test_summary_shows_topping_allergens(menu):
    summary = menu.summary()
    assert "Bun (gluten, sesame)" in summary
    assert "Cheddar (milk)" in summary
    assert "Peanut Sauce (peanuts)" in summary
    assert "Secret Sauce (allergens not confirmed)" in summary


def test_summary_shows_item_allergens_as_served(menu):
    lines = {line.split("]")[0]: line for line in menu.summary().splitlines() if line.startswith("- [")}
    assert "allergens as served: gluten, milk, sesame" in lines["- [10"]
    # The wrap as served is confirmed; only the optional sauce is unchecked.
    assert "allergens as served: gluten" in lines["- [11"]
    assert "allergens: not confirmed" in lines["- [12"]


def test_old_menu_data_without_allergens_is_not_confirmed(categories):
    # Data from a menu service without allergen support.
    summary = Menu.from_categories(categories).summary()
    assert "allergens" in summary
    assert "allergens as served" not in summary


# ── The guard ────────────────────────────────────────────────────────────────

def test_avoid_allergens_is_offered_to_the_model():
    props = tools.PROPOSE_ORDER["function"]["parameters"]["properties"]
    assert props["avoid_allergens"]["items"]["enum"] == list(ALLERGENS)


def test_draft_without_avoid_list_is_saved_as_before(menu):
    outcome = propose(menu, [{"menu_item_id": 10, "add": ["Peanut Sauce"]}])
    assert outcome.error_type is None
    assert outcome.draft


def test_draft_free_of_avoided_allergens_is_saved(menu):
    outcome = propose(menu, [{"menu_item_id": 10}], avoid=["peanuts", "tree_nuts"])
    assert outcome.error_type is None
    assert outcome.draft
    assert "peanuts" in outcome.result and "tree nuts" in outcome.result


def test_draft_with_an_avoided_allergen_is_rejected(menu):
    outcome = propose(menu, [{"menu_item_id": 10, "add": ["Peanut Sauce"]}], avoid=["peanuts"])
    assert outcome.error_type == "allergen_conflict"
    assert outcome.draft is None
    assert "Peanut Sauce" in outcome.result and "peanuts" in outcome.result


def test_removing_the_topping_resolves_the_conflict(menu):
    rejected = propose(menu, [{"menu_item_id": 10}], avoid=["milk"])
    assert rejected.error_type == "allergen_conflict"
    assert "Cheddar" in rejected.result
    saved = propose(menu, [{"menu_item_id": 10, "remove": ["Cheddar"]}], avoid=["milk"])
    assert saved.error_type is None


def test_unchecked_ingredient_is_rejected_when_avoiding(menu):
    outcome = propose(menu, [{"menu_item_id": 11, "add": ["Secret Sauce"]}], avoid=["celery"])
    assert outcome.error_type == "allergen_conflict"
    assert "Secret Sauce" in outcome.result and "not confirmed" in outcome.result


def test_item_with_no_ingredients_is_rejected_when_avoiding(menu):
    outcome = propose(menu, [{"menu_item_id": 12}], avoid=["celery"])
    assert outcome.error_type == "allergen_conflict"
    assert "Cola" in outcome.result
    assert "cook" in outcome.result


def test_unknown_allergen_is_rejected(menu):
    outcome = propose(menu, [{"menu_item_id": 10}], avoid=["nuts"])
    assert outcome.error_type == "invalid_order"
    assert "peanuts" in outcome.result and "tree_nuts" in outcome.result


def test_menu_errors_are_reported_before_allergen_checks(menu):
    outcome = propose(menu, [{"menu_item_id": 999}], avoid=["milk"])
    assert outcome.error_type == "invalid_order"


def test_unchecked_items_are_fine_without_allergies(menu):
    outcome = propose(menu, [{"menu_item_id": 11, "add": ["Secret Sauce"]}, {"menu_item_id": 12}])
    assert outcome.error_type is None
    assert outcome.draft


def test_prompt_tells_the_model_to_use_the_data_and_the_guard():
    from app.prompts import SYSTEM_PROMPT
    assert "avoid_allergens" in SYSTEM_PROMPT
    assert "not confirmed" in SYSTEM_PROMPT
    assert "has no allergen information" not in SYSTEM_PROMPT
