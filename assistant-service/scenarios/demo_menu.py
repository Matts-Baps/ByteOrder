"""Demo menu used by the scenarios. Each item is (name, description, toppings, extras)."""

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
         ["Tomato Sauce", "Mozzarella", "Basil"],
         ["Olives", "Jalapenos", "Pepperoni"]),
        ("Pepperoni Pizza", "Wood-fired, 10 inch",
         ["Tomato Sauce", "Mozzarella", "Pepperoni"],
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
