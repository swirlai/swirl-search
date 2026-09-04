"""
Regression tests for the SWIRL for Backstage container entrypoint.

Defect: `docker compose restart` brought daphne and Redis back but not Celery,
so /swirl/sapi/health/backstage/ stayed on 503 forever. swirl.py writes ./.swirl
in the app directory and refuses to start a service named in it; that file lives
in the container's writable layer, which a restart keeps, so the second start
saw the previous run's pids and gave up:

    entrypoint: starting celery
      celery-worker is already running - remove .swirl if this is incorrect

The fix is docker/backstage/clear_stale_pids.sh, called by the entrypoint before
`swirl.py start`. These tests run that script for real against a throwaway
directory, and check the entrypoint calls it in the right place.

Run with: pytest swirl/tests/test_backstage_entrypoint.py -v
"""

import json
import os
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "docker", "backstage", "clear_stale_pids.sh")
ENTRYPOINT = os.path.join(ROOT, "docker", "backstage", "entrypoint.sh")


def run(app_dir):
    return subprocess.run(["sh", SCRIPT, str(app_dir)],
                          capture_output=True, text=True, timeout=30)


def test_the_script_ships_with_the_image():
    assert os.path.exists(SCRIPT)


def test_a_stale_swirl_pid_file_is_removed(tmp_path):
    """The exact state a restarted container is in: pids from the last run."""
    stale = tmp_path / ".swirl"
    stale.write_text(json.dumps({"celery-worker": 41, "celery-beats": 54}))

    result = run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert not stale.exists()
    assert ".swirl" in result.stdout


def test_a_stale_celerybeat_pid_file_is_removed(tmp_path):
    """celery beat refuses to start on its own leftover pid file."""
    stale = tmp_path / "celerybeat.pid"
    stale.write_text("54\n")

    result = run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert not stale.exists()


def test_a_live_pid_in_the_file_does_not_save_it(tmp_path):
    """A pid that names a live process is still cleared.

    Inside a container pids restart at 1 and are reused, so a pid written by
    the previous run very often names an unrelated live process in the next
    one. Validating liveness would keep the wedge rather than clear it, which
    is why the script does not.
    """
    stale = tmp_path / ".swirl"
    stale.write_text(json.dumps({"celery-worker": os.getpid()}))

    assert run(tmp_path).returncode == 0
    assert not stale.exists()


def test_nothing_to_clear_is_not_an_error(tmp_path):
    result = run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_a_missing_app_dir_is_not_an_error(tmp_path):
    result = run(tmp_path / "no-such-directory")
    assert result.returncode == 0, result.stderr


def test_the_entrypoint_clears_the_pid_state_before_starting_celery():
    with open(ENTRYPOINT, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "clear_stale_pids.sh" in body
    assert body.index("clear_stale_pids.sh") < body.index("swirl.py start"), (
        "the pid state has to be cleared before swirl.py start, or swirl.py "
        "refuses to start the worker")


def test_the_entrypoint_and_the_script_are_executable():
    assert os.access(ENTRYPOINT, os.X_OK)
    assert os.access(SCRIPT, os.X_OK)


# ---------------------------------------------------------------------------
# The Kubernetes manifest
#
# The image measures 2.48 GiB idle, so the 2Gi limit it shipped with was under
# the idle footprint and the pod was OOMKilled before it answered a query.
# ---------------------------------------------------------------------------

K8S = os.path.join(ROOT, "docker", "backstage", "k8s.yaml")


def _swirl_container():
    yaml = pytest.importorskip("yaml")
    with open(K8S, "r", encoding="utf-8") as handle:
        documents = list(yaml.safe_load_all(handle))
    deployments = [d for d in documents if d and d.get("kind") == "Deployment"]
    assert len(deployments) == 1, "expected one Deployment in k8s.yaml"
    return deployments[0]["spec"]["template"]["spec"]["containers"][0]


def _mebibytes(value):
    units = {"Ki": 1 / 1024.0, "Mi": 1.0, "Gi": 1024.0}
    for suffix, factor in units.items():
        if value.endswith(suffix):
            return float(value[:-len(suffix)]) * factor
    return float(value) / (1024.0 * 1024.0)


def test_the_memory_limit_is_above_the_measured_footprint():
    resources = _swirl_container()["resources"]
    assert resources["limits"]["memory"] == "3Gi"
    assert resources["requests"]["memory"] == "2.5Gi"
    # 2.64 GiB with the example catalog indexed is the number to clear.
    assert _mebibytes(resources["limits"]["memory"]) >= 2.64 * 1024
    assert (_mebibytes(resources["limits"]["memory"])
            >= _mebibytes(resources["requests"]["memory"]))


def test_the_manifest_points_at_the_deferred_slim_profile():
    with open(K8S, "r", encoding="utf-8") as handle:
        body = handle.read()
    assert "WP06b" in body
    assert "slim profile" in body


# ---------------------------------------------------------------------------
# The seed path the image actually uses
#
# Defect, found re-running the gauntlet against the released image: the
# provider-tag fix changed SearchProviders/*.json, but the container seeds
# /data/db.sqlite3 from the shipped db.sqlite3.dist, which is a binary artifact
# only .github/workflows/db-dist.yml regenerates. The shipped `Code - GitHub`
# row therefore still carried ["GitHub", "Code", "Dev"] and an unscoped
# template, so it could not join the federated lane whose default tag is
# `backstage`.
#
# The fix is reconciliation in docker/backstage/load_backstage_provider.py,
# which the entrypoint runs on every start. These tests drive that reconciler
# over the rows taken out of the real db.sqlite3.dist, which is the state a
# fresh container is in on its first boot.
# ---------------------------------------------------------------------------

import importlib.util
import sqlite3

import pytest

DIST_DB = os.path.join(ROOT, "db.sqlite3.dist")
PRELOADED = os.path.join(ROOT, "SearchProviders", "preloaded.json")

#: The six providers preloaded.json tags for the federated lane: four GitHub,
#: Confluence, and the Backstage index itself.
FEDERATED_NAMES = (
    "Code - GitHub",
    "Issues - GitHub",
    "PRs - GitHub",
    "Commits - GitHub",
    "Docs - Atlassian Confluence",
    "Backstage Index - SWIRL",
)

#: Columns of swirl_searchprovider that map onto model fields the reconciler
#: reads or writes.
SEEDED_COLUMNS = (
    "name", "active", "tags", "query_template", "query_template_json",
    "connector", "url", "shared",
)


def load_seeder():
    """Import the script the entrypoint runs, by path: it is not a package."""
    path = os.path.join(ROOT, "docker", "backstage", "load_backstage_provider.py")
    spec = importlib.util.spec_from_file_location("load_backstage_provider", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_from_dist(owner):
    """Recreate the shipped rows in the test database, verbatim from the dist.

    This is the whole point of the test: not a hand written fixture of what the
    dist is believed to hold, but what it actually holds today.
    """
    from swirl.models import SearchProvider

    connection = sqlite3.connect(DIST_DB)
    connection.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in FEDERATED_NAMES)
    rows = connection.execute(
        "select {} from swirl_searchprovider where name in ({})".format(
            ",".join(SEEDED_COLUMNS), placeholders), FEDERATED_NAMES).fetchall()
    connection.close()

    seeded = {}
    for row in rows:
        provider = SearchProvider.objects.create(
            owner=owner,
            name=row["name"],
            active=bool(row["active"]),
            shared=bool(row["shared"]),
            connector=row["connector"] or "RequestsGet",
            url=row["url"] or "",
            query_template=row["query_template"] or "",
            query_template_json=json.loads(row["query_template_json"] or "{}"),
            tags=json.loads(row["tags"] or "[]"),
        )
        seeded[provider.name] = provider
    return seeded


@pytest.fixture
def dist_owner(db):
    from django.contrib.auth.models import User

    user, _ = User.objects.get_or_create(username="dist_seed_owner")
    return user


def test_the_shipped_dist_database_is_the_state_the_reconciler_is_for():
    """Guard the premise. If a regenerated dist ships, this is what changes."""
    assert os.path.exists(DIST_DB), DIST_DB
    connection = sqlite3.connect(DIST_DB)
    row = connection.execute(
        "select tags from swirl_searchprovider where name = 'Code - GitHub'"
    ).fetchone()
    connection.close()
    assert row is not None, "Code - GitHub is missing from db.sqlite3.dist"
    # Either the dist is stale, which is what the reconciler repairs, or it has
    # been regenerated and already carries the tag. Both are acceptable; what
    # is not acceptable is the reconciler silently doing nothing in either case,
    # which the tests below check.
    assert isinstance(json.loads(row[0]), list)


@pytest.mark.django_db
def test_the_seed_path_gives_code_github_the_backstage_tag(dist_owner):
    from swirl.models import SearchProvider

    seed_from_dist(dist_owner)
    load_seeder().reconcile_federated_providers(PRELOADED)

    provider = SearchProvider.objects.get(name="Code - GitHub")
    assert "backstage" in provider.tags


@pytest.mark.django_db
def test_the_seed_path_leaves_code_github_inactive_and_scoped(dist_owner):
    from swirl.models import SearchProvider
    from swirl.scope import is_scoped

    seed_from_dist(dist_owner)
    load_seeder().reconcile_federated_providers(PRELOADED)

    provider = SearchProvider.objects.get(name="Code - GitHub")
    assert provider.active is False
    assert "repo:<your-org>/<your-repo>" in provider.query_template
    assert is_scoped(provider)


@pytest.mark.django_db
def test_the_seed_path_covers_every_federated_provider_it_finds(dist_owner):
    from swirl.models import SearchProvider

    seeded = seed_from_dist(dist_owner)
    load_seeder().reconcile_federated_providers(PRELOADED)

    for name in seeded:
        provider = SearchProvider.objects.get(name=name)
        assert "backstage" in provider.tags, name
        if provider.connector == "TantivyIndex":
            # The Backstage index provider is the indexed lane and ships active
            # in the image profile by design; only federated rows stay inactive
            # until an operator scopes them.
            continue
        assert provider.active is False, name


@pytest.mark.django_db
def test_the_seed_path_keeps_the_tags_the_row_already_had(dist_owner):
    """Galaxy filters on the old tags; the new one is added, not swapped in."""
    from swirl.models import SearchProvider

    seeded = seed_from_dist(dist_owner)
    before = {name: set(provider.tags) for name, provider in seeded.items()}
    load_seeder().reconcile_federated_providers(PRELOADED)

    for name, tags in before.items():
        provider = SearchProvider.objects.get(name=name)
        assert tags <= set(provider.tags), name


@pytest.mark.django_db
def test_the_seed_path_is_idempotent(dist_owner):
    from swirl.models import SearchProvider

    seed_from_dist(dist_owner)
    seeder = load_seeder()
    seeder.reconcile_federated_providers(PRELOADED)
    first = {p.name: (p.tags, p.query_template)
             for p in SearchProvider.objects.all()}

    assert seeder.reconcile_federated_providers(PRELOADED) == []

    second = {p.name: (p.tags, p.query_template)
              for p in SearchProvider.objects.all()}
    assert first == second


@pytest.mark.django_db
def test_the_seed_path_does_not_undo_an_operator_scope(dist_owner):
    """An operator who filled in their repo and switched it on keeps it."""
    from swirl.models import SearchProvider

    seed_from_dist(dist_owner)
    provider = SearchProvider.objects.get(name="Code - GitHub")
    provider.query_template = "{url}?q={query_string}+repo:acme/widgets"
    provider.active = True
    provider.save()

    load_seeder().reconcile_federated_providers(PRELOADED)

    provider.refresh_from_db()
    assert provider.query_template == "{url}?q={query_string}+repo:acme/widgets"
    assert provider.active is True
    assert "backstage" in provider.tags


@pytest.mark.django_db
def test_the_seed_path_does_not_recreate_a_deleted_provider(dist_owner):
    from swirl.models import SearchProvider

    seed_from_dist(dist_owner)
    SearchProvider.objects.filter(name="Commits - GitHub").delete()

    load_seeder().reconcile_federated_providers(PRELOADED)

    assert not SearchProvider.objects.filter(name="Commits - GitHub").exists()


def test_the_entrypoint_runs_the_provider_loader_before_starting_celery():
    body = open(ENTRYPOINT).read()
    assert "load_backstage_provider.py" in body
    assert body.index("load_backstage_provider.py") < body.index("swirl.py start")
