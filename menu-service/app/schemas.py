import re
from typing import Optional
from pydantic import BaseModel, field_validator

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


# Ingredients
class IngredientOut(BaseModel):
    id: int
    name: str
    active: bool
    model_config = {"from_attributes": True}

class IngredientIn(BaseModel):
    name: str
    active: bool = True


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
