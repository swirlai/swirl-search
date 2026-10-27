"""
Unit tests for the Backstage ingest API, swirl/views_index.py (WP02).

Design: TECH_DESIGN_swirl_for_backstage.md section 3.2.

Covers the full lifecycle (config, begin, docs, finalize, list, abort, delete),
that a zero-document finalize answers 400 and keeps the live generation, that a
bad document is rejected with its index and nothing is written, that anonymous
and unprivileged callers are refused, that a second begin answers 409, and the
type-name validation.

The manager is pointed at a tmp_path data directory through the
SWIRL_TANTIVY_DATA_DIR setting, so no test touches the real index.

Run with: pytest swirl/tests/test_views_index.py -v
"""

import pytest

tantivy = pytest.importorskip("tantivy", reason="tantivy is not installed")

from django.contrib.auth.models import Permission, User      # noqa: E402
from django.contrib.contenttypes.models import ContentType   # noqa: E402
from rest_framework.test import APIClient                    # noqa: E402

from swirl.models import SearchIndexGeneration, SearchProvider  # noqa: E402
from swirl.tantivy_index import generations as gen           # noqa: E402
from swirl.tantivy_index.manager import TantivyIndexManager  # noqa: E402

TYPE = "software-catalog"
BASE = "/swirl/index/"


def doc(name, **extra):
    payload = {
        "title": name,
        "text": "The {} component of the platform.".format(name),
        "location": "/catalog/default/component/{}".format(name),
        "kind": "Component",
    }
    payload.update(extra)
    return payload


@pytest.fixture
def data_dir(tmp_path, settings, monkeypatch):
    """Point the process wide manager at a throwaway directory."""
    from swirl.tantivy_index import manager as manager_module

    directory = str(tmp_path / "tantivy")
    settings.SWIRL_TANTIVY_DATA_DIR = directory
    settings.SWIRL_TANTIVY_WRITER_HEAP_MB = 15
    settings.SWIRL_TANTIVY_BEGIN_TTL = 3600
    monkeypatch.setattr(manager_module, "default_manager", TantivyIndexManager())
    import swirl.views_index as views_index
    monkeypatch.setattr(views_index, "default_manager",
                        manager_module.default_manager, raising=False)
    return directory


@pytest.fixture
def indexer(db):
    """A user with swirl.change_searchprovider, the ingest permission."""
    user, _ = User.objects.get_or_create(username="backstage_indexer")
    user.user_permissions.add(Permission.objects.get(
        codename="change_searchprovider",
        content_type=ContentType.objects.get_for_model(SearchProvider)))
    return User.objects.get(pk=user.pk)


@pytest.fixture
def reader(db):
    """An authenticated user with no ingest permission."""
    user, _ = User.objects.get_or_create(username="backstage_reader")
    return user


@pytest.fixture
def client(indexer, data_dir):
    api = APIClient()
    api.force_authenticate(user=indexer)
    return api


@pytest.fixture
def anon(data_dir):
    return APIClient()


def begin(client, type_name=TYPE):
    response = client.post("{}{}/begin/".format(BASE, type_name), {}, format="json")
    assert response.status_code == 201, response.data
    return response.data["generation"]


# ---------------------------------------------------------------------------
# The full lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_full_lifecycle(client, data_dir):
    generation = begin(client)
    assert gen.GENERATION_RE.match(generation)
    row = SearchIndexGeneration.objects.get(type=TYPE, generation=generation)
    assert row.state == SearchIndexGeneration.STATE_OPEN
    assert row.started_by.username == "backstage_indexer"

    docs = client.post(
        "{}{}/{}/docs/".format(BASE, TYPE, generation),
        {"documents": [doc("petstore"), doc("wayback-search")]}, format="json")
    assert docs.status_code == 202, docs.data
    assert docs.data["accepted"] == 2
    assert docs.data["generation"] == generation
    assert SearchIndexGeneration.objects.get(
        type=TYPE, generation=generation).doc_count == 2

    final = client.post("{}{}/{}/finalize/".format(BASE, TYPE, generation),
                        {}, format="json")
    assert final.status_code == 200, final.data
    assert final.data["live"] == generation
    assert final.data["count"] == 2
    assert final.data["bytes"] > 0
    row = SearchIndexGeneration.objects.get(type=TYPE, generation=generation)
    assert row.state == SearchIndexGeneration.STATE_LIVE
    assert row.finalized_at is not None
    assert row.doc_count == 2

    listing = client.get(BASE)
    assert listing.status_code == 200
    rows = {entry["type"]: entry for entry in listing.data["types"]}
    assert rows[TYPE]["live"] == generation
    assert rows[TYPE]["doc_count"] == 2
    assert rows[TYPE]["bytes"] > 0
    assert rows[TYPE]["open"] is None

    # The documents are searchable through the manager.
    from swirl.tantivy_index.manager import default_manager
    hits = default_manager.search(types=[TYPE], term="petstore")
    assert [hit["title"] for hit in hits] == ["petstore"]

    assert client.delete("{}{}/".format(BASE, TYPE)).status_code == 204
    assert client.get(BASE).data["types"] == []
    assert SearchIndexGeneration.objects.filter(type=TYPE).count() == 0


@pytest.mark.django_db
def test_a_second_generation_replaces_the_first(client):
    first = begin(client)
    client.post("{}{}/{}/docs/".format(BASE, TYPE, first),
                {"documents": [doc("alpha")]}, format="json")
    client.post("{}{}/{}/finalize/".format(BASE, TYPE, first), {}, format="json")

    second = begin(client)
    client.post("{}{}/{}/docs/".format(BASE, TYPE, second),
                {"documents": [doc("beta")]}, format="json")
    client.post("{}{}/{}/finalize/".format(BASE, TYPE, second), {}, format="json")

    assert SearchIndexGeneration.objects.get(
        type=TYPE, generation=first).state == SearchIndexGeneration.STATE_RETIRED
    assert SearchIndexGeneration.objects.get(
        type=TYPE, generation=second).state == SearchIndexGeneration.STATE_LIVE

    from swirl.tantivy_index.manager import default_manager
    assert [hit["title"] for hit in default_manager.search(types=[TYPE], term="beta")]
    assert default_manager.search(types=[TYPE], term="alpha") == []


# ---------------------------------------------------------------------------
# begin
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_a_second_begin_is_409(client):
    first = begin(client)
    second = client.post("{}{}/begin/".format(BASE, TYPE), {}, format="json")
    assert second.status_code == 409
    assert second.data["generation"] == first
    assert "already open" in second.data["detail"]


@pytest.mark.django_db
def test_begin_after_abort_succeeds(client):
    first = begin(client)
    assert client.post("{}{}/{}/abort/".format(BASE, TYPE, first),
                       {}, format="json").status_code == 204
    assert begin(client) != first


@pytest.mark.django_db
@pytest.mark.parametrize("bad", ["Software", "soft_ware", "soft.ware", "x" * 65])
def test_begin_rejects_a_bad_type_name(client, bad):
    response = client.post("{}{}/begin/".format(BASE, bad), {}, format="json")
    assert response.status_code == 400
    assert "type name must match" in response.data["detail"]


@pytest.mark.django_db
def test_type_names_are_validated_on_every_endpoint(client):
    bad = "Bad_Name"
    assert client.post("{}{}/begin/".format(BASE, bad), {},
                       format="json").status_code == 400
    assert client.post("{}{}/20200101T000000-000000/docs/".format(BASE, bad),
                       {"documents": []}, format="json").status_code == 400
    assert client.post("{}{}/20200101T000000-000000/finalize/".format(BASE, bad),
                       {}, format="json").status_code == 400
    assert client.post("{}{}/20200101T000000-000000/abort/".format(BASE, bad),
                       {}, format="json").status_code == 400
    assert client.delete("{}{}/".format(BASE, bad)).status_code == 400


# ---------------------------------------------------------------------------
# docs
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_a_bad_document_is_rejected_with_its_index(client, data_dir):
    generation = begin(client)
    response = client.post(
        "{}{}/{}/docs/".format(BASE, TYPE, generation),
        {"documents": [doc("good"), {"title": "no text", "location": "/x"}]},
        format="json")
    assert response.status_code == 400
    assert "index 1" in response.data["detail"]
    assert 'missing the required field "text"' in response.data["detail"]
    # Nothing was written: the whole batch is refused.
    assert SearchIndexGeneration.objects.get(
        type=TYPE, generation=generation).doc_count == 0
    from swirl.tantivy_index.manager import default_manager
    assert default_manager._read_count(
        gen.generation_dir(data_dir, TYPE, generation)) == 0


@pytest.mark.django_db
@pytest.mark.parametrize("body,fragment", [
    ({}, 'must carry a "documents" list'),
    ({"documents": "nope"}, '"documents" must be a list'),
    ({"documents": ["a string"]}, "is not an object"),
])
def test_malformed_docs_bodies_are_400(client, body, fragment):
    generation = begin(client)
    response = client.post("{}{}/{}/docs/".format(BASE, TYPE, generation),
                           body, format="json")
    assert response.status_code == 400
    assert fragment in response.data["detail"]


@pytest.mark.django_db
def test_a_batch_over_the_limit_is_400(client):
    generation = begin(client)
    response = client.post(
        "{}{}/{}/docs/".format(BASE, TYPE, generation),
        {"documents": [doc("d{}".format(i)) for i in range(1001)]}, format="json")
    assert response.status_code == 400
    assert "1000" in response.data["detail"]


@pytest.mark.django_db
def test_an_empty_batch_is_accepted(client):
    generation = begin(client)
    response = client.post("{}{}/{}/docs/".format(BASE, TYPE, generation),
                           {"documents": []}, format="json")
    assert response.status_code == 202
    assert response.data["accepted"] == 0


@pytest.mark.django_db
def test_docs_to_an_unknown_generation_is_404(client):
    begin(client)
    response = client.post(
        "{}{}/20200101T000000-000000/docs/".format(BASE, TYPE),
        {"documents": [doc("alpha")]}, format="json")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# finalize
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_zero_document_finalize_is_400_and_keeps_the_live_generation(
        client, data_dir):
    first = begin(client)
    client.post("{}{}/{}/docs/".format(BASE, TYPE, first),
                {"documents": [doc("alpha")]}, format="json")
    client.post("{}{}/{}/finalize/".format(BASE, TYPE, first), {}, format="json")

    second = begin(client)
    response = client.post("{}{}/{}/finalize/".format(BASE, TYPE, second),
                           {}, format="json")
    assert response.status_code == 400
    assert "no documents" in response.data["detail"]
    assert gen.live_generation(data_dir, TYPE) == first
    assert client.get(BASE).data["types"][0]["live"] == first
    assert SearchIndexGeneration.objects.get(
        type=TYPE, generation=second).state == SearchIndexGeneration.STATE_OPEN
    # The empty generation can still be filled and finalized.
    client.post("{}{}/{}/docs/".format(BASE, TYPE, second),
                {"documents": [doc("beta")]}, format="json")
    assert client.post("{}{}/{}/finalize/".format(BASE, TYPE, second),
                       {}, format="json").status_code == 200


@pytest.mark.django_db
def test_finalize_of_an_unknown_generation_is_404(client):
    begin(client)
    assert client.post(
        "{}{}/20200101T000000-000000/finalize/".format(BASE, TYPE),
        {}, format="json").status_code == 404


# ---------------------------------------------------------------------------
# abort and delete
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_abort_keeps_the_live_generation(client, data_dir):
    first = begin(client)
    client.post("{}{}/{}/docs/".format(BASE, TYPE, first),
                {"documents": [doc("alpha")]}, format="json")
    client.post("{}{}/{}/finalize/".format(BASE, TYPE, first), {}, format="json")

    second = begin(client)
    client.post("{}{}/{}/docs/".format(BASE, TYPE, second),
                {"documents": [doc("beta")]}, format="json")
    assert client.post("{}{}/{}/abort/".format(BASE, TYPE, second),
                       {}, format="json").status_code == 204
    assert gen.live_generation(data_dir, TYPE) == first
    assert SearchIndexGeneration.objects.get(
        type=TYPE, generation=second).state == SearchIndexGeneration.STATE_ABORTED


@pytest.mark.django_db
def test_abort_of_the_live_generation_is_400(client):
    generation = begin(client)
    client.post("{}{}/{}/docs/".format(BASE, TYPE, generation),
                {"documents": [doc("alpha")]}, format="json")
    client.post("{}{}/{}/finalize/".format(BASE, TYPE, generation), {}, format="json")
    response = client.post("{}{}/{}/abort/".format(BASE, TYPE, generation),
                           {}, format="json")
    assert response.status_code == 400
    assert "refusing to abort the live generation" in response.data["detail"]


@pytest.mark.django_db
def test_delete_of_an_unknown_type_is_404(client):
    assert client.delete("{}nothing-here/".format(BASE)).status_code == 404


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_config_returns_the_effective_tuning(client):
    response = client.post(BASE + "config/", {"text_boost": 2.0}, format="json")
    assert response.status_code == 200
    assert response.data["text_boost"] == 2.0
    assert response.data["title_exact_boost"] == 3.0
    assert client.get(BASE + "config/").data["text_boost"] == 2.0


@pytest.mark.django_db
def test_config_rejects_a_bad_tuning_block(client):
    response = client.post(BASE + "config/", {"ngram_max": 99}, format="json")
    assert response.status_code == 400
    assert "ngram_max" in response.data["detail"]


@pytest.mark.django_db
def test_config_rejects_unknown_keys_instead_of_dropping_them(client):
    """Contract change: silently dropping keys is how a whole tuning block
    could be configured and do nothing. An unknown key is now a 400 naming it.
    """
    response = client.post(BASE + "config/", {"nonsense": 1}, format="json")
    assert response.status_code == 400
    assert "nonsense" in response.data["detail"]
    assert "unknown tuning key" in response.data["detail"]


@pytest.mark.django_db
def test_config_names_an_unknown_key_inside_a_nested_block(client):
    response = client.post(BASE + "config/", {"fuzzy": {"bogus": 1}},
                           format="json")
    assert response.status_code == 400
    assert "fuzzy.bogus" in response.data["detail"]


@pytest.mark.django_db
def test_config_accepts_the_nested_backstage_tuning_block(client):
    """The shape the engine module sends verbatim out of app-config."""
    response = client.post(BASE + "config/", {
        "fieldBoosts": {"titleExact": 5, "titleNgram": 2, "text": 1.5},
        "ngram": {"min": 2, "max": 6},
        "stemmer": "english",
        "stopwords": ["platform"],
        "fuzzy": {"enabled": True, "distance": 2},
        "bm25": {"k1": 1.5, "b": 0.6},
        "highlight": {"enabled": True, "maxChars": 120},
    }, format="json")

    assert response.status_code == 200, response.data
    # The response is SWIRL's flat form.
    assert response.data["title_exact_boost"] == 5.0
    assert response.data["title_ngram_boost"] == 2.0
    assert response.data["text_boost"] == 1.5
    assert response.data["ngram_min"] == 2
    assert response.data["ngram_max"] == 6
    assert response.data["extra_stopwords"] == ["platform"]
    assert response.data["fuzzy_enabled"] is True
    assert response.data["fuzzy_distance"] == 2
    assert response.data["snippet_chars"] == 120
    assert response.data["bm25_k1"] == 1.5
    assert response.data["bm25_b"] == 0.6
    # ...and it says what it took, in the shape it was sent.
    assert "fuzzy.enabled" in response.data["accepted_keys"]
    assert "fieldBoosts.titleExact" in response.data["accepted_keys"]
    assert "highlight.maxChars" in response.data["accepted_keys"]
    # It persists.
    assert client.get(BASE + "config/").data["fuzzy_enabled"] is True


@pytest.mark.django_db
def test_config_still_accepts_the_flat_swirl_tuning_block(client):
    response = client.post(BASE + "config/",
                           {"fuzzy_enabled": True, "text_boost": 2.0},
                           format="json")
    assert response.status_code == 200, response.data
    assert response.data["fuzzy_enabled"] is True
    assert response.data["text_boost"] == 2.0
    assert sorted(response.data["accepted_keys"]) == ["fuzzy_enabled",
                                                      "text_boost"]


@pytest.mark.django_db
def test_config_reports_that_bm25_is_not_applied(client):
    """tantivy-py exposes no BM25 knobs, so the values are stored and said so."""
    from swirl.tantivy_index.tuning import BM25_NOT_APPLIED, bm25_supported

    response = client.post(BASE + "config/", {"bm25": {"k1": 1.4, "b": 0.5}},
                           format="json")
    assert response.status_code == 200, response.data
    assert response.data["bm25_k1"] == 1.4
    assert response.data["bm25_b"] == 0.5
    if bm25_supported():
        assert "bm25" not in response.data
    else:
        assert response.data["bm25"] == BM25_NOT_APPLIED


@pytest.mark.django_db
def test_config_says_nothing_about_bm25_when_it_was_not_asked_for(client):
    response = client.post(BASE + "config/", {"text_boost": 2.0}, format="json")
    assert response.status_code == 200
    assert "bm25" not in response.data


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize("method,path,body", [
    ("get", BASE, None),
    ("post", BASE + "config/", {}),
    ("post", BASE + TYPE + "/begin/", {}),
    ("post", BASE + TYPE + "/20200101T000000-000000/docs/", {"documents": []}),
    ("post", BASE + TYPE + "/20200101T000000-000000/finalize/", {}),
    ("post", BASE + TYPE + "/20200101T000000-000000/abort/", {}),
    ("delete", BASE + TYPE + "/", None),
])
def test_anonymous_is_refused_on_every_endpoint(anon, method, path, body):
    call = getattr(anon, method)
    response = call(path, body, format="json") if body is not None else call(path)
    assert response.status_code in (401, 403), (path, response.status_code)


@pytest.mark.django_db
def test_an_authenticated_user_without_the_permission_is_403(reader, data_dir):
    api = APIClient()
    api.force_authenticate(user=reader)
    response = api.post("{}{}/begin/".format(BASE, TYPE), {}, format="json")
    assert response.status_code == 403
    assert "swirl.change_searchprovider" in response.data["detail"]
    assert api.get(BASE).status_code == 403


@pytest.mark.django_db
def test_the_permission_is_change_searchprovider(indexer):
    assert indexer.has_perm("swirl.change_searchprovider")


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_the_generation_admin_is_read_only():
    from django.contrib import admin as django_admin

    from swirl.admin import SearchIndexGenerationAdmin

    model_admin = django_admin.site._registry[SearchIndexGeneration]
    assert isinstance(model_admin, SearchIndexGenerationAdmin)
    assert model_admin.has_add_permission(None) is False
    assert model_admin.has_change_permission(None) is False
    assert "abort_open_generations" in model_admin.actions


@pytest.mark.django_db
def test_the_generation_admin_size_is_human_readable():
    from django.contrib import admin as django_admin

    model_admin = django_admin.site._registry[SearchIndexGeneration]
    assert model_admin.size(SearchIndexGeneration(bytes=0)) == "0 B"
    assert model_admin.size(SearchIndexGeneration(bytes=2048)) == "2.0 KB"
    assert model_admin.size(SearchIndexGeneration(bytes=3 * 1024 * 1024)) == "3.0 MB"


# ---------------------------------------------------------------------------
# Concurrent begin
#
# Defect: two collators calling POST /swirl/index/<type>/begin/ in the same
# instant both created a generation directory, and the loser died with
# sqlite3.OperationalError "database is locked" out of the bookkeeping write
# after the directory and the OPEN lock were already on disk. The type was then
# wedged: every later begin answered 409 until the two hour TTL expired.
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_two_simultaneous_begins_do_not_wedge_the_type(indexer, data_dir):
    """One 201, one 409, no 500, and the type still works afterwards."""
    import threading

    from django.db import connection

    barrier = threading.Barrier(2)
    outcomes = {}

    def call(name):
        api = APIClient()
        api.force_authenticate(user=indexer)
        try:
            barrier.wait(timeout=30)
            response = api.post("{}{}/begin/".format(BASE, TYPE), {},
                                format="json")
            outcomes[name] = (response.status_code, response.data)
        except Exception as err:                     # noqa: BLE001
            outcomes[name] = ("raised", repr(err))
        finally:
            connection.close()

    threads = [threading.Thread(target=call, args=(name,))
               for name in ("first", "second")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
        assert not thread.is_alive(), "a begin thread hung"

    codes = sorted(str(code) for code, _ in outcomes.values())
    assert "500" not in codes, outcomes
    assert "raised" not in codes, outcomes
    assert codes.count("201") == 1, outcomes
    assert codes == ["201", "409"], outcomes

    winner = [payload["generation"] for code, payload in outcomes.values()
              if code == 201][0]

    # Exactly one generation directory exists, and it is the one that won.
    assert gen.generations(data_dir, TYPE) == [winner]
    assert gen.open_generation(data_dir, TYPE) == winner
    assert SearchIndexGeneration.objects.filter(type=TYPE).count() == 1
    assert SearchIndexGeneration.objects.get(
        type=TYPE, generation=winner).state == SearchIndexGeneration.STATE_OPEN

    # The type is not wedged: finish the winner and a new begin is accepted.
    api = APIClient()
    api.force_authenticate(user=indexer)
    assert api.post("{}{}/{}/docs/".format(BASE, TYPE, winner),
                    {"documents": [doc("petstore")]},
                    format="json").status_code == 202
    assert api.post("{}{}/{}/finalize/".format(BASE, TYPE, winner), {},
                    format="json").status_code == 200
    again = api.post("{}{}/begin/".format(BASE, TYPE), {}, format="json")
    assert again.status_code == 201, again.data
    assert again.data["generation"] != winner


@pytest.mark.django_db
def test_a_locked_database_is_retried_and_the_begin_succeeds(client, monkeypatch):
    """A transient "database is locked" does not fail the begin."""
    from django.db import OperationalError

    real = SearchIndexGeneration.objects.update_or_create
    attempts = []

    def flaky(*args, **kwargs):
        attempts.append(1)
        if len(attempts) < 3:
            raise OperationalError("database is locked")
        return real(*args, **kwargs)

    monkeypatch.setattr(SearchIndexGeneration.objects, "update_or_create", flaky)

    response = client.post("{}{}/begin/".format(BASE, TYPE), {}, format="json")

    assert response.status_code == 201, response.data
    assert len(attempts) == 3
    assert SearchIndexGeneration.objects.filter(
        type=TYPE, generation=response.data["generation"]).exists()


@pytest.mark.django_db
def test_a_begin_that_cannot_be_recorded_rolls_the_generation_back(
        client, data_dir, monkeypatch):
    """The failure mode that used to wedge the type leaves nothing behind."""
    from django.db import OperationalError

    def always_locked(*args, **kwargs):
        raise OperationalError("database is locked")

    monkeypatch.setattr(SearchIndexGeneration.objects, "update_or_create",
                        always_locked)

    response = client.post("{}{}/begin/".format(BASE, TYPE), {}, format="json")

    assert response.status_code == 503, response.data
    assert "rolled back" in response.data["detail"]
    # Nothing of the half-done begin survives: no lock, no directory, no row.
    assert gen.read_open(data_dir, TYPE) is None
    assert gen.generations(data_dir, TYPE) == []
    assert SearchIndexGeneration.objects.filter(type=TYPE).count() == 0

    # And the type is not wedged.
    monkeypatch.undo()
    again = client.post("{}{}/begin/".format(BASE, TYPE), {}, format="json")
    assert again.status_code == 201, again.data


@pytest.mark.django_db
def test_the_generation_admin_can_clear_a_stale_open_lock(client, data_dir):
    """The escape hatch for a type left holding a lock, without waiting a TTL."""
    from django.contrib import admin as django_admin

    generation = begin(client)
    model_admin = django_admin.site._registry[SearchIndexGeneration]
    assert "clear_stale_open_locks" in model_admin.actions

    queryset = SearchIndexGeneration.objects.filter(type=TYPE)
    request = _admin_request()

    # A lock inside its TTL belongs to a running ingest and is left alone.
    model_admin.clear_stale_open_locks(request, queryset)
    assert gen.read_open(data_dir, TYPE)["generation"] == generation

    # Age it past the TTL and it is released.
    _age_the_open_lock(data_dir, TYPE)
    model_admin.clear_stale_open_locks(request, queryset)
    assert gen.read_open(data_dir, TYPE) is None
    assert client.post("{}{}/begin/".format(BASE, TYPE), {},
                       format="json").status_code == 201


@pytest.mark.django_db
def test_the_admin_abort_action_removes_the_lock_file(client, data_dir):
    """Abort has to release the lock, not only delete the directory."""
    from django.contrib import admin as django_admin

    generation = begin(client)
    model_admin = django_admin.site._registry[SearchIndexGeneration]
    model_admin.abort_open_generations(
        _admin_request(), SearchIndexGeneration.objects.filter(type=TYPE))

    assert gen.read_open(data_dir, TYPE) is None
    assert generation not in gen.generations(data_dir, TYPE)
    assert SearchIndexGeneration.objects.get(
        type=TYPE, generation=generation).state == (
            SearchIndexGeneration.STATE_ABORTED)
    assert client.post("{}{}/begin/".format(BASE, TYPE), {},
                       format="json").status_code == 201


def _admin_request():
    """A request object with the message framework stubbed out."""
    from django.test import RequestFactory

    request = RequestFactory().post("/admin/")
    request._messages = _SwallowMessages()
    return request


class _SwallowMessages(list):
    def add(self, level, message, extra_tags=''):
        self.append((level, message))


def _age_the_open_lock(data_dir, type_name, seconds=None):
    """Backdate the OPEN record so the lock reads as abandoned."""
    import json as _json
    import time as _time

    from django.conf import settings as django_settings

    ttl = seconds if seconds is not None else getattr(
        django_settings, "SWIRL_TANTIVY_BEGIN_TTL", 1800)
    path = gen.open_file(data_dir, type_name)
    with open(path, "r", encoding="utf-8") as handle:
        record = _json.load(handle)
    record["started_at"] = _time.time() - (float(ttl) + 60)
    with open(path, "w", encoding="utf-8") as handle:
        _json.dump(record, handle)
