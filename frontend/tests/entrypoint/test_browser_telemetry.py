"""Tests for the nginx start-up script that switches on browser telemetry (#62).

Runs the real frontend nginx config in an nginx:alpine container, with a fake
collector on :4318 that echoes back what it receives.

Run from the repo root:  uvx pytest frontend/tests/entrypoint
Needs Docker.
"""

import subprocess
import time
import uuid
from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[2]
SCRIPT = FRONTEND / "docker-entrypoint.d" / "40-byteorder-browser-telemetry.sh"
IMAGE = "nginx:alpine"

# Stands in for the OpenTelemetry collector.
FAKE_COLLECTOR = r"""
server {
    listen 4318;
    location / {
        default_type text/plain;
        return 200 "auth=[$http_authorization] cookie=[$http_cookie] uri=$request_uri\n";
    }
}
"""


class Frontend:
    def __init__(self, name: str):
        self.name = name

    def sh(self, command: str) -> str:
        result = subprocess.run(
            ["docker", "exec", self.name, "sh", "-c", command],
            capture_output=True, text=True, check=True,
        )
        return result.stdout

    def request(self, path: str, *curl_args: str) -> tuple[int, str]:
        out = self.sh(
            "curl -s -w '\\n%{http_code}' "
            + " ".join(curl_args)
            + f" http://localhost{path}"
        )
        body, _, status = out.rpartition("\n")
        return int(status), body

    def post(self, path: str, *curl_args: str) -> tuple[int, str]:
        return self.request(path, "-X POST -H 'Content-Type: application/json' -d '{}'", *curl_args)

    def logs(self) -> str:
        result = subprocess.run(["docker", "logs", self.name], capture_output=True, text=True)
        return result.stdout + result.stderr


@pytest.fixture
def frontend(tmp_path):
    """Start the frontend nginx with the given env, and stop it afterwards."""
    started = []
    (tmp_path / "html").mkdir()
    (tmp_path / "html" / "index.html").write_text("<html>ByteOrder</html>")
    (tmp_path / "collector.conf").write_text(FAKE_COLLECTOR)

    def start(**env: str) -> Frontend:
        # Docker would otherwise create a root-owned directory in its place.
        assert SCRIPT.is_file(), f"missing {SCRIPT}"
        name = f"byteorder-telemetry-test-{uuid.uuid4().hex[:8]}"
        args = ["docker", "run", "-d", "--name", name]
        for host in ("menu-service", "order-service", "assistant-service", "collector"):
            args += ["--add-host", f"{host}:127.0.0.1"]
        args += [
            "-v", f"{SCRIPT}:/docker-entrypoint.d/40-byteorder-browser-telemetry.sh:ro",
            "-v", f"{FRONTEND / 'nginx.conf'}:/etc/nginx/conf.d/default.conf:ro",
            "-v", f"{tmp_path / 'collector.conf'}:/etc/nginx/conf.d/zz-collector.conf:ro",
            "-v", f"{tmp_path / 'html' / 'index.html'}:/usr/share/nginx/html/index.html:ro",
        ]
        for key, value in env.items():
            args += ["-e", f"{key}={value}"]
        subprocess.run(args + [IMAGE], check=True, capture_output=True)
        started.append(name)
        fe = Frontend(name)
        for _ in range(50):
            try:
                if fe.request("/")[0] == 200:
                    return fe
            except subprocess.CalledProcessError:
                pass
            time.sleep(0.1)
        pytest.fail(f"nginx did not start:\n{fe.logs()}")

    yield start
    for name in started:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


ON = {
    "BROWSER_TELEMETRY_ENABLED": "true",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4318",
}


def runtime_config(fe: Frontend) -> str:
    status, body = fe.request("/runtime-config.js")
    assert status == 200
    return body


# --- off unless asked for ------------------------------------------------------


def test_off_by_default(frontend):
    fe = frontend()
    assert '"enabled": false' in runtime_config(fe)
    status, body = fe.post("/otel/v1/traces")
    assert "auth=" not in body


def test_off_when_only_the_backend_endpoint_is_set(frontend):
    fe = frontend(OTEL_EXPORTER_OTLP_ENDPOINT="http://collector:4318")
    assert '"enabled": false' in runtime_config(fe)


@pytest.mark.parametrize(
    "env, reason",
    [
        ({"BROWSER_TELEMETRY_ENABLED": "true"}, "OTEL_EXPORTER_OTLP_ENDPOINT"),
        ({**ON, "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc"}, "HTTP"),
        ({**ON, "OTEL_EXPORTER_OTLP_ENDPOINT": "http://no-such-collector.invalid:4318"}, "resolve"),
        ({**ON, "OTEL_EXPORTER_OTLP_ENDPOINT": "collector:4318"}, "http"),
        ({**ON, "BROWSER_TELEMETRY_SAMPLE_RATE": "150"}, "BROWSER_TELEMETRY_SAMPLE_RATE"),
        ({**ON, "BROWSER_TELEMETRY_SESSION_REPLAY": "yes"}, "BROWSER_TELEMETRY_SESSION_REPLAY"),
    ],
    ids=["no-endpoint", "grpc", "unresolvable", "no-scheme", "bad-sample-rate", "bad-replay-flag"],
)
def test_stays_off_and_says_why_when_misconfigured(frontend, env, reason):
    fe = frontend(**env)
    assert '"enabled": false' in runtime_config(fe)
    assert "byteorder-browser-telemetry" in fe.logs()
    assert reason in fe.logs()
    # nginx still serves the app.
    assert fe.request("/")[0] == 200


# --- on --------------------------------------------------------------------------


def test_runtime_config_switches_tracing_on(frontend):
    fe = frontend(**ON, OTEL_SERVICE_NAME="byteorder-frontend", BROWSER_TELEMETRY_SAMPLE_RATE="25")
    config = runtime_config(fe)
    assert '"enabled": true' in config
    assert '"serviceName": "byteorder-frontend"' in config
    assert '"sampleRate": 25' in config


def test_session_replay_is_off_by_default(frontend):
    assert '"sessionReplay": false' in runtime_config(frontend(**ON))


def test_session_replay_can_be_switched_on(frontend):
    fe = frontend(**ON, BROWSER_TELEMETRY_SESSION_REPLAY="true")
    assert '"sessionReplay": true' in runtime_config(fe)


def test_runtime_config_is_not_cached(frontend):
    fe = frontend(**ON)
    headers = fe.sh("curl -sI http://localhost/runtime-config.js")
    assert "no-store" in headers.lower()


@pytest.mark.parametrize("signal", ["traces", "logs"])
def test_forwards_traces_and_logs_to_the_collector(frontend, signal):
    fe = frontend(**ON)
    status, body = fe.post(f"/otel/v1/{signal}")
    assert status == 200
    assert f"uri=/v1/{signal}" in body


def test_strips_the_browsers_token_and_cookies(frontend):
    fe = frontend(**ON)
    _, body = fe.post("/otel/v1/traces", "-H 'Authorization: Bearer from-the-browser'", "-H 'Cookie: session=abc'")
    assert "auth=[]" in body
    assert "cookie=[]" in body


def test_adds_otlp_headers_on_the_server_side(frontend):
    fe = frontend(**ON, OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer%20s3cret,X-Extra=1")
    _, body = fe.post("/otel/v1/traces", "-H 'Authorization: Bearer from-the-browser'")
    assert "auth=[Bearer s3cret]" in body
    assert "s3cret" not in runtime_config(fe)


def test_rejects_headers_that_could_break_the_nginx_config(frontend):
    fe = frontend(**ON, OTEL_EXPORTER_OTLP_HEADERS='Authorization=Bearer";evil')
    assert '"enabled": false' in runtime_config(fe)
    assert "OTEL_EXPORTER_OTLP_HEADERS" in fe.logs()


def test_only_accepts_post(frontend):
    fe = frontend(**ON)
    status, body = fe.request("/otel/v1/traces")
    assert status == 403
    assert "auth=" not in body


def test_only_forwards_the_two_sdk_paths(frontend):
    fe = frontend(**ON)
    _, body = fe.post("/otel/v1/metrics")
    assert "auth=" not in body


def test_rejects_large_payloads(frontend):
    fe = frontend(**ON)
    fe.sh("head -c 2000000 /dev/zero > /tmp/big")
    status, _ = fe.request("/otel/v1/traces", "-X POST --data-binary @/tmp/big")
    assert status == 413


def test_rate_limits_floods(frontend):
    fe = frontend(**ON)
    codes = fe.sh(
        "for i in $(seq 1 150); do "
        "curl -s -o /dev/null -w '%{http_code}\\n' -X POST -d '{}' http://localhost/otel/v1/traces; "
        "done"
    ).split()
    assert "200" in codes
    assert "429" in codes
