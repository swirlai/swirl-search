"""
Unit tests for the TantivyIndex connector and the Backstage search params
(WP04).

Design: TECH_DESIGN_swirl_for_backstage.md sections 3.4 and 3.5.

The connector is driven directly against a real Tantivy index in tmp_path, with
the process wide manager monkeypatched to point there, the way
test_general_request.py drives the HTTP connectors against a mocked endpoint.

Run with: pytest swirl/tests/test_tantivy_connector.py -v
"""

import json

import pytest

tantivy = pytest.importorskip("tantivy", reason="tantivy is not installed")

from django.contrib.auth.models import Permission, User      # noqa: E402
from django.contrib.contenttypes.models import ContentType   # noqa: E402
from django.test import RequestFactory                       # noqa: E402

from swirl.connectors import alloc_connector                  # noqa: E402
from swirl.connectors.tantivy_index import TantivyIndex       # noqa: E402
from swirl.models import Search, SearchProvider               # noqa: E402
from swirl.tantivy_index.manager import TantivyIndexManager   # noqa: E402
from swirl.views import backstage_query_params                # noqa: E402

TYPE = "software-catalog"


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
def manager(tmp_path, settings, monkeypatch):
    """A manager over a throwaway index, patched in everywhere the code looks."""
    from swirl.connectors import tantivy_index as connector_module
    from swirl.tantivy_index import manager as manager_module

    settings.SWIRL_TANTIVY_DATA_DIR = str(tmp_path / "tantivy")
    settings.SWIRL_TANTIVY_WRITER_HEAP_MB = 15
    settings.SWIRL_TANTIVY_BEGIN_TTL = 3600
    instance = TantivyIndexManager()
    monkeypatch.setattr(manager_module, "default_manager", instance)
    monkeypatch.setattr(connector_module, "default_manager", instance)
    return instance


@pytest.fixture
def loaded(manager):
    generation = manager.begin(TYPE)
    manager.add(TYPE, generation, [
        doc("petstore", lifecycle="production", owner="team-c"),
        doc("petstore-webhook", lifecycle="experimental", owner="team-c"),
        doc("wayback-search", lifecycle="production", owner="team-a"),
    ])
    manager.finalize(TYPE, generation)

    generation = manager.begin("techdocs")
    manager.add("techdocs", generation, [
        doc("petstore-guide", lifecycle="production", owner="team-c")])
    manager.finalize("techdocs", generation)
    return manager


@pytest.fixture
def owner(db):
    user, _ = User.objects.get_or_create(username="backstage_searcher")
    user.user_permissions.add(Permission.objects.get(
        codename="change_searchprovider",
        content_type=ContentType.objects.get_for_model(SearchProvider)))
    return User.objects.get(pk=user.pk)


@pytest.fixture
def provider(owner):
    return SearchProvider.objects.create(
        name="Backstage Index - SWIRL",
        owner=owner,
        active=True,
        default=True,
        connector="TantivyIndex",
        results_per_query=100,
        result_processors=["MappingResultProcessor", "CosineRelevancyResultProcessor"],
        tags=["backstage", "backstage-index"],
    )


def build(provider, owner, query="petstore", backstage=None):
    """Return a TantivyIndex connector wired to a fresh Search."""
    search = Search.objects.create(
        query_string=query, searchprovider_list=[provider.id], owner=owner,
        query_template_json={"backstage": backstage} if backstage else {})
    search.query_string_processed = query
    search.save()
    connector = TantivyIndex(provider.id, search.id, False)
    connector.process_query()
    connector.construct_query()
    return connector


def run(connector):
    assert connector.validate_query() is True
    connector.execute_search()
    assert connector.status == "READY", connector.messages
    connector.normalize_response()
    return connector.results


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def test_the_connector_is_in_the_allowlist():
    assert alloc_connector("TantivyIndex") is TantivyIndex


def test_the_connector_is_in_connector_choices():
    assert ("TantivyIndex", "SWIRL Tantivy Index") in SearchProvider.CONNECTOR_CHOICES


def test_the_connector_type_name():
    assert TantivyIndex.type == "TantivyIndex"


# ---------------------------------------------------------------------------
# normalize_response
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_normalize_response_shape(loaded, provider, owner):
    results = run(build(provider, owner, "petstore"))
    assert results
    first = results[0]
    assert set(first) == {"title", "body", "url", "title_hit_highlights",
                          "body_hit_highlights", "payload"}
    assert first["title"] == "petstore"
    assert first["url"] == "/catalog/default/component/petstore"
    assert first["body"]
    assert isinstance(first["payload"], dict)


@pytest.mark.django_db
def test_payload_backstage_carries_the_type_and_the_whole_document(
        loaded, provider, owner):
    results = run(build(provider, owner, "petstore"))
    payload = results[0]["payload"]
    assert "backstage" in payload
    assert payload["backstage"]["type"] == TYPE
    document = payload["backstage"]["document"]
    assert document["title"] == "petstore"
    assert document["location"] == "/catalog/default/component/petstore"
    assert document["lifecycle"] == "production"
    assert document["owner"] == "team-c"
    assert payload["doc_id"] == "/catalog/default/component/petstore"


@pytest.mark.django_db
def test_the_tantivy_score_is_carried_in_the_payload(loaded, provider, owner):
    results = run(build(provider, owner, "petstore"))
    scores = [result["payload"]["searchprovider_score"] for result in results]
    assert all(score > 0 for score in scores)
    assert scores == sorted(scores, reverse=True)


@pytest.mark.django_db
def test_no_top_level_key_is_unknown_to_the_mapping_processor(
        loaded, provider, owner):
    """Anything the MappingResultProcessor does not know would clobber payload."""
    from swirl.processors.utils import create_result_dictionary

    results = run(build(provider, owner, "petstore"))
    known = set(create_result_dictionary())
    for result in results:
        assert set(result) <= known


@pytest.mark.django_db
def test_a_query_with_no_hits_is_not_an_error(loaded, provider, owner):
    connector = build(provider, owner, "zebracrossing")
    assert run(connector) == []
    assert connector.status == "READY"
    assert connector.retrieved == 0


@pytest.mark.django_db
def test_results_survive_the_mapping_result_processor(loaded, provider, owner):
    connector = build(provider, owner, "petstore")
    run(connector)
    from swirl.processors.mapping import MappingResultProcessor

    processor = MappingResultProcessor(
        connector.results, provider, "petstore", request_id="test")
    assert processor.process() > 0
    first = processor.processed_results[0]
    assert first["title"] == "petstore"
    assert first["url"] == "/catalog/default/component/petstore"
    assert first["payload"]["backstage"]["document"]["title"] == "petstore"
    assert first["payload"]["searchprovider_score"] > 0
    assert first["searchprovider"] == "Backstage Index - SWIRL"


# ---------------------------------------------------------------------------
# backstage_types and backstage_filters
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_no_types_searches_every_live_type(loaded, provider, owner):
    results = run(build(provider, owner, "petstore"))
    types = {result["payload"]["backstage"]["type"] for result in results}
    assert types == {TYPE, "techdocs"}


@pytest.mark.django_db
def test_backstage_types_restrict_the_search(loaded, provider, owner):
    connector = build(provider, owner, "petstore",
                      backstage={"types": ["techdocs"]})
    assert connector.backstage_types == ["techdocs"]
    results = run(connector)
    assert results
    assert all(result["payload"]["backstage"]["type"] == "techdocs"
               for result in results)


@pytest.mark.django_db
def test_backstage_types_accept_a_comma_string(loaded, provider, owner):
    connector = build(provider, owner, "petstore",
                      backstage={"types": "techdocs, software-catalog"})
    assert connector.backstage_types == ["techdocs", "software-catalog"]


@pytest.mark.django_db
def test_backstage_filters_are_honoured(loaded, provider, owner):
    connector = build(provider, owner, "component",
                      backstage={"types": [TYPE],
                                 "filters": {"lifecycle": "production"}})
    assert connector.backstage_filters == {"lifecycle": "production"}
    results = run(connector)
    assert results
    titles = sorted(result["title"] for result in results)
    assert titles == ["petstore", "wayback-search"]


@pytest.mark.django_db
def test_a_multi_valued_filter_is_an_or(loaded, provider, owner):
    connector = build(provider, owner, "component",
                      backstage={"types": [TYPE],
                                 "filters": {"owner": ["team-a", "team-c"]}})
    assert connector.backstage_filters == {"owner": ["team-a", "team-c"]}
    assert len(run(connector)) == 3


@pytest.mark.django_db
def test_a_filter_that_matches_nothing_returns_nothing(loaded, provider, owner):
    connector = build(provider, owner, "component",
                      backstage={"filters": {"lifecycle": "retired"}})
    assert run(connector) == []


@pytest.mark.django_db
def test_nested_filter_values_are_dropped(loaded, provider, owner):
    connector = build(provider, owner, "component", backstage={
        "filters": {"lifecycle": "production", "nested": {"a": 1},
                    "empty": "", "none": None, "list": ["x", {"y": 1}]}})
    assert connector.backstage_filters == {"lifecycle": "production",
                                           "list": ["x"]}


@pytest.mark.django_db
def test_the_provider_supplies_defaults_when_the_search_carries_none(
        loaded, provider, owner):
    provider.query_template_json = {"backstage": {"types": ["techdocs"]}}
    provider.save()
    connector = build(provider, owner, "petstore")
    assert connector.backstage_types == ["techdocs"]


@pytest.mark.django_db
def test_the_search_overrides_the_provider(loaded, provider, owner):
    provider.query_template_json = {"backstage": {"types": ["techdocs"]}}
    provider.save()
    connector = build(provider, owner, "petstore",
                      backstage={"types": [TYPE]})
    assert connector.backstage_types == [TYPE]


@pytest.mark.django_db
def test_a_junk_backstage_block_is_ignored(loaded, provider, owner):
    search = Search.objects.create(
        query_string="petstore", searchprovider_list=[provider.id], owner=owner,
        query_template_json={"backstage": "not an object"})
    search.query_string_processed = "petstore"
    search.save()
    connector = TantivyIndex(provider.id, search.id, False)
    connector.process_query()
    connector.construct_query()
    assert connector.backstage_types == []
    assert connector.backstage_filters == {}
    assert run(connector)


@pytest.mark.django_db
def test_an_empty_query_fails_validation(loaded, provider, owner):
    import time as _time

    connector = build(provider, owner, "petstore")
    connector.query_to_provider = ""
    # Connector.error() saves a Result row, which needs start_time; federate()
    # normally sets it.
    connector.start_time = _time.time()
    assert connector.validate_query() is False


# ---------------------------------------------------------------------------
# The search view params (section 3.5)
# ---------------------------------------------------------------------------

def request_with(**params):
    return RequestFactory().get("/swirl/search/", params)


def test_no_backstage_params_stores_nothing():
    assert backstage_query_params(request_with(qs="tech")) == {}


def test_backstage_types_is_a_comma_list():
    block = backstage_query_params(
        request_with(qs="tech", backstage_types="software-catalog, techdocs"))
    assert block == {"backstage": {"types": ["software-catalog", "techdocs"]}}


def test_backstage_filters_is_json():
    block = backstage_query_params(request_with(
        qs="tech", backstage_filters=json.dumps({"kind": "component"})))
    assert block == {"backstage": {"filters": {"kind": "component"}}}


def test_both_params_together():
    block = backstage_query_params(request_with(
        backstage_types="techdocs",
        backstage_filters=json.dumps({"owner": ["team-a", "team-b"]})))
    assert block == {"backstage": {
        "types": ["techdocs"],
        "filters": {"owner": ["team-a", "team-b"]}}}


@pytest.mark.parametrize("raw", ["{not json", "[]", '"a string"', "null"])
def test_malformed_backstage_filters_is_ignored_not_fatal(raw):
    assert backstage_query_params(request_with(backstage_filters=raw)) == {}


def test_empty_values_store_nothing():
    assert backstage_query_params(
        request_with(backstage_types=" , ", backstage_filters="{}")) == {}


@pytest.mark.django_db
def test_the_search_view_stores_the_params_on_the_search(loaded, provider, owner):
    """?qs= with the Backstage params lands on Search.query_template_json.

    The response itself is not asserted: /swirl/search/ needs a running Celery
    worker to produce results, and this test is about what the view records on
    the Search row before federating.
    """
    from rest_framework.test import APIClient

    from django.contrib.auth.models import Permission as Perm
    for codename in ('add_search', 'change_search', 'view_search',
                     'add_result', 'change_result'):
        owner.user_permissions.add(Perm.objects.get(codename=codename))
    api = APIClient()
    api.force_authenticate(user=User.objects.get(pk=owner.pk))
    api.get("/swirl/search/", {
        "qs": "petstore",
        "providers": "backstage-index",
        "backstage_types": "software-catalog",
        "backstage_filters": json.dumps({"lifecycle": "production"}),
    })
    search = Search.objects.filter(query_string="petstore").order_by('-id').first()
    assert search is not None
    assert search.query_template_json == {"backstage": {
        "types": ["software-catalog"],
        "filters": {"lifecycle": "production"}}}


# ---------------------------------------------------------------------------
# The preloaded provider
# ---------------------------------------------------------------------------

def test_the_preloaded_backstage_provider():
    import os

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(root, "SearchProviders", "backstage.json"),
              encoding="utf-8") as handle:
        entry = json.load(handle)
    assert entry["name"] == "Backstage Index - SWIRL"
    assert entry["connector"] == "TantivyIndex"
    assert entry["tags"] == ["backstage", "backstage-index"]
    assert entry["results_per_query"] == 100
    assert entry["active"] is True
    assert entry["result_processors"] == ["MappingResultProcessor",
                                          "CosineRelevancyResultProcessor"]

    with open(os.path.join(root, "SearchProviders", "preloaded.json"),
              encoding="utf-8") as handle:
        preloaded = json.load(handle)
    matches = [row for row in preloaded if row["name"] == entry["name"]]
    assert len(matches) == 1
    assert matches[0] == entry
