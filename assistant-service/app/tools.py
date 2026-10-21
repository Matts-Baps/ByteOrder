"""Tools the model can call. There is only one: proposing a draft order.

The tool never places an order. It checks the proposal against the menu and,
if valid, hands it back to the customer, who confirms it themselves.
"""
from dataclasses import dataclass

from app.allergens import ALLERGENS, words
from app.menu import Menu

PROPOSE_ORDER = {
    "type": "function",
    "function": {
        "name": "propose_order",
        "description": (
            "Save the customer's complete draft order so they can review it. "
            "Replaces any earlier draft. Does not place the order."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "description": "Every item in the order.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "menu_item_id": {"type": "integer", "description": "The id in brackets on the menu."},
                            "quantity": {"type": "integer", "description": "How many. Defaults to 1."},
                            "remove": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Toppings the item comes with that the customer does not want.",
                            },
                            "add": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional extras the customer wants added.",
                            },
                        },
                        "required": ["menu_item_id"],
                    },
                },
                "avoid_allergens": {
                    "type": "array",
                    "items": {"type": "string", "enum": list(ALLERGENS)},
                    "description": (
                        "Every allergen the customer has said they must avoid. The draft is "
                        "rejected if it contains one, or anything whose allergens are not "
                        "confirmed. A nut allergy means peanuts and tree_nuts; dairy means "
                        "milk; coeliac means gluten."
                    ),
                },
            },
            "required": ["items"],
        },
    },
}

TOOLS = [PROPOSE_ORDER]


@dataclass
class ToolOutcome:
    result: str
    error_type: str | None = None
    draft: list[dict] | None = None
    draft_summary: str | None = None


def execute(name: str, arguments: dict, menu: Menu) -> ToolOutcome:
    if name != "propose_order":
        return ToolOutcome(
            result=f"Unknown tool '{name}'. The only tool is propose_order.",
            error_type="unknown_tool",
        )

    items = arguments.get("items")
    if not isinstance(items, list):
        items = []
    avoid = arguments.get("avoid_allergens") or []
    if not isinstance(avoid, list):
        avoid = [avoid]
    draft, errors = menu.build_order(items)
    unknown = sorted({str(a) for a in avoid} - set(ALLERGENS))
    if unknown:
        errors.append(f"Unknown allergens: {', '.join(unknown)}. Use these ids: {', '.join(ALLERGENS)}.")
    if errors:
        return _not_saved(errors, "invalid_order")

    conflicts = menu.allergen_conflicts(draft, set(avoid))
    if conflicts:
        return _not_saved(conflicts, "allergen_conflict")

    summary = menu.describe_order(draft)
    checked = f" Checked against the customer's allergies: {words(avoid)}." if avoid else ""
    return ToolOutcome(
        result=(
            f"Draft saved: {summary}.{checked} Tell the customer what is in the draft and ask them "
            "to press \"Use this order\" to check it in their basket."
        ),
        draft=draft,
        draft_summary=summary,
    )


def _not_saved(errors: list[str], error_type: str) -> ToolOutcome:
    return ToolOutcome(
        result="The draft was not saved:\n- " + "\n- ".join(errors) + "\nFix these and call propose_order again.",
        error_type=error_type,
    )
