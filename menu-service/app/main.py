from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.telemetry import setup_telemetry
from app.routers import categories, items, ingredients, settings as settings_router, kitchens


def _run_migrations(engine=None):
    """Idempotent schema migrations. Safe to run on every startup.

    Uses SQLAlchemy inspect() for column detection so it works on both SQLite
    (tests) and PostgreSQL (production).  The primary-key fix for the settings
    table is PostgreSQL-only and is skipped on other dialects.
    """
    from sqlalchemy import inspect as sa_inspect

    _engine = engine or globals()['engine']

    with _engine.connect() as conn:
        insp = sa_inspect(conn)
        existing_tables = set(insp.get_table_names())

        # Add kitchen_id to tables that predate multi-tenancy (orphan old rows with '').
        for table_name in ('categories', 'menu_items', 'ingredients'):
            if table_name in existing_tables:
                cols = {c['name'] for c in insp.get_columns(table_name)}
                if 'kitchen_id' not in cols:
                    conn.execute(text(
                        f"ALTER TABLE {table_name} ADD COLUMN kitchen_id VARCHAR NOT NULL DEFAULT ''"
                    ))

        # settings: add kitchen_id with DEFAULT 'default' so self-hosted installs
        # retain their existing data under the default kitchen.
        if 'settings' in existing_tables:
            settings_cols = {c['name'] for c in insp.get_columns('settings')}
            if 'kitchen_id' not in settings_cols:
                conn.execute(text(
                    "ALTER TABLE settings ADD COLUMN kitchen_id VARCHAR NOT NULL DEFAULT 'default'"
                ))
                # Fix primary key: drop single-column PK and replace with composite.
                # This step is PostgreSQL-specific; SQLite doesn't support PK changes
                # and create_all handles fresh SQLite DBs correctly already.
                if _engine.dialect.name == 'postgresql':
                    conn.execute(text("""
                        DO $$ BEGIN
                            IF EXISTS (
                                SELECT 1 FROM pg_constraint
                                WHERE conrelid = 'settings'::regclass AND contype = 'p'
                            ) THEN
                                ALTER TABLE settings DROP CONSTRAINT settings_pkey;
                            END IF;
                            ALTER TABLE settings ADD PRIMARY KEY (kitchen_id, key);
                        END $$
                    """))

        conn.commit()


def _seed_self_hosted():
    """In self-hosted mode, ensure a 'default' kitchen row exists so the
    customer frontend can load brand settings without any manual setup."""
    if os.getenv("AUTH_MODE") != "self-hosted":
        return
    kitchen_id = os.getenv("DEFAULT_KITCHEN_ID", "default")
    slug = os.getenv("DEFAULT_KITCHEN_SLUG", kitchen_id)
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO kitchens (kitchen_id, slug)
            VALUES (:kid, :slug)
            ON CONFLICT DO NOTHING
        """), {"kid": kitchen_id, "slug": slug})
        conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    _seed_self_hosted()
    yield


app = FastAPI(title="ByteOrder Menu Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(items.router)
app.include_router(ingredients.router)
app.include_router(settings_router.router)
app.include_router(kitchens.router)

setup_telemetry(engine=engine, app=app)


@app.get("/health")
def health():
    return {"status": "ok", "service": "menu-service"}
