"""Tests for set-image-tag.sh, which CI uses to deploy a new image (#70).

Runs the script with mikefarah yq v4 and GNU diff/patch, as on GitHub's
runners, in a small image built from the official yq image.
Run from the repo root:  uvx pytest deploy/scripts/tests
Needs Docker.
"""

import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
YQ_IMAGE = "mikefarah/yq:4.54.1"
TEST_IMAGE = "byteorder-set-image-tag-test"
DOCKERFILE = f"""\
FROM {YQ_IMAGE}
USER root
RUN apk add --no-cache diffutils patch
"""


@pytest.fixture(scope="session", autouse=True)
def test_image():
    subprocess.run(
        ["docker", "build", "-q", "-t", TEST_IMAGE, "-"],
        input=DOCKERFILE, text=True, check=True, capture_output=True,
    )

VALUES = """\
registry: ghcr.io/matts-baps/byteorder

# Database on the CNPG cluster.
postgres:
  enabled: false   # keep this comment
"""


def run(values: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "docker", "run", "--rm", "--user", f"{_uid()}",
            "-v", f"{SCRIPTS}:/scripts:ro",
            "-v", f"{values.parent}:/work",
            "--entrypoint", "sh", TEST_IMAGE,
            "/scripts/set-image-tag.sh", f"/work/{values.name}", *args,
        ],
        capture_output=True, text=True,
    )


def _uid() -> str:
    import os
    return f"{os.getuid()}:{os.getgid()}"


def yq(values: Path, expr: str) -> str:
    result = subprocess.run(
        ["docker", "run", "--rm", "--user", _uid(), "-v", f"{values.parent}:/work", YQ_IMAGE, expr, f"/work/{values.name}"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def values(tmp_path):
    path = tmp_path / "values.yaml"
    path.write_text(VALUES)
    return path


def test_adds_a_tag_for_a_service(values):
    result = run(values, "frontend", "sha-4194200")
    assert result.returncode == 0, result.stderr
    assert yq(values, '.images.frontend.tag') == "sha-4194200"


def test_handles_service_names_with_hyphens(values):
    assert run(values, "menu-service", "sha-abcdef0").returncode == 0
    assert yq(values, '.images["menu-service"].tag') == "sha-abcdef0"


def test_updates_one_service_and_leaves_the_others(values):
    run(values, "frontend", "sha-1111111")
    run(values, "admin", "sha-2222222")
    run(values, "frontend", "sha-3333333")
    assert yq(values, '.images.frontend.tag') == "sha-3333333"
    assert yq(values, '.images.admin.tag') == "sha-2222222"


def test_keeps_the_rest_of_the_file_and_its_comments(values):
    run(values, "frontend", "sha-4194200")
    text = values.read_text()
    assert "# Database on the CNPG cluster." in text
    assert "# keep this comment" in text
    assert yq(values, '.registry') == "ghcr.io/matts-baps/byteorder"


def test_keeps_blank_lines(values):
    run(values, "frontend", "sha-4194200")
    run(values, "frontend", "sha-1234567")
    lines = values.read_text().splitlines()
    assert lines[1] == ""
    assert lines[:5] == VALUES.splitlines()[:5]


def test_reports_when_nothing_changed(values):
    run(values, "frontend", "sha-4194200")
    before = values.read_text()
    result = run(values, "frontend", "sha-4194200")
    assert result.returncode == 0
    assert "unchanged" in result.stdout
    assert values.read_text() == before


@pytest.mark.parametrize(
    "service, tag",
    [
        ("frontend", "latest; rm -rf /"),
        ("frontend", ""),
        ("Frontend", "sha-4194200"),
        ("../frontend", "sha-4194200"),
        ("frontend", "sha-xyz"),
    ],
    ids=["injected-tag", "empty-tag", "uppercase-service", "path-service", "non-hex-sha"],
)
def test_rejects_bad_input(values, service, tag):
    before = values.read_text()
    result = run(values, service, tag)
    assert result.returncode != 0
    assert values.read_text() == before


def test_rejects_a_missing_file(tmp_path):
    result = run(tmp_path / "missing.yaml", "frontend", "sha-4194200")
    assert result.returncode != 0
