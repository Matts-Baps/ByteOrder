import os
from typing import Optional
from fastapi import Header, Query, HTTPException

AUTH_MODE = os.getenv("AUTH_MODE", "cloud")
DEFAULT_KITCHEN_ID = os.getenv("DEFAULT_KITCHEN_ID", "default")


def get_kitchen_id(
    x_kitchen_id: Optional[str] = Header(default=None, alias="x-kitchen-id"),
    kitchen_id: Optional[str] = Query(default=None),
) -> str:
    """Return the kitchen ID for the current request.

    Self-hosted: always returns DEFAULT_KITCHEN_ID (single-tenant).
    Cloud: extracted from X-Kitchen-ID header or kitchen_id query param,
           which the admin proxy injects from the Clerk org ID.
    """
    if AUTH_MODE == "self-hosted":
        return DEFAULT_KITCHEN_ID
    kid = x_kitchen_id or kitchen_id
    if not kid:
        raise HTTPException(status_code=400, detail="X-Kitchen-ID header or kitchen_id query param is required")
    return kid
