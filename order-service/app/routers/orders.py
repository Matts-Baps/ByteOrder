import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db, SessionLocal
from app.redis_client import get_redis

router = APIRouter(prefix="/orders", tags=["orders"])

ACTIVE_STATUSES = ("pending", "in_progress", "ready")


def _next_order_number(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"BO-{today}-"
    last = (
        db.query(models.Order)
        .filter(models.Order.order_number.like(f"{prefix}%"))
        .order_by(models.Order.id.desc())
        .first()
    )
    seq = int(last.order_number.split("-")[-1]) + 1 if last else 1
    return f"{prefix}{seq:03d}"


def _queue_position(order: models.Order, db: Session) -> int | None:
    if order.status not in ACTIVE_STATUSES:
        return None
    ahead = (
        db.query(models.Order)
        .filter(
            models.Order.status.in_(ACTIVE_STATUSES),
            models.Order.created_at < order.created_at,
        )
        .count()
    )
    return ahead + 1


@router.post("/", response_model=schemas.OrderOut, status_code=201)
def create_order(data: schemas.OrderIn, db: Session = Depends(get_db)):
    order = models.Order(
        order_number=_next_order_number(db),
        customer_name=data.customer_name,
    )
    db.add(order)
    db.flush()

    for item_data in data.items:
        item = models.OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
            menu_item_name=item_data.menu_item_name,
        )
        db.add(item)
        db.flush()

        for ing in item_data.ingredients:
            db.add(models.OrderItemIngredient(
                order_item_id=item.id,
                ingredient_id=ing.ingredient_id,
                ingredient_name=ing.ingredient_name,
                included=ing.included,
            ))
        for opt in item_data.options:
            db.add(models.OrderItemOption(
                order_item_id=item.id,
                option_id=opt.option_id,
                option_name=opt.option_name,
                group_name=opt.group_name,
            ))

    db.commit()
    db.refresh(order)

    # Publish to Redis for print-service and queue watchers
    redis = get_redis()
    redis.publish("queue_updates", json.dumps({"order_id": order.id, "status": order.status}))
    redis.publish("new_orders", json.dumps({
        "order_id": order.id,
        "order_number": order.order_number,
        "customer_name": order.customer_name,
        "items": [
            {
                "name": oi.menu_item_name,
                "ingredients": [
                    {"name": i.ingredient_name, "included": i.included}
                    for i in oi.ingredients
                ],
                "options": [
                    {"group": o.group_name, "name": o.option_name}
                    for o in oi.options
                ],
            }
            for oi in order.items
        ],
    }))

    result = schemas.OrderOut.model_validate(order)
    result.queue_position = _queue_position(order, db)
    return result


@router.get("/queue", response_model=list[schemas.OrderOut])
def get_queue(db: Session = Depends(get_db)):
    orders = (
        db.query(models.Order)
        .filter(models.Order.status.in_(ACTIVE_STATUSES))
        .order_by(models.Order.created_at)
        .all()
    )
    results = []
    for order in orders:
        out = schemas.OrderOut.model_validate(order)
        out.queue_position = _queue_position(order, db)
        results.append(out)
    return results


@router.get("/queue/stream")
async def queue_stream():
    async def event_generator():
        redis = get_redis()
        pubsub = redis.pubsub()
        pubsub.subscribe("queue_updates")
        try:
            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0)
                if message:
                    yield f"data: {message['data'].decode()}\n\n"
                else:
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.5)
        finally:
            pubsub.unsubscribe()
            pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/history", response_model=list[schemas.OrderOut])
def get_history(date: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Order).filter(models.Order.status == "completed")
    if date:
        try:
            d = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Use YYYY-MM-DD")
        q = q.filter(func.date(models.Order.created_at) == d)
    else:
        q = q.filter(func.date(models.Order.created_at) == datetime.utcnow().date())
    return q.order_by(models.Order.created_at.desc()).all()


@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    out = schemas.OrderOut.model_validate(order)
    out.queue_position = _queue_position(order, db)
    return out


@router.put("/{order_id}/status", response_model=schemas.OrderOut)
def update_status(order_id: int, data: schemas.OrderStatusUpdate, db: Session = Depends(get_db)):
    valid = ("pending", "in_progress", "ready", "completed")
    if data.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid}")

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = data.status
    db.commit()
    db.refresh(order)

    # Publish status change for SSE
    redis = get_redis()
    redis.publish(f"order_status:{order.id}", json.dumps({
        "order_id": order.id,
        "order_number": order.order_number,
        "status": order.status,
    }))
    # Also publish to global queue channel so home page updates
    redis.publish("queue_updates", json.dumps({"order_id": order.id, "status": order.status}))

    out = schemas.OrderOut.model_validate(order)
    out.queue_position = _queue_position(order, db)
    return out


@router.get("/{order_id}/stream")
async def order_stream(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    async def event_generator():
        redis = get_redis()
        pubsub = redis.pubsub()
        pubsub.subscribe(f"order_status:{order_id}")
        try:
            # Send current status immediately
            current_db = SessionLocal()
            try:
                current = current_db.query(models.Order).filter(models.Order.id == order_id).first()
                pos = _queue_position(current, current_db)
                yield f"data: {json.dumps({'status': current.status, 'queue_position': pos})}\n\n"
            finally:
                current_db.close()

            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0)
                if message:
                    yield f"data: {message['data'].decode()}\n\n"
                else:
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.5)
        finally:
            pubsub.unsubscribe()
            pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
