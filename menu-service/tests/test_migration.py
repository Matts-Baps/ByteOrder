"""
Tests for the startup database migration (_run_migrations).

Verifies:
- A fresh database (via create_all) has the correct multi-tenant schema.
- A pre-multi-tenancy database (settings with single-column PK, no kitchen_id)
  is correctly upgraded: kitchen_id column added, existing rows preserved with
  DEFAULT 'default', second run is idempotent.

The column-detection and column-addition steps are tested against SQLite so
they run in any CI environment. The PostgreSQL-specific PK constraint change
is exercised only on a real Postgres instance (tested end-to-end on the live
cluster, not mocked here).
"""
import pytest
from sqlalchemy import create_engine, inspect as sa_inspect, text
from sqlalchemy.pool import StaticPool

# ── Helpers ───────────────────────────────────────────────────────────────────

OLD_SCHEMA_SQL = [
    """CREATE TABLE settings (
        key     VARCHAR NOT NULL PRIMARY KEY,
        value   TEXT,
        updated_at DATETIME
    )""",
    "INSERT INTO settings (key, value) VALUES ('kitchen_name', 'Legacy Kitchen')",
    "INSERT INTO settings (key, value) VALUES ('brand_primary', '#ff0000')",
]

OLD_OTHER_TABLES_SQL = [
    "CREATE TABLE categories (id INTEGER PRIMARY KEY, name VARCHAR, sort_order INTEGER, active INTEGER, description TEXT)",
    "CREATE TABLE menu_items  (id INTEGER PRIMARY KEY, name VARCHAR, category_id INTEGER, description TEXT, active INTEGER, sort_order INTEGER)",
    "CREATE TABLE ingredients (id INTEGER PRIMARY KEY, name VARCHAR, active INTEGER)",
]


def _make_old_engine(*, include_other_tables=False):
    """SQLite engine with the pre-multi-tenancy schema."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.connect() as conn:
        for sql in OLD_SCHEMA_SQL + (OLD_OTHER_TABLES_SQL if include_other_tables else []):
            conn.execute(text(sql))
        conn.commit()
    return engine


# ── Fresh schema (create_all path) ────────────────────────────────────────────

class TestFreshSchema:
    """create_all on a blank database must produce the full multi-tenant schema."""

    def _fresh_engine(self):
        from app.database import Base
        import app.models  # noqa: F401 — registers all ORM classes
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        return engine

    def test_settings_has_kitchen_id(self):
        engine = self._fresh_engine()
        with engine.connect() as conn:
            cols = {c['name'] for c in sa_inspect(conn).get_columns('settings')}
        assert 'kitchen_id' in cols

    def test_settings_composite_primary_key(self):
        engine = self._fresh_engine()
        with engine.connect() as conn:
            pk = sa_inspect(conn).get_pk_constraint('settings')
        assert set(pk['constrained_columns']) == {'kitchen_id', 'key'}

    def test_kitchens_table_exists(self):
        engine = self._fresh_engine()
        with engine.connect() as conn:
            tables = sa_inspect(conn).get_table_names()
        assert 'kitchens' in tables

    def test_categories_has_kitchen_id(self):
        engine = self._fresh_engine()
        with engine.connect() as conn:
            cols = {c['name'] for c in sa_inspect(conn).get_columns('categories')}
        assert 'kitchen_id' in cols


# ── Migration of old schema ───────────────────────────────────────────────────

class TestMigrationOnOldSchema:
    """_run_migrations upgrades a pre-multi-tenancy settings table correctly."""

    def test_kitchen_id_column_added(self):
        engine = _make_old_engine()
        from app.main import _run_migrations
        _run_migrations(engine=engine)
        with engine.connect() as conn:
            cols = {c['name'] for c in sa_inspect(conn).get_columns('settings')}
        assert 'kitchen_id' in cols

    def test_existing_rows_get_default_kitchen_id(self):
        """Old rows must be tagged 'default', not empty string."""
        engine = _make_old_engine()
        from app.main import _run_migrations
        _run_migrations(engine=engine)
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT key, kitchen_id FROM settings")).fetchall()
        assert rows, "Expected pre-existing rows to survive migration"
        assert all(r[1] == 'default' for r in rows), (
            f"Expected all kitchen_ids to be 'default', got: {rows}"
        )

    def test_existing_data_preserved_after_migration(self):
        engine = _make_old_engine()
        from app.main import _run_migrations
        _run_migrations(engine=engine)
        with engine.connect() as conn:
            rows = {r[0]: r[1] for r in conn.execute(
                text("SELECT key, value FROM settings")
            ).fetchall()}
        assert rows.get('kitchen_name') == 'Legacy Kitchen'
        assert rows.get('brand_primary') == '#ff0000'

    def test_migration_idempotent(self):
        """Running migration twice must not raise and must leave schema correct."""
        engine = _make_old_engine()
        from app.main import _run_migrations
        _run_migrations(engine=engine)
        _run_migrations(engine=engine)  # second run
        with engine.connect() as conn:
            cols = {c['name'] for c in sa_inspect(conn).get_columns('settings')}
        assert 'kitchen_id' in cols

    def test_migration_also_handles_other_tables(self):
        """kitchen_id is added to categories, menu_items, ingredients too."""
        engine = _make_old_engine(include_other_tables=True)
        from app.main import _run_migrations
        _run_migrations(engine=engine)
        with engine.connect() as conn:
            insp = sa_inspect(conn)
            for table in ('categories', 'menu_items', 'ingredients'):
                cols = {c['name'] for c in insp.get_columns(table)}
                assert 'kitchen_id' in cols, f"Missing kitchen_id on {table}"

    def test_migration_skips_missing_tables_gracefully(self):
        """Migration must not crash if a table doesn't exist yet."""
        engine = _make_old_engine(include_other_tables=False)  # no categories etc.
        from app.main import _run_migrations
        _run_migrations(engine=engine)  # must not raise
