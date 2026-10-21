"""OpenTelemetry is configured only from the standard OTEL_* variables (#56)."""
from unittest.mock import patch

import pytest

from app import telemetry
from app.config import settings

ENDPOINT = "http://collector:4318"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in (
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_PROTOCOL",
        "OTEL_SERVICE_NAME",
        "OTEL_RESOURCE_ATTRIBUTES",
        "OTEL_ENDPOINT",
    ):
        monkeypatch.delenv(var, raising=False)


def test_export_is_off_without_an_endpoint():
    with patch.object(telemetry, "_install") as install:
        assert telemetry.setup_telemetry(engine="engine") is False
    install.assert_not_called()


def test_the_old_otel_endpoint_variable_is_ignored(monkeypatch):
    monkeypatch.setenv("OTEL_ENDPOINT", ENDPOINT)
    with patch.object(telemetry, "_install") as install:
        assert telemetry.setup_telemetry(engine="engine") is False
    install.assert_not_called()


def test_export_is_on_with_the_standard_endpoint(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", ENDPOINT)
    with patch.object(telemetry, "_install") as install:
        assert telemetry.setup_telemetry(engine="engine") is True
    install.assert_called_once_with(engine="engine")


def test_settings_no_longer_carry_otel_config():
    assert not hasattr(settings, "otel_endpoint")
    assert not hasattr(settings, "otel_service_name")


def test_service_name_has_a_default():
    assert telemetry.resource().attributes["service.name"] == "print-service"


def test_service_name_comes_from_otel_service_name(monkeypatch):
    monkeypatch.setenv("OTEL_SERVICE_NAME", "byteorder-print-service")
    assert telemetry.resource().attributes["service.name"] == "byteorder-print-service"


@pytest.mark.parametrize(
    ("protocol", "module"),
    [(None, "proto.http"), ("http/protobuf", "proto.http"), ("grpc", "proto.grpc")],
)
def test_exporters_follow_otel_exporter_otlp_protocol(monkeypatch, protocol, module):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", ENDPOINT)
    if protocol:
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", protocol)
    spans, metrics = telemetry.exporters()
    assert module in type(spans).__module__
    assert module in type(metrics).__module__
