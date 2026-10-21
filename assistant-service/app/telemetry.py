"""OpenTelemetry setup, configured only through the standard OTEL_* variables.

Export is enabled only when OTEL_EXPORTER_OTLP_ENDPOINT is set. If something
else (such as the Dash0 operator's auto-instrumentation) has already installed
providers, they are reused rather than replaced.
"""
import functools
import logging
import os

from opentelemetry import metrics, trace

log = logging.getLogger(__name__)


def _exporters():
    protocol = os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
    if protocol == "grpc":
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    else:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    return OTLPSpanExporter(), OTLPMetricExporter()


@functools.cache
def _install_providers() -> None:
    """Install tracer and meter providers. Cached so it only ever runs once per process."""
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create()  # reads OTEL_SERVICE_NAME and OTEL_RESOURCE_ATTRIBUTES
    span_exporter, metric_exporter = _exporters()

    if isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(provider)
    else:
        log.info("Using existing tracer provider")

    if type(metrics.get_meter_provider()).__name__ == "_ProxyMeterProvider":
        metrics.set_meter_provider(
            MeterProvider(resource=resource, metric_readers=[PeriodicExportingMetricReader(metric_exporter)])
        )
    else:
        log.info("Using existing meter provider")


@functools.cache
def _instrument_httpx() -> None:
    """Patch httpx globally, once per process."""
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    HTTPXClientInstrumentor().instrument()


def setup_telemetry(app) -> None:
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return
    _install_providers()
    _instrument_httpx()

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
