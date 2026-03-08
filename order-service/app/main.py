from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routers import orders

_otel_exporter_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
if _otel_exporter_endpoint or settings.otel_endpoint:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource

    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    if _otel_exporter_endpoint:
        exporter = OTLPSpanExporter()
    else:
        exporter = OTLPSpanExporter(endpoint=f"{settings.otel_endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


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

if _otel_exporter_endpoint or settings.otel_endpoint:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)


@app.get("/health")
def health():
    return {"status": "ok", "service": "order-service"}
