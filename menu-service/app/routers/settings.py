from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/settings", tags=["settings"])

ALLOWED_KEYS = {"printer_url", "kitchen_name", "frontend_url", "logo"}


@router.get("/", response_model=list[schemas.SettingOut])
def list_settings(db: Session = Depends(get_db)):
    return db.query(models.Setting).all()


@router.get("/{key}", response_model=schemas.SettingOut)
def get_setting(key: str, db: Session = Depends(get_db)):
    setting = db.query(models.Setting).filter(models.Setting.key == key).first()
    if not setting:
        return schemas.SettingOut(key=key, value=None)
    return setting


@router.put("/{key}", response_model=schemas.SettingOut)
def upsert_setting(key: str, data: schemas.SettingIn, db: Session = Depends(get_db)):
    setting = db.query(models.Setting).filter(models.Setting.key == key).first()
    if setting:
        setting.value = data.value
    else:
        setting = models.Setting(key=key, value=data.value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting
