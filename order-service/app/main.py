from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.telemetry import setup_telemetry
from app.routers import orders, printers


def _run_migrations():
    """Idempotent schema migrations. Safe to run on every startup."""
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS kitchen_id VARCHAR NOT NULL DEFAULT ''"))
        conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS public_id VARCHAR"))
        # Back-fill public_id for rows that predate this column, then enforce NOT NULL + UNIQUE
        conn.execute(text("UPDATE orders SET public_id = gen_random_uuid()::text WHERE public_id IS NULL"))
        conn.execute(text("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE table_name = 'orders' AND constraint_name = 'orders_public_id_key'
                ) THEN
                    ALTER TABLE orders ALTER COLUMN public_id SET NOT NULL;
                    ALTER TABLE orders ADD CONSTRAINT orders_public_id_key UNIQUE (public_id);
                END IF;
            END $$
        """))
        conn.execute(text("ALTER TABLE printer_devices ADD COLUMN IF NOT EXISTS ip_address VARCHAR"))
        conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    yield


app = FastAPI(title="ByteOrder Order Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orders.router)
app.include_router(printers.router)

setup_telemetry(engine=engine, app=app)


@app.get("/health")
def health():
    return {"status": "ok", "service": "order-service"}
