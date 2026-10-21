from app.menu import Menu


def test_inactive_items_are_left_out(categories):
    menu = Menu.from_categories(categories)
    assert menu.item(12) is None
    assert "Retired Burger" not in menu.summary()


def test_summary_lists_ids_toppings_and_extras(categories):
    summary = Menu.from_categories(categories).summary()
    assert "Burgers:" in summary
    assert "[10] Classic Burger - Beef patty in a brioche bun" in summary
    assert "comes with: Cheddar, Red Onion" in summary
    assert "optional extras: Bacon" in summary
    assert "[20] Lemonade" in summary


def test_build_default_item(categories):
    menu = Menu.from_categories(categories)
    items, errors = menu.build_order([{"menu_item_id": 10}])
    assert errors == []
    assert items == [
        {
            "menu_item_id": 10,
            "menu_item_name": "Classic Burger",
            "ingredients": [
                {"ingredient_id": 100, "ingredient_name": "Cheddar", "included": True},
                {"ingredient_id": 101, "ingredient_name": "Red Onion", "included": True},
                {"ingredient_id": 102, "ingredient_name": "Bacon", "included": False},
            ],
            "options": [],
        }
    ]


def test_remove_and_add_toppings_case_insensitively(categories):
    menu = Menu.from_categories(categories)
    items, errors = menu.build_order(
        [{"menu_item_id": 10, "remove": ["red onion"], "add": ["BACON"]}]
    )
    assert errors == []
    included = {i["ingredient_name"]: i["included"] for i in items[0]["ingredients"]}
    assert included == {"Cheddar": True, "Red Onion": False, "Bacon": True}


def test_quantity_repeats_the_item(categories):
    menu = Menu.from_categories(categories)
    items, errors = menu.build_order([{"menu_item_id": 20, "quantity": 3}])
    assert errors == []
    assert [i["menu_item_name"] for i in items] == ["Lemonade"] * 3


def test_unknown_item_is_an_error(categories):
    items, errors = Menu.from_categories(categories).build_order([{"menu_item_id": 999}])
    assert items == []
    assert errors == ["There is no menu item with id 999."]


def test_inactive_item_is_an_error(categories):
    _, errors = Menu.from_categories(categories).build_order([{"menu_item_id": 12}])
    assert errors == ["There is no menu item with id 12."]


def test_unknown_topping_lists_valid_ones(categories):
    _, errors = Menu.from_categories(categories).build_order(
        [{"menu_item_id": 11, "add": ["Pineapple"]}]
    )
    assert errors == ["'Pineapple' is not a topping on Bean Burger. Its toppings are: Red Onion."]


def test_topping_on_item_without_toppings(categories):
    _, errors = Menu.from_categories(categories).build_order(
        [{"menu_item_id": 20, "remove": ["Ice"]}]
    )
    assert errors == ["'Ice' is not a topping on Lemonade. It has no toppings."]


def test_empty_order_is_an_error(categories):
    _, errors = Menu.from_categories(categories).build_order([])
    assert errors == ["The order has no items."]


def test_too_many_items_is_an_error(categories):
    _, errors = Menu.from_categories(categories).build_order(
        [{"menu_item_id": 20, "quantity": 11}]
    )
    assert errors == ["An order can have at most 10 items."]


def test_bad_quantity_is_an_error(categories):
    _, errors = Menu.from_categories(categories).build_order(
        [{"menu_item_id": 20, "quantity": 0}]
    )
    assert errors == ["Quantity for item 20 must be at least 1."]


def test_malformed_entry_is_an_error(categories):
    _, errors = Menu.from_categories(categories).build_order(["Lemonade"])
    assert errors == ["Each order item must have a numeric menu_item_id."]


def test_describe_order(categories):
    menu = Menu.from_categories(categories)
    items, _ = menu.build_order(
        [{"menu_item_id": 10, "remove": ["Red Onion"], "add": ["Bacon"]}, {"menu_item_id": 20}]
    )
    assert menu.describe_order(items) == "Classic Burger (no Red Onion, add Bacon); Lemonade"
