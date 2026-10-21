import re
from typing import Optional
from pydantic import BaseModel, field_validator

from app.allergens import ALLERGENS, in_order

SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$')


# Kitchen / slug
class KitchenOut(BaseModel):
    kitchen_id: str
    slug: str
    model_config = {"from_attributes": True}

class KitchenIn(BaseModel):
    slug: str

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not SLUG_RE.match(v):
            raise ValueError("Slug must be 2-64 characters, lowercase letters, numbers and hyphens only, and cannot start or end with a hyphen")
        return v

class SlugLookupOut(BaseModel):
    kitchen_id: str
    slug: str


# Settings
class SettingOut(BaseModel):
    key: str
    value: Optional[str]
    model_config = {"from_attributes": True}

class SettingIn(BaseModel):
    value: Optional[str]


# Allergens
class AllergenOut(BaseModel):
    id: str
    label: str


class ItemAllergensOut(BaseModel):
    contains: list[str]
    in_extras: list[str]
    confirmed: bool


# Ingredients
class IngredientOut(BaseModel):
    id: int
    name: str
    active: bool
    allergens: list[str] = []
    allergens_checked: bool = False
    model_config = {"from_attributes": True}

class IngredientIn(BaseModel):
    name: str
    active: bool = True
    # None leaves the stored value alone on update, so clients that only send
    # name and active don't wipe allergen data.
    allergens: Optional[list[str]] = None
    allergens_checked: Optional[bool] = None

    @field_validator("allergens")
    @classmethod
    def known_allergens(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        unknown = sorted(set(v) - set(ALLERGENS))
        if unknown:
            raise ValueError(f"Unknown allergens: {', '.join(unknown)}. Use: {', '.join(ALLERGENS)}")
        return in_order(v)


# Menu item ingredients
class MenuItemIngredientOut(BaseModel):
    ingredient: IngredientOut
    is_default: bool
    model_config = {"from_attributes": True}

class MenuItemIngredientIn(BaseModel):
    ingredient_id: int
    is_default: bool = True


# Options
class OptionOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}

class OptionIn(BaseModel):
    name: str


# Option groups
class OptionGroupOut(BaseModel):
    id: int
    name: str
    required: bool
    min_select: int
    max_select: int
    options: list[OptionOut] = []
    model_config = {"from_attributes": True}

class OptionGroupIn(BaseModel):
    name: str
    required: bool = False
    min_select: int = 0
    max_select: int = 1


# Menu items
class MenuItemOut(BaseModel):
    id: int
    category_id: int
    name: str
    description: Optional[str]
    active: bool
    sort_order: int
    item_ingredients: list[MenuItemIngredientOut] = []
    option_groups: list[OptionGroupOut] = []
    allergens: ItemAllergensOut
    model_config = {"from_attributes": True}

class MenuItemIn(BaseModel):
    category_id: int
    name: str
    description: Optional[str] = None
    active: bool = True
    sort_order: int = 0


# Categories
class CategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    sort_order: int
    active: bool
    items: list[MenuItemOut] = []
    model_config = {"from_attributes": True}

class CategoryIn(BaseModel):
    name: str
    description: Optional[str] = None
    sort_order: int = 0
    active: bool = True
