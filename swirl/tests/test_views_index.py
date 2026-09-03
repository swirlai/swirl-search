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
def test_config_ignores_unknown_keys(client):
    response = client.post(BASE + "config/", {"nonsense": 1}, format="json")
    assert response.status_code == 200
    assert "nonsense" not in response.data


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
