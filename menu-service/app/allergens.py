"""The 14 major allergens UK food law requires businesses to declare (#72).

https://www.food.gov.uk/business-guidance/allergen-guidance-for-food-businesses

The ids are stored in the database, so don't rename them. Their order here is
the order the API returns them in.
"""

LABELS = {
    "celery": "Celery",
    "gluten": "Cereals containing gluten",
    "crustaceans": "Crustaceans",
    "eggs": "Eggs",
    "fish": "Fish",
    "lupin": "Lupin",
    "milk": "Milk",
    "molluscs": "Molluscs",
    "mustard": "Mustard",
    "tree_nuts": "Tree nuts",
    "peanuts": "Peanuts",
    "sesame": "Sesame",
    "soya": "Soya",
    "sulphites": "Sulphur dioxide and sulphites",
}

ALLERGENS = tuple(LABELS)


def in_order(allergens) -> list[str]:
    """Known allergens from `allergens`, without duplicates, in the list's order."""
    wanted = set(allergens)
    return [a for a in ALLERGENS if a in wanted]
