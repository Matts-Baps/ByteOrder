from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.auth import get_kitchen_id

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=list[schemas.MenuItemOut])
def list_items(category_id: int | None = None, active_only: bool = True, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    q = db.query(models.MenuItem).filter(models.MenuItem.kitchen_id == kitchen_id)
    if active_only:
        q = q.filter(models.MenuItem.active == True)
    if category_id:
        q = q.filter(models.MenuItem.category_id == category_id)
    return q.order_by(models.MenuItem.sort_order).all()


@router.get("/{item_id}", response_model=schemas.MenuItemOut)
def get_item(item_id: int, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id, models.MenuItem.kitchen_id == kitchen_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("/", response_model=schemas.MenuItemOut, status_code=201)
def create_item(data: schemas.MenuItemIn, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    item = models.MenuItem(**data.model_dump(), kitchen_id=kitchen_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=schemas.MenuItemOut)
def update_item(item_id: int, data: schemas.MenuItemIn, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id, models.MenuItem.kitchen_id == kitchen_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for k, v in data.model_dump().items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id, models.MenuItem.kitchen_id == kitchen_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()


# Ingredients on an item (scoped via menu_item.kitchen_id)
@router.get("/{item_id}/ingredients", response_model=list[schemas.MenuItemIngredientOut])
def list_item_ingredients(item_id: int, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id, models.MenuItem.kitchen_id == kitchen_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item.item_ingredients


@router.post("/{item_id}/ingredients", response_model=schemas.MenuItemIngredientOut, status_code=201)
def add_item_ingredient(item_id: int, data: schemas.MenuItemIngredientIn, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id, models.MenuItem.kitchen_id == kitchen_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    mii = models.MenuItemIngredient(menu_item_id=item_id, **data.model_dump())
    db.add(mii)
    db.commit()
    db.refresh(mii)
    return mii


@router.delete("/{item_id}/ingredients/{ingredient_id}", status_code=204)
def remove_item_ingredient(item_id: int, ingredient_id: int, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id, models.MenuItem.kitchen_id == kitchen_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    mii = db.query(models.MenuItemIngredient).filter(
        models.MenuItemIngredient.menu_item_id == item_id,
        models.MenuItemIngredient.ingredient_id == ingredient_id,
    ).first()
    if not mii:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(mii)
    db.commit()


# Option groups on an item (scoped via menu_item.kitchen_id)
@router.get("/{item_id}/option-groups", response_model=list[schemas.OptionGroupOut])
def list_option_groups(item_id: int, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id, models.MenuItem.kitchen_id == kitchen_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item.option_groups


@router.post("/{item_id}/option-groups", response_model=schemas.OptionGroupOut, status_code=201)
def create_option_group(item_id: int, data: schemas.OptionGroupIn, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id, models.MenuItem.kitchen_id == kitchen_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    og = models.OptionGroup(menu_item_id=item_id, **data.model_dump())
    db.add(og)
    db.commit()
    db.refresh(og)
    return og


@router.delete("/{item_id}/option-groups/{group_id}", status_code=204)
def delete_option_group(item_id: int, group_id: int, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id, models.MenuItem.kitchen_id == kitchen_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    og = db.query(models.OptionGroup).filter(
        models.OptionGroup.id == group_id,
        models.OptionGroup.menu_item_id == item_id,
    ).first()
    if not og:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(og)
    db.commit()


# Options within a group (scoped via menu_item.kitchen_id)
@router.post("/{item_id}/option-groups/{group_id}/options", response_model=schemas.OptionOut, status_code=201)
def add_option(item_id: int, group_id: int, data: schemas.OptionIn, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id, models.MenuItem.kitchen_id == kitchen_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    og = db.query(models.OptionGroup).filter(
        models.OptionGroup.id == group_id,
        models.OptionGroup.menu_item_id == item_id,
    ).first()
    if not og:
        raise HTTPException(status_code=404, detail="Option group not found")
    opt = models.Option(group_id=group_id, **data.model_dump())
    db.add(opt)
    db.commit()
    db.refresh(opt)
    return opt


@router.delete("/{item_id}/option-groups/{group_id}/options/{option_id}", status_code=204)
def delete_option(item_id: int, group_id: int, option_id: int, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id, models.MenuItem.kitchen_id == kitchen_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    opt = db.query(models.Option).filter(
        models.Option.id == option_id,
        models.Option.group_id == group_id,
    ).first()
    if not opt:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(opt)
    db.commit()
