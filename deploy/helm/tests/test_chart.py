"""Render tests for the ByteOrder Helm chart.

Run from the repo root:  uvx --with pyyaml pytest deploy/helm/tests
Needs `helm` on PATH.
"""

import subprocess
from pathlib import Path

import pytest
import yaml

CHART = Path(__file__).resolve().parents[1] / "byteorder"
BACKENDS = ["menu-service", "order-service", "print-service", "admin"]
CLOUD = ["clerk.publishableKey=pk", "clerk.secretKey=sk"]
SELF_HOSTED = ["authMode=self-hosted", "selfHosted.adminPassword=pw", "selfHosted.jwtSecret=jwt"]


def render(*sets: str) -> subprocess.CompletedProcess:
    """Render the chart. Cloud mode (with Clerk keys) unless the sets say otherwise."""
    args = ["helm", "template", "t", str(CHART)]
    for s in CLOUD + list(sets):
        args += ["--set", s]
    return subprocess.run(args, capture_output=True, text=True)


def deployments(*sets: str) -> dict[str, dict]:
    """Render the chart and return {deployment name: {env name: env entry}}."""
    result = render(*sets)
    assert result.returncode == 0, result.stderr
    out = {}
    for doc in yaml.safe_load_all(result.stdout):
        if doc and doc["kind"] == "Deployment":
            container = doc["spec"]["template"]["spec"]["containers"][0]
            out[doc["metadata"]["name"]] = {e["name"]: e for e in container.get("env", [])}
    return out


def secret_name(entry: dict) -> str:
    return entry["valueFrom"]["secretKeyRef"]["name"]


# --- auth modes (#58) ---------------------------------------------------------


def test_cloud_mode_renders():
    env = deployments()["byteorder-admin"]
    assert secret_name(env["CLERK_SECRET_KEY"]) == "byteorder-clerk"


def test_self_hosted_mode_renders_with_inline_credentials():
    env = deployments(*SELF_HOSTED)["byteorder-admin"]
    for var in ("ADMIN_USERNAME", "ADMIN_PASSWORD", "JWT_SECRET"):
        assert secret_name(env[var]) == "byteorder-self-hosted"


def test_self_hosted_mode_uses_an_existing_secret():
    env = deployments("authMode=self-hosted", "selfHosted.existingSecretName=mine")["byteorder-admin"]
    for var in ("ADMIN_USERNAME", "ADMIN_PASSWORD", "JWT_SECRET"):
        assert secret_name(env[var]) == "mine"


# --- OpenTelemetry (#56) ------------------------------------------------------


@pytest.mark.parametrize("sets", [(), tuple(SELF_HOSTED)], ids=["cloud", "self-hosted"])
def test_otel_export_is_off_by_default(sets):
    for name, env in deployments(*sets).items():
        assert "OTEL_EXPORTER_OTLP_ENDPOINT" not in env, name
        assert "OTEL_ENDPOINT" not in env, name


def test_every_backend_has_a_service_name():
    deps = deployments("assistant.enabled=true", "assistant.ollamaUrl=http://ollama:11434")
    for svc in BACKENDS + ["assistant-service"]:
        assert deps[f"byteorder-{svc}"]["OTEL_SERVICE_NAME"]["value"] == f"byteorder-{svc}"


def test_otel_endpoint_is_passed_to_every_backend():
    deps = deployments(
        "otel.endpoint=http://collector:4318",
        "assistant.enabled=true",
        "assistant.ollamaUrl=http://ollama:11434",
    )
    for svc in BACKENDS + ["assistant-service"]:
        env = deps[f"byteorder-{svc}"]
        assert env["OTEL_EXPORTER_OTLP_ENDPOINT"]["value"] == "http://collector:4318"
        assert env["OTEL_EXPORTER_OTLP_PROTOCOL"]["value"] == "http/protobuf"
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" not in deps["byteorder-frontend"]


def test_otel_headers_come_from_a_secret():
    deps = deployments("otel.endpoint=http://collector:4318", "otel.headersSecret.name=otel-auth")
    for svc in BACKENDS:
        ref = deps[f"byteorder-{svc}"]["OTEL_EXPORTER_OTLP_HEADERS"]["valueFrom"]["secretKeyRef"]
        assert ref == {"name": "otel-auth", "key": "headers"}


def test_extra_otel_env_is_passed_through():
    deps = deployments("otel.env.OTEL_RESOURCE_ATTRIBUTES=deployment.environment.name=prod")
    for svc in BACKENDS:
        env = deps[f"byteorder-{svc}"]
        assert env["OTEL_RESOURCE_ATTRIBUTES"]["value"] == "deployment.environment.name=prod"


def test_old_otel_endpoint_value_fails_with_a_hint():
    result = render("otelEndpoint=http://collector:4318")
    assert result.returncode != 0
    assert "otel.endpoint" in result.stderr


# --- frontend nginx config rollout -------------------------------------------


def frontend_annotations(*sets: str) -> dict:
    result = render(*sets)
    assert result.returncode == 0, result.stderr
    for doc in yaml.safe_load_all(result.stdout):
        if doc and doc["kind"] == "Deployment" and doc["metadata"]["name"] == "byteorder-frontend":
            return doc["spec"]["template"]["metadata"].get("annotations") or {}
    raise AssertionError("no frontend deployment")


def test_frontend_restarts_when_its_nginx_config_changes():
    # The config is mounted with subPath, so a running pod never sees ConfigMap
    # changes. A checksum on the pod template makes Helm roll the pod instead.
    off = frontend_annotations()
    on = frontend_annotations("assistant.enabled=true", "assistant.ollamaUrl=http://ollama:11434")
    assert off.get("checksum/nginx-config")
    assert off["checksum/nginx-config"] != on["checksum/nginx-config"]


def test_frontend_checksum_is_stable():
    assert frontend_annotations() == frontend_annotations()


# --- admin behind the ingress (#64) -------------------------------------------


def test_admin_trusts_one_proxy_hop_by_default():
    env = deployments()["byteorder-admin"]
    assert env["TRUST_PROXY"]["value"] == "1"


def test_admin_trusted_hops_are_configurable():
    env = deployments("admin.trustProxy=2")["byteorder-admin"]
    assert env["TRUST_PROXY"]["value"] == "2"


def test_only_admin_gets_trust_proxy():
    for name, env in deployments().items():
        if name != "byteorder-admin":
            assert "TRUST_PROXY" not in env, name


# --- browser telemetry (#62) ---------------------------------------------------

BROWSER = ["otel.endpoint=http://collector:4318", "otel.browser.enabled=true"]


def nginx_config(*sets: str) -> str:
    result = render(*sets)
    assert result.returncode == 0, result.stderr
    for doc in yaml.safe_load_all(result.stdout):
        if doc and doc["kind"] == "ConfigMap" and doc["metadata"]["name"] == "byteorder-frontend-nginx":
            return doc["data"]["default.conf"]
    raise AssertionError("frontend nginx ConfigMap not found")


def test_browser_telemetry_is_off_by_default():
    env = deployments("otel.endpoint=http://collector:4318")["byteorder-frontend"]
    assert "BROWSER_TELEMETRY_ENABLED" not in env
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" not in env


def test_browser_telemetry_gets_the_collector_settings():
    env = deployments(*BROWSER, "otel.headersSecret.name=otlp", "otel.browser.sampleRate=25")["byteorder-frontend"]
    assert env["BROWSER_TELEMETRY_ENABLED"]["value"] == "true"
    assert env["BROWSER_TELEMETRY_SAMPLE_RATE"]["value"] == "25"
    assert env["BROWSER_TELEMETRY_SESSION_REPLAY"]["value"] == "false"
    assert env["OTEL_EXPORTER_OTLP_ENDPOINT"]["value"] == "http://collector:4318"
    assert env["OTEL_EXPORTER_OTLP_PROTOCOL"]["value"] == "http/protobuf"
    assert env["OTEL_SERVICE_NAME"]["value"] == "byteorder-frontend"
    assert secret_name(env["OTEL_EXPORTER_OTLP_HEADERS"]) == "otlp"


def test_frontend_never_gets_backend_settings():
    env = deployments(*BROWSER)["byteorder-frontend"]
    for var in ("REDIS_URL", "AUTH_MODE"):
        assert var not in env


def test_browser_telemetry_needs_an_endpoint():
    result = render("otel.browser.enabled=true")
    assert result.returncode != 0
    assert "otel.endpoint" in result.stderr


def test_nginx_config_includes_the_generated_telemetry_proxy():
    config = nginx_config()
    assert "include /etc/nginx/byteorder/*.conf;" in config
    assert "location = /runtime-config.js" in config


def test_session_replay_can_be_switched_on():
    env = deployments(*BROWSER, "otel.browser.sessionReplay=true")["byteorder-frontend"]
    assert env["BROWSER_TELEMETRY_SESSION_REPLAY"]["value"] == "true"
