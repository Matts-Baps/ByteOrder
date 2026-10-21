from fastapi import APIRouter

from app import schemas
from app.allergens import LABELS

router = APIRouter(prefix="/allergens", tags=["allergens"])


@router.get("/", response_model=list[schemas.AllergenOut])
def list_allergens():
    """The fixed list of allergens ingredients can be tagged with. No auth required."""
    return [{"id": a, "label": label} for a, label in LABELS.items()]
