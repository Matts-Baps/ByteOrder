import ipaddress
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.auth import get_kitchen_id

router = APIRouter(prefix="/settings", tags=["settings"])

ALLOWED_KEYS = {"printer_url", "kitchen_name", "frontend_url", "logo", "brand_primary", "brand_bg", "brand_surface", "brand_text"}

# Hosts that must never be used as printer targets (internal service names + metadata endpoints)
_BLOCKED_PRINTER_HOSTS = {
    "localhost", "postgres", "redis", "menu-service", "order-service",
    "admin", "print-service", "metadata.google.internal",
}


def _validate_printer_url(url: str) -> None:
    """Reject URLs that could be used for SSRF against internal resources."""
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="printer_url is not a valid URL")

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="printer_url must use http or https")

    host = (parsed.hostname or "").lower()
    if not host:
        raise HTTPException(status_code=400, detail="printer_url must include a hostname")

    if host in _BLOCKED_PRINTER_HOSTS:
        raise HTTPException(status_code=400, detail="printer_url cannot point to an internal host")

    try:
        addr = ipaddress.ip_address(host)
        # Allow private LAN IPs (printer lives on the local network).
        # Block only loopback (127.x, ::1) and link-local (169.254.x — cloud metadata).
        if addr.is_loopback or addr.is_link_local:
            raise HTTPException(status_code=400, detail="printer_url cannot point to a loopback or link-local address")
    except ValueError:
        pass  # Not an IP literal — hostname validation above is sufficient


@router.get("/", response_model=list[schemas.SettingOut])
def list_settings(db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    return db.query(models.Setting).filter(models.Setting.kitchen_id == kitchen_id).all()


@router.get("/{key}", response_model=schemas.SettingOut)
def get_setting(key: str, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    setting = db.query(models.Setting).filter(models.Setting.kitchen_id == kitchen_id, models.Setting.key == key).first()
    if not setting:
        return schemas.SettingOut(key=key, value=None)
    return setting


@router.put("/{key}", response_model=schemas.SettingOut)
def upsert_setting(key: str, data: schemas.SettingIn, db: Session = Depends(get_db), kitchen_id: str = Depends(get_kitchen_id)):
    if key not in ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail=f"Unknown setting key: {key}")
    if key == "printer_url" and data.value:
        _validate_printer_url(data.value)
    setting = db.query(models.Setting).filter(models.Setting.kitchen_id == kitchen_id, models.Setting.key == key).first()
    if setting:
        setting.value = data.value
    else:
        setting = models.Setting(kitchen_id=kitchen_id, key=key, value=data.value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting
