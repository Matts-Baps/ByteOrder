import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.auth import get_kitchen_id

router = APIRouter(tags=["kitchens"])

SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$')


# ── Public endpoint ────────────────────────────────────────────────────────────

@router.get("/slug/{slug}", response_model=schemas.SlugLookupOut)
def resolve_slug(slug: str, db: Session = Depends(get_db)):
    """Resolve a friendly slug to a kitchen_id. No auth required."""
    kitchen = db.query(models.Kitchen).filter(models.Kitchen.slug == slug).first()
    if not kitchen:
        raise HTTPException(status_code=404, detail="Kitchen not found")
    return kitchen


# ── Authenticated endpoints ────────────────────────────────────────────────────

@router.get("/kitchens/me", response_model=schemas.KitchenOut)
def get_my_kitchen(db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    kitchen = db.query(models.Kitchen).filter(models.Kitchen.kitchen_id == kitchen_id).first()
    if not kitchen:
        raise HTTPException(status_code=404, detail="Kitchen profile not set up yet")
    return kitchen


@router.put("/kitchens/me", response_model=schemas.KitchenOut)
def upsert_my_kitchen(data: schemas.KitchenIn, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    # Check slug uniqueness (allow re-saving the same slug)
    existing = db.query(models.Kitchen).filter(
        models.Kitchen.slug == data.slug,
        models.Kitchen.kitchen_id != kitchen_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="That slug is already taken — please choose another")

    kitchen = db.query(models.Kitchen).filter(models.Kitchen.kitchen_id == kitchen_id).first()
    if kitchen:
        kitchen.slug = data.slug
    else:
        kitchen = models.Kitchen(kitchen_id=kitchen_id, slug=data.slug)
        db.add(kitchen)
    db.commit()
    db.refresh(kitchen)
    return kitchen
