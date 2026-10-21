"""OpenTelemetry setup, configured only through the standard OTEL_* variables.

Export is enabled only when OTEL_EXPORTER_OTLP_ENDPOINT is set. The exporters
read the endpoint, protocol and headers themselves. If something else (such as
the Dash0 operator's auto-instrumentation) has already installed providers, they
are reused rather than replaced.
"""
import logging
import os

from opentelemetry import metrics, trace

SERVICE_NAME = "print-service"

log = logging.getLogger(__name__)


def resource():
    from opentelemetry.sdk.resources import Resource

    # Resource.create() reads OTEL_SERVICE_NAME and OTEL_RESOURCE_ATTRIBUTES.
    if os.environ.get("OTEL_SERVICE_NAME"):
        return Resource.create()
    return Resource.create({"service.name": SERVICE_NAME})


def exporters():
    if os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL") == "grpc":
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    else:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    return OTLPSpanExporter(), OTLPMetricExporter()


def _install_providers() -> None:
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    res = resource()
    span_exporter, metric_exporter = exporters()

    if isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
        provider = TracerProvider(resource=res)
        provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(provider)
    else:
        log.info("Using existing tracer provider")

    if type(metrics.get_meter_provider()).__name__ == "_ProxyMeterProvider":
        metrics.set_meter_provider(
            MeterProvider(resource=res, metric_readers=[PeriodicExportingMetricReader(metric_exporter)])
        )
    else:
        log.info("Using existing meter provider")


def _install(engine) -> None:
    _install_providers()

    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    SQLAlchemyInstrumentor().instrument(engine=engine)
    RedisInstrumentor().instrument()
    RequestsInstrumentor().instrument()


def setup_telemetry(engine) -> bool:
    """Set up export and instrumentation. Returns False when export is off."""
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return False
    _install(engine=engine)
    return True
