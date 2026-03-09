from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.auth import get_kitchen_id
import app.models  # noqa: F401 — ensures all tables are registered with Base before create_all

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

Base.metadata.create_all(bind=test_engine)


@pytest.fixture(autouse=True)
def clean_tables():
    """Wipe all rows between tests so each test starts with a clean slate."""
    yield
    with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_redis():
    mock = MagicMock()
    mock.publish = MagicMock(return_value=None)
    pubsub_mock = MagicMock()
    pubsub_mock.subscribe = MagicMock()
    pubsub_mock.get_message = MagicMock(return_value=None)
    mock.pubsub = MagicMock(return_value=pubsub_mock)
    return mock


@pytest.fixture
def client(db, mock_redis):
    from app.main import app

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_kitchen_id():
        return "test-kitchen"

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_kitchen_id] = override_get_kitchen_id

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    with patch.object(app.router, "lifespan_context", noop_lifespan), \
         patch("app.routers.orders.get_redis", return_value=mock_redis), \
         patch("app.routers.printers.get_redis", return_value=mock_redis):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()
