from fastapi import FastAPI
from opentelemetry import trace

from app.telemetry import setup_telemetry


def test_does_nothing_without_an_endpoint(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    before = trace.get_tracer_provider()
    setup_telemetry(FastAPI())
    assert trace.get_tracer_provider() is before
