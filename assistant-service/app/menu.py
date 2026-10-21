"""The kitchen's menu as the assistant sees it, and the checker for draft orders.

Toppings follow the customer ordering page: every ingredient linked to an item
can be switched on or off, and `is_default` decides whether it starts on.
Option groups are ignored, as the ordering page does not use them yet.

Allergens (#74): each topping carries the menu service's allergen list and
whether it has been checked. What an item contains depends on which toppings
are included, so allergens are worked out for a selection of toppings.
"""
from dataclasses import dataclass

from app.allergens import ALLERGENS, words

MAX_ORDER_ITEMS = 10


@dataclass(frozen=True)
class Topping:
    id: int
    name: str
    default: bool
    allergens: tuple[str, ...] = ()
    checked: bool = False

    def label(self) -> str:
        if not self.checked:
            return f"{self.name} (allergens not confirmed)"
        return f"{self.name} ({words(self.allergens)})" if self.allergens else self.name


@dataclass(frozen=True)
class Item:
    id: int
    name: str
    description: str | None
    category: str
    toppings: tuple[Topping, ...]

    def topping(self, name: str) -> Topping | None:
        wanted = name.strip().casefold()
        return next((t for t in self.toppings if t.name.casefold() == wanted), None)

    def allergen_note(self) -> str:
        """Allergens in the item as it comes, for the menu summary."""
        served = [t for t in self.toppings if t.default]
        # With nothing listed, nobody has said what is in the item.
        if not served or not all(t.checked for t in served):
            return "allergens: not confirmed"
        found = {a for t in served for a in t.allergens}
        return f"allergens as served: {words(found) or 'none of the 14 major allergens'}"


class Menu:
    def __init__(self, items: list[Item]):
        self._items = {item.id: item for item in items}

    @classmethod
    def from_categories(cls, categories: list[dict]) -> "Menu":
        """Build from the menu-service `GET /categories/` response."""
        items = []
        for cat in categories:
            if not cat.get("active", True):
                continue
            for raw in sorted(cat.get("items", []), key=lambda i: i.get("sort_order", 0)):
                if not raw.get("active", True):
                    continue
                toppings = tuple(
                    Topping(
                        ii["ingredient"]["id"],
                        ii["ingredient"]["name"],
                        ii["is_default"],
                        tuple(a for a in ii["ingredient"].get("allergens", []) if a in ALLERGENS),
                        ii["ingredient"].get("allergens_checked", False) is True,
                    )
                    for ii in raw.get("item_ingredients", [])
                    if ii["ingredient"].get("active", True)
                )
                items.append(
                    Item(raw["id"], raw["name"], raw.get("description"), cat["name"], toppings)
                )
        return cls(items)

    def item(self, item_id: int) -> Item | None:
        return self._items.get(item_id)

    def summary(self) -> str:
        """Compact text menu for the system prompt. Kept short to fit a small context window."""
        lines: list[str] = []
        current = None
        for item in self._items.values():
            if item.category != current:
                if lines:
                    lines.append("")
                lines.append(f"{item.category}:")
                current = item.category
            line = f"- [{item.id}] {item.name}"
            if item.description:
                line += f" - {item.description}"
            defaults = [t.label() for t in item.toppings if t.default]
            extras = [t.label() for t in item.toppings if not t.default]
            if defaults:
                line += f"; comes with: {', '.join(defaults)}"
            if extras:
                line += f"; optional extras: {', '.join(extras)}"
            line += f"; {item.allergen_note()}"
            lines.append(line)
        return "\n".join(lines) if lines else "(The menu is empty.)"

    def build_order(self, requested: list) -> tuple[list[dict], list[str]]:
        """Turn the model's proposed items into basket items.

        Returns (items, errors). Items are only returned when there are no errors,
        in the same shape the ordering page sends to order-service.
        """
        if not requested:
            return [], ["The order has no items."]

        items: list[dict] = []
        errors: list[str] = []
        for entry in requested:
            if not isinstance(entry, dict) or not isinstance(entry.get("menu_item_id"), int):
                errors.append("Each order item must have a numeric menu_item_id.")
                continue
            item_id = entry["menu_item_id"]
            item = self.item(item_id)
            if item is None:
                errors.append(f"There is no menu item with id {item_id}.")
                continue
            quantity = entry.get("quantity", 1)
            if not isinstance(quantity, int) or quantity < 1:
                errors.append(f"Quantity for item {item_id} must be at least 1.")
                continue

            included = {t.id: t.default for t in item.toppings}
            for names, value in ((entry.get("remove") or [], False), (entry.get("add") or [], True)):
                for name in names:
                    topping = item.topping(str(name))
                    if topping is None:
                        errors.append(_unknown_topping(str(name), item))
                    else:
                        included[topping.id] = value

            basket_item = {
                "menu_item_id": item.id,
                "menu_item_name": item.name,
                "ingredients": [
                    {"ingredient_id": t.id, "ingredient_name": t.name, "included": included[t.id]}
                    for t in item.toppings
                ],
                "options": [],
            }
            items.extend(dict(basket_item) for _ in range(quantity))

        if not errors and len(items) > MAX_ORDER_ITEMS:
            errors.append(f"An order can have at most {MAX_ORDER_ITEMS} items.")
        return ([] if errors else items), errors

    def allergen_conflicts(self, items: list[dict], avoid: set[str]) -> list[str]:
        """Why a valid draft can't go to a customer avoiding `avoid`, if it can't.

        Every included topping must be checked and free of those allergens, and
        an item with nothing included has no allergen information at all.
        """
        if not avoid:
            return []
        problems: list[str] = []
        seen: set[tuple] = set()
        for basket_item in items:
            item = self.item(basket_item["menu_item_id"])
            included = {i["ingredient_id"] for i in basket_item["ingredients"] if i["included"]}
            toppings = [t for t in item.toppings if t.id in included]
            if not toppings:
                problem = (f"{item.name} has no allergen information. Leave it out, or tell the "
                           "customer to check with the cook before ordering it.")
                if problem not in seen:
                    seen.add(problem)
                    problems.append(problem)
                continue
            for t in toppings:
                key = (item.id, t.id)
                if key in seen:
                    continue
                seen.add(key)
                hint = "Remove it" if t.default else "Leave it off"
                if not t.checked:
                    problems.append(f"{item.name}: the allergens in {t.name} are not confirmed. "
                                    f"{hint}, or tell the customer to check with the cook.")
                elif avoid & set(t.allergens):
                    problems.append(f"{item.name}: {t.name} contains {words(avoid & set(t.allergens))}. "
                                    f"{hint}, or choose a different item.")
        return problems

    def describe_order(self, items: list[dict]) -> str:
        """One-line, human-readable summary of basket items."""
        parts = []
        for basket_item in items:
            item = self.item(basket_item["menu_item_id"])
            defaults = {t.id: t.default for t in item.toppings} if item else {}
            changes = []
            for ing in basket_item["ingredients"]:
                default = defaults.get(ing["ingredient_id"])
                if default and not ing["included"]:
                    changes.append(f"no {ing['ingredient_name']}")
                elif default is False and ing["included"]:
                    changes.append(f"add {ing['ingredient_name']}")
            text = basket_item["menu_item_name"]
            if changes:
                text += f" ({', '.join(changes)})"
            parts.append(text)
        return "; ".join(parts)


def _unknown_topping(name: str, item: Item) -> str:
    if not item.toppings:
        return f"'{name}' is not a topping on {item.name}. It has no toppings."
    names = ", ".join(t.name for t in item.toppings)
    return f"'{name}' is not a topping on {item.name}. Its toppings are: {names}."
