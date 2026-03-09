from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routers import categories, items, ingredients, settings as settings_router, kitchens

# OpenTelemetry setup
_otel_exporter_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
if _otel_exporter_endpoint or settings.otel_endpoint:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    resource = Resource.create({"service.name": settings.otel_service_name})

    # Prefer the standard env var (injected by Dash0); fall back to OTEL_ENDPOINT for
    # non-Dash0 deployments, appending the required OTLP paths.
    if _otel_exporter_endpoint:
        trace_exporter = OTLPSpanExporter()
        metric_exporter = OTLPMetricExporter()
    else:
        trace_exporter = OTLPSpanExporter(endpoint=f"{settings.otel_endpoint}/v1/traces")
        metric_exporter = OTLPMetricExporter(endpoint=f"{settings.otel_endpoint}/v1/metrics")

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(provider)

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[PeriodicExportingMetricReader(metric_exporter)],
    )
    metrics.set_meter_provider(meter_provider)

    SQLAlchemyInstrumentor().instrument(engine=engine)


def _run_migrations():
    """Idempotent schema migrations. Safe to run on every startup."""
    with engine.connect() as conn:
        # Add kitchen_id to tables that predate multi-tenancy
        conn.execute(text("ALTER TABLE categories ADD COLUMN IF NOT EXISTS kitchen_id VARCHAR NOT NULL DEFAULT ''"))
        conn.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS kitchen_id VARCHAR NOT NULL DEFAULT ''"))
        conn.execute(text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS kitchen_id VARCHAR NOT NULL DEFAULT ''"))
        # Migrate settings from single-column PK (key) to composite PK (kitchen_id, key)
        conn.execute(text("ALTER TABLE settings ADD COLUMN IF NOT EXISTS kitchen_id VARCHAR NOT NULL DEFAULT ''"))
        conn.execute(text("""
            DO $$ BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conrelid = 'settings'::regclass
                    AND contype = 'p'
                    AND array_length(conkey, 1) = 1
                ) THEN
                    ALTER TABLE settings DROP CONSTRAINT settings_pkey;
                    ALTER TABLE settings ADD PRIMARY KEY (kitchen_id, key);
                END IF;
            END $$
        """))
        # kitchens table is created by Base.metadata.create_all, no ALTER needed
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

if _otel_exporter_endpoint or settings.otel_endpoint:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app, tracer_provider=trace.get_tracer_provider())


@app.get("/health")
def health():
    return {"status": "ok", "service": "menu-service"}
