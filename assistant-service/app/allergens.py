"""The 14 UK major allergens, as the menu service stores them (#72, #74).

Keep the ids in step with menu-service/app/allergens.py.
"""

ALLERGENS = (
    "celery", "gluten", "crustaceans", "eggs", "fish", "lupin", "milk",
    "molluscs", "mustard", "tree_nuts", "peanuts", "sesame", "soya", "sulphites",
)


def words(allergens) -> str:
    """'tree_nuts' -> 'tree nuts', joined with commas, in the list's order."""
    wanted = set(allergens)
    return ", ".join(a.replace("_", " ") for a in ALLERGENS if a in wanted)
