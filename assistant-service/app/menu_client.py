import httpx

from app.menu import Menu

DEFAULT_KITCHEN_NAME = "this kitchen"


class MenuUnavailable(Exception):
    pass


async def fetch_menu(base_url: str, kitchen_id: str) -> tuple[Menu, str]:
    """Load the kitchen's active menu and display name from menu-service."""
    headers = {"X-Kitchen-ID": kitchen_id}
    try:
        async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=10.0) as client:
            categories = await client.get("/categories/")
            categories.raise_for_status()
            name = await client.get("/settings/kitchen_name")
            kitchen_name = (name.json().get("value") if name.is_success else None) or DEFAULT_KITCHEN_NAME
            return Menu.from_categories(categories.json()), kitchen_name
    except (httpx.HTTPError, ValueError) as exc:
        raise MenuUnavailable(str(exc)) from exc
