"""
Unit tests for the Backstage health endpoint (WP06).

Design: TECH_DESIGN_swirl_for_backstage.md section 3.7.

Run with: pytest swirl/tests/test_health_backstage.py -v
"""

import pytest

from rest_framework.test import APIClient

from swirl import views_health

URL = "/swirl/sapi/health/backstage/"


@pytest.fixture
def healthy(monkeypatch, tmp_path, settings):
    """Every dependency reports ok."""
    monkeypatch.setattr(views_health, "check_redis",
                        lambda: {"ok": True, "url": "redis://localhost:6379/0"})
    monkeypatch.setattr(views_health, "check_celery",
                        lambda: {"ok": True, "workers": ["celery@container"]})
    monkeypatch.setattr(views_health, "check_tantivy",
                        lambda: {"ok": True, "types": ["software-catalog"]})


# ---------------------------------------------------------------------------
# The endpoint
# ---------------------------------------------------------------------------

def test_health_is_reachable_without_authentication(healthy):
    response = APIClient().get(URL)
    assert response.status_code == 200
    assert response.data["ok"] is True


def test_health_body_shape(healthy):
    body = APIClient().get(URL).data
    assert set(body) == {"ok", "redis", "celery_search_worker", "tantivy", "license"}
    assert body["redis"]["ok"] is True
    assert body["celery_search_worker"]["workers"] == ["celery@container"]
    assert body["tantivy"]["types"] == ["software-catalog"]
    assert body["license"] == {"edition": "community", "backstage": True}


@pytest.mark.parametrize("broken", ["check_redis", "check_celery", "check_tantivy"])
def test_a_broken_dependency_makes_it_not_ok_and_503(healthy, monkeypatch, broken):
    monkeypatch.setattr(views_health, broken,
                        lambda: {"ok": False, "error": "boom"})
    response = APIClient().get(URL)
    assert response.status_code == 503
    assert response.data["ok"] is False


def test_the_body_carries_no_secret(healthy, monkeypatch, settings):
    settings.CELERY_BROKER_URL = "redis://someuser:supersecret@redis:6379/0"
    monkeypatch.undo()
    monkeypatch.setattr(views_health, "check_celery",
                        lambda: {"ok": True, "workers": []})
    monkeypatch.setattr(views_health, "check_tantivy",
                        lambda: {"ok": True, "types": []})
    body = APIClient().get(URL).data
    assert "supersecret" not in str(body)


# ---------------------------------------------------------------------------
# The individual checks
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url,expected", [
    ("redis://localhost:6379/0", "redis://localhost:6379/0"),
    ("redis://user:pw@redis:6379/1", "redis://user:***@redis:6379/1"),
    ("rediss://:pw@redis:6380/0", "rediss://redis:6380/0"),
    ("", ""),
])
def test_redact_url(url, expected):
    assert views_health.redact_url(url) == expected


def test_check_redis_reports_the_failure_without_raising(settings):
    settings.CELERY_BROKER_URL = "redis://127.0.0.1:6399/0"
    row = views_health.check_redis()
    assert row["ok"] is False
    assert "error" in row
    assert row["url"] == "redis://127.0.0.1:6399/0"


def test_check_tantivy_lists_the_live_types(settings, tmp_path, monkeypatch):
    pytest.importorskip("tantivy", reason="tantivy is not installed")
    from swirl.tantivy_index import manager as manager_module
    from swirl.tantivy_index.manager import TantivyIndexManager

    settings.SWIRL_TANTIVY_DATA_DIR = str(tmp_path / "tantivy")
    settings.SWIRL_TANTIVY_WRITER_HEAP_MB = 15
    instance = TantivyIndexManager()
    monkeypatch.setattr(manager_module, "default_manager", instance)

    assert views_health.check_tantivy() == {"ok": True, "types": []}

    generation = instance.begin("software-catalog")
    instance.add("software-catalog", generation, [
        {"title": "alpha", "text": "a component", "location": "/catalog/alpha"}])
    instance.finalize("software-catalog", generation)
    row = views_health.check_tantivy()
    assert row["ok"] is True
    assert row["types"] == ["software-catalog"]


def test_check_celery_reports_no_workers_without_raising(monkeypatch):
    class _Control:
        @staticmethod
        def ping(timeout=None):
            return []

    class _App:
        control = _Control()

    import swirl_server.celery as celery_module
    monkeypatch.setattr(celery_module, "app", _App())
    row = views_health.check_celery()
    assert row["ok"] is False
    assert row["workers"] == []


def test_check_celery_lists_the_workers(monkeypatch):
    class _Control:
        @staticmethod
        def ping(timeout=None):
            return [{"celery@one": {"ok": "pong"}}, {"celery@two": {"ok": "pong"}}]

    class _App:
        control = _Control()

    import swirl_server.celery as celery_module
    monkeypatch.setattr(celery_module, "app", _App())
    row = views_health.check_celery()
    assert row["ok"] is True
    assert row["workers"] == ["celery@one", "celery@two"]


# ---------------------------------------------------------------------------
# The backstage image profile (TECH_DESIGN section 3.8)
# ---------------------------------------------------------------------------

import os                                                        # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(*parts):
    with open(os.path.join(REPO_ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_the_profile_files_exist():
    for relative in (
            ("docker", "backstage", "entrypoint.sh"),
            ("docker", "backstage", "compose.yaml"),
            ("docker", "backstage", "k8s.yaml"),
            ("docker", "backstage", "load_backstage_provider.py"),
            (".env.backstage.dist",),
    ):
        assert os.path.exists(os.path.join(REPO_ROOT, *relative)), relative


def test_the_entrypoint_is_executable():
    path = os.path.join(REPO_ROOT, "docker", "backstage", "entrypoint.sh")
    assert os.access(path, os.X_OK)


def test_the_dockerfile_takes_the_profile_build_arg():
    dockerfile = read("Dockerfile")
    assert "ARG SWIRL_PROFILE=full" in dockerfile
    assert 'if [ "$SWIRL_PROFILE" = "backstage" ]' in dockerfile
    assert "en_core_web_sm" in dockerfile
    assert "en_core_web_lg" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "/swirl/sapi/health/backstage/" in dockerfile


def test_the_backstage_env_points_everything_at_the_volume():
    env = read(".env.backstage.dist")
    assert "SQL_DATABASE=/data/db.sqlite3" in env
    assert "SWIRL_TANTIVY_DATA_DIR=/data/tantivy" in env
    assert "redis://127.0.0.1:6379/0" in env
    assert "SWIRL_SPACY_MODEL_EN=en_core_web_sm" in env


def test_compose_declares_one_service_and_one_volume():
    compose = read("docker", "backstage", "compose.yaml")
    assert "swirl-data:/data" in compose
    assert "/swirl/sapi/health/backstage/" in compose
    # One service only: the whole point of the profile.
    assert compose.count("\n  swirl:\n") == 1
    assert "redis:\n    image:" not in compose


def test_the_entrypoint_only_starts_redis_when_the_broker_is_local():
    entrypoint = read("docker", "backstage", "entrypoint.sh")
    assert "broker_is_local" in entrypoint
    assert "redis-server --save 60 1" in entrypoint
    assert "exec daphne" in entrypoint
    assert "load_backstage_provider.py" in entrypoint


def test_the_health_path_is_exempt_from_token_middleware():
    from swirl.middleware import SWIRL_API_ANONYMOUS_URLS

    assert URL in SWIRL_API_ANONYMOUS_URLS
    assert "/api" + URL in SWIRL_API_ANONYMOUS_URLS
