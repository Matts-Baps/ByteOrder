"""Load the demo menu into a running menu-service.

    uv run python -m scenarios.seed --menu-url http://localhost:9000 --kitchen default

Skips categories that already exist, so it is safe to run more than once.
Allergens are set on every demo ingredient each time.
Talks to menu-service directly, so only use it against a local or test stack.
"""
import argparse

import httpx

from scenarios.demo_menu import ALLERGENS, KITCHEN_NAME, MENU


def seed(menu_url: str, kitchen_id: str) -> None:
    with httpx.Client(base_url=menu_url, headers={"X-Kitchen-ID": kitchen_id}, timeout=10) as client:
        existing_categories = {c["name"] for c in client.get("/categories/", params={"active_only": False}).json()}
        ingredients = {i["name"]: i["id"] for i in client.get("/ingredients/").json()}

        def ingredient_id(name: str) -> int:
            if name not in ingredients:
                ingredients[name] = client.post("/ingredients/", json={"name": name}).raise_for_status().json()["id"]
            return ingredients[name]

        for order, (category, items) in enumerate(MENU.items()):
            if category in existing_categories:
                print(f"skip {category} (exists)")
                continue
            cat_id = client.post("/categories/", json={"name": category, "sort_order": order}).raise_for_status().json()["id"]
            for item_order, (name, description, toppings, extras) in enumerate(items):
                item_id = client.post(
                    "/items/",
                    json={"category_id": cat_id, "name": name, "description": description, "sort_order": item_order},
                ).raise_for_status().json()["id"]
                for topping in toppings:
                    client.post(f"/items/{item_id}/ingredients",
                                json={"ingredient_id": ingredient_id(topping), "is_default": True}).raise_for_status()
                for extra in extras:
                    client.post(f"/items/{item_id}/ingredients",
                                json={"ingredient_id": ingredient_id(extra), "is_default": False}).raise_for_status()
            print(f"added {category} ({len(items)} items)")

        # Set allergens on every demo ingredient, including ones that already existed.
        for name, allergens in ALLERGENS.items():
            body = {"name": name, "allergens": allergens or [], "allergens_checked": allergens is not None}
            client.put(f"/ingredients/{ingredient_id(name)}", json=body).raise_for_status()

        client.put("/settings/kitchen_name", json={"value": KITCHEN_NAME}).raise_for_status()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--menu-url", default="http://localhost:9000")
    parser.add_argument("--kitchen", default="default")
    args = parser.parse_args()
    seed(args.menu_url, args.kitchen)
