from typing import Optional
from fastapi import Header, Query, HTTPException


def get_kitchen_id(
    x_kitchen_id: Optional[str] = Header(default=None, alias="x-kitchen-id"),
    kitchen_id: Optional[str] = Query(default=None),
) -> str:
    """Extract kitchen ID from X-Kitchen-ID header or kitchen_id query param.

    Header is set by the admin Express proxy (from Clerk orgId) and by axios
    on the customer frontend. Query param is used as a fallback for EventSource
    connections, which cannot set custom headers.
    """
    kid = x_kitchen_id or kitchen_id
    if not kid:
        raise HTTPException(status_code=400, detail="X-Kitchen-ID header or kitchen_id query param is required")
    return kid
