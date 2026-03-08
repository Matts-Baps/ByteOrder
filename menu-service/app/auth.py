from fastapi import Header, HTTPException


def get_kitchen_id(x_kitchen_id: str = Header(alias="x-kitchen-id")) -> str:
    """Extract kitchen ID from the X-Kitchen-ID request header.

    Set by the admin Express proxy (from Clerk orgId) and by the
    customer-facing nginx (from the Helm kitchenId value).
    """
    if not x_kitchen_id:
        raise HTTPException(status_code=400, detail="X-Kitchen-ID header is required")
    return x_kitchen_id
