"""Demo menu used by the scenarios. Each item is (name, description, toppings, extras).

ALLERGENS gives each ingredient's allergens (#74). Ingredients set to None are
left unchecked, and the drinks have no ingredients, so the scenarios also cover
"not confirmed".
"""

KITCHEN_NAME = "Garden Kitchen"

MENU = {
    "Burgers": [
        ("Classic Beef Burger", "Smashed beef patty",
         ["Brioche Bun", "Beef Patty", "Cheddar", "Lettuce", "Tomato", "Red Onion", "Pickles"],
         ["Bacon", "Jalapenos"]),
        ("Spiced Bean Burger", "Vegetarian",
         ["Brioche Bun", "Spiced Bean Patty", "Lettuce", "Tomato", "Red Onion", "Vegan Mayo"],
         ["Cheddar", "Jalapenos"]),
        ("Halloumi Burger", "Grilled halloumi with chilli jam",
         ["Brioche Bun", "Grilled Halloumi", "Rocket", "Roasted Pepper", "Chilli Jam"],
         []),
    ],
    "Pizza": [
        ("Margherita", "Wood-fired, 10 inch",
         ["Pizza Dough", "Tomato Sauce", "Mozzarella", "Basil"],
         ["Olives", "Jalapenos", "Pepperoni"]),
        ("Pepperoni Pizza", "Wood-fired, 10 inch",
         ["Pizza Dough", "Tomato Sauce", "Mozzarella", "Pepperoni"],
         ["Jalapenos", "Red Onion"]),
    ],
    "Sides": [
        ("Skin-on Fries", None, ["Sea Salt"], ["Rosemary Salt"]),
        ("Halloumi Fries", None, ["Grilled Halloumi", "Pomegranate", "Yoghurt Dip"], []),
    ],
    "Drinks": [
        ("Homemade Lemonade", None, [], []),
        ("Cola", None, [], []),
        ("Sparkling Water", None, [], []),
    ],
}

ALLERGENS = {
    "Brioche Bun": ["gluten", "eggs", "sesame"],
    "Beef Patty": [],
    "Cheddar": ["milk"],
    "Lettuce": [],
    "Tomato": [],
    "Red Onion": [],
    "Pickles": ["mustard", "sulphites"],
    "Bacon": [],
    "Jalapenos": [],
    "Spiced Bean Patty": ["celery", "mustard"],
    "Vegan Mayo": ["mustard", "soya"],
    "Grilled Halloumi": ["milk"],
    "Rocket": [],
    "Roasted Pepper": [],
    "Chilli Jam": None,
    "Pizza Dough": ["gluten"],
    "Tomato Sauce": [],
    "Mozzarella": ["milk"],
    "Basil": [],
    "Olives": [],
    "Pepperoni": [],
    "Sea Salt": [],
    "Rosemary Salt": [],
    "Pomegranate": [],
    "Yoghurt Dip": ["milk"],
}
