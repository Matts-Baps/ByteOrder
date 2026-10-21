import pytest


def _topping(ing_id, name, default=True):
    return {"ingredient": {"id": ing_id, "name": name, "active": True}, "is_default": default}


CATEGORIES = [
    {
        "id": 1,
        "name": "Burgers",
        "description": None,
        "sort_order": 0,
        "active": True,
        "items": [
            {
                "id": 10,
                "category_id": 1,
                "name": "Classic Burger",
                "description": "Beef patty in a brioche bun",
                "active": True,
                "sort_order": 0,
                "item_ingredients": [
                    _topping(100, "Cheddar"),
                    _topping(101, "Red Onion"),
                    _topping(102, "Bacon", default=False),
                ],
                "option_groups": [],
            },
            {
                "id": 11,
                "category_id": 1,
                "name": "Bean Burger",
                "description": "Spiced bean patty",
                "active": True,
                "sort_order": 1,
                "item_ingredients": [_topping(101, "Red Onion")],
                "option_groups": [],
            },
            {
                "id": 12,
                "category_id": 1,
                "name": "Retired Burger",
                "description": None,
                "active": False,
                "sort_order": 2,
                "item_ingredients": [],
                "option_groups": [],
            },
        ],
    },
    {
        "id": 2,
        "name": "Drinks",
        "description": None,
        "sort_order": 1,
        "active": True,
        "items": [
            {
                "id": 20,
                "category_id": 2,
                "name": "Lemonade",
                "description": None,
                "active": True,
                "sort_order": 0,
                "item_ingredients": [],
                "option_groups": [],
            }
        ],
    },
]


@pytest.fixture
def categories():
    return CATEGORIES
