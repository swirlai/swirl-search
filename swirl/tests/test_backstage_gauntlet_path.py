"""The nine gate-zero gauntlet cases through the whole shipped Backstage path.

WP00 drove tantivy-py in process, and swirl/tests/test_tantivy_search_relevance.py
protects that. This module asks the same nine questions of the path a released
container actually serves: a Backstage plugin token, the ingest API, the
SearchProvider as SearchProviders/backstage.json ships it (so the query
processor named there is the one under test), the TantivyIndex connector,
MappingResultProcessor and CosineRelevancyResultProcessor, and finally
CosineRelevancyPostResultProcessor, which is what sets swirl_score and decides
the order the plugin sees.

Why the full path and not the connector alone. Re-running the gauntlet against
the released image found `foo-bar.com` failing, and it failed nowhere near the
index: Tantivy put foo-bar.com first with a score two orders of magnitude above
the next hit. AdaptiveQueryProcessor had turned the term into `foo-bar com`
before the connector saw it, and the relevancy pass then scored a page of
`recommendation-*` entities above the one exact hit. A connector-level test
passes in that state, so it would not have caught the defect.

The corpus is the in-memory fixture from test_tantivy_search_relevance.py plus
synthetic entities, so nothing here depends on a checkout of `backstage`.

Run with: pytest swirl/tests/test_backstage_gauntlet_path.py -v
"""

import json
import os

import pytest

tantivy = pytest.importorskip("tantivy", reason="tantivy is not installed")

import responses                                              # noqa: E402
from django.contrib.auth.models import User                   # noqa: E402
from rest_framework.test import APIClient                     # noqa: E402

from swirl.backstage_bearer import reset_jwks_client          # noqa: E402
from swirl.models import SearchProvider                       # noqa: E402
from swirl.tantivy_index.manager import TantivyIndexManager   # noqa: E402

# swirl/tests has no __init__.py, so pytest puts the directory on sys.path and
# these sibling modules import by their bare names.
from test_backstage_bearer import (                           # noqa: E402
    AUDIENCE,
    JWKS_URL,
    _make_es256_key,
    _mint_plugin_token,
)
from test_tantivy_search_relevance import (                   # noqa: E402
    EXAMPLE_ENTITIES,
    gauntlet,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROVIDER_FILE = os.path.join(REPO_ROOT, "SearchProviders", "backstage.json")

TYPE = "software-catalog"
USER_REF = "user:default/sid"
INDEX = "/swirl/index/"

#: Enough synthetic entities for every case to be applicable and for the
#: `recommendation-*` decoys that broke `foo-bar.com` on the released image to
#: be present in numbers. 600 keeps the run under a minute.
SYNTHETIC_COUNT = 600


def bearer(token):
    return {"HTTP_AUTHORIZATION": "Bearer {}".format(token)}


@pytest.fixture(scope="module")
def corpus():
    documents = [gauntlet.entity_to_document(entity)
                 for entity in EXAMPLE_ENTITIES]
    documents = [document for document in documents if document]
    documents.extend(gauntlet.generate_synthetic(SYNTHETIC_COUNT))
    return documents


@pytest.fixture
def index_dir(tmp_path, settings, monkeypatch):
    """Point every holder of the process wide manager at a throwaway index."""
    from swirl.connectors import tantivy_index as connector_module
    from swirl.tantivy_index import manager as manager_module
    import swirl.views_index as views_index

    settings.SWIRL_TANTIVY_DATA_DIR = str(tmp_path / "tantivy")
    settings.SWIRL_TANTIVY_WRITER_HEAP_MB = 30
    settings.SWIRL_TANTIVY_BEGIN_TTL = 3600
    instance = TantivyIndexManager()
    monkeypatch.setattr(manager_module, "default_manager", instance)
    monkeypatch.setattr(connector_module, "default_manager", instance)
    monkeypatch.setattr(views_index, "default_manager", instance, raising=False)
    return instance


@pytest.fixture
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = False
    from swirl_server.celery import app as celery_app
    assert celery_app.conf.task_always_eager is True
    return celery_app


@pytest.fixture
def shipped_provider(db):
    """The provider exactly as SearchProviders/backstage.json ships it.

    Read from the file rather than spelled out here, so that the query
    processor and result processor chain under test are the ones the image
    loads at start. docker/backstage/load_backstage_provider.py does the same.
    """
    with open(PROVIDER_FILE, encoding="utf-8") as handle:
        entry = json.load(handle)
    owner = User.objects.create_user(username="backstage_gauntlet_owner")
    return SearchProvider.objects.create(
        name=entry["name"],
        owner=owner,
        shared=True,
        active=entry.get("active", True),
        default=entry.get("default", True),
        connector=entry["connector"],
        url=entry.get("url", ""),
        query_template=entry.get("query_template", ""),
        query_template_json=entry.get("query_template_json", {}),
        query_processors=entry.get("query_processors", []),
        query_mappings=entry.get("query_mappings", ""),
        result_processors=entry.get("result_processors", []),
        results_per_query=entry.get("results_per_query", 100),
        tags=entry.get("tags", []),
    )


def ingest(api, token, documents):
    begin = api.post("{}{}/begin/".format(INDEX, TYPE), {}, format="json",
                     **bearer(token))
    assert begin.status_code == 201, begin.data
    generation = begin.data["generation"]
    for offset in range(0, len(documents), 500):
        batch = documents[offset:offset + 500]
        docs = api.post("{}{}/{}/docs/".format(INDEX, TYPE, generation),
                        {"documents": batch}, format="json", **bearer(token))
        assert docs.status_code == 202, docs.data
    finalize = api.post("{}{}/{}/finalize/".format(INDEX, TYPE, generation),
                        {}, format="json", **bearer(token))
    assert finalize.status_code == 200, finalize.data
    assert finalize.data["count"] == len(documents)
    return generation


def run_case(api, token, case):
    """One gauntlet case through GET /swirl/search/, paging to case.limit.

    Returns the hits in the shape the gauntlet check functions expect: title,
    score and the whole Backstage document.
    """
    params = {
        "qs": case.term,
        "providers": "backstage-index",
        "backstage_types": TYPE,
    }
    if case.filters:
        params["backstage_filters"] = json.dumps(case.filters)
    response = api.get("/swirl/search/", params, **bearer(token))
    assert response.status_code == 200, response.data
    body = response.json()

    hits = []

    def take(payload):
        for result in payload.get("results") or []:
            document = ((result.get("payload") or {}).get("backstage")
                        or {}).get("document") or {}
            hits.append({
                "title": result.get("title") or document.get("title") or "",
                "score": result.get("swirl_score") or 0.0,
                "document": document,
            })

    take(body)
    next_page = ((body.get("info") or {}).get("results") or {}).get("next_page")
    while next_page and len(hits) < case.limit:
        page = api.get(next_page, **bearer(token))
        if page.status_code != 200:
            break
        payload = page.json()
        before = len(hits)
        take(payload)
        if len(hits) == before:
            break
        next_page = ((payload.get("info") or {}).get("results")
                     or {}).get("next_page")
    return hits, body


@pytest.fixture
def gauntlet_api(settings, index_dir, shipped_provider, celery_eager, corpus):
    """Ingest the corpus once and hand back a client with a user token.

    The whole Backstage bearer path is real: a key pair minted here, a JWKS
    served over the mocked transport, a service token for the ingest and a user
    token carrying an obo for the search.

    Fuzzy is turned on globally, which is how the release gauntlet is run: WP00
    enabled it for the typo case alone, and the re-run against the image
    confirmed it changes nothing else at this corpus size.
    """
    settings.SWIRL_BACKSTAGE_JWKS_URL = JWKS_URL
    settings.SWIRL_BACKSTAGE_AUDIENCE = AUDIENCE
    priv_pem, jwk = _make_es256_key()
    reset_jwks_client()
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        mock.add(responses.GET, JWKS_URL, json={"keys": [jwk]}, status=200)
        api = APIClient()
        service_token = _mint_plugin_token(priv_pem, jwk["kid"])
        ingest(api, service_token, corpus)

        config = api.post("{}config/".format(INDEX),
                          {"fuzzy": {"enabled": True}}, format="json",
                          **bearer(service_token))
        assert config.status_code == 200, config.data
        assert config.data["fuzzy_enabled"] is True

        user_token = _mint_plugin_token(priv_pem, jwk["kid"], user_ref=USER_REF)
        yield api, user_token
    reset_jwks_client()


# ---------------------------------------------------------------------------
# The gauntlet
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_the_nine_gauntlet_cases_pass_on_the_shipped_path(gauntlet_api, corpus):
    api, token = gauntlet_api
    available = {document.get("title") or "" for document in corpus}

    failures = []
    for case in gauntlet.GAUNTLET_CASES:
        missing = [title for title in case.requires if title not in available]
        assert not missing, (
            "the fixture corpus must contain every planted entity, missing "
            "{} for case {}".format(missing, case.name))
        hits, _body = run_case(api, token, case)
        passed, detail = case.check(hits[:case.limit])
        if not passed:
            failures.append("{} ({!r}): {} - top 5 {}".format(
                case.name, case.term, detail,
                [(hit["title"], hit["score"]) for hit in hits[:5]]))

    assert failures == [], "\n".join(failures)


@pytest.mark.django_db
def test_a_dotted_hostname_reaches_the_provider_with_its_dots(gauntlet_api):
    """The regression itself: the provider must be asked for foo-bar.com.

    clean_string() keeps `-` and turns `.` into a space, so
    AdaptiveQueryProcessor asked the provider for `foo-bar com`; the bare token
    `com` then matched inside every `recommendation-*` title through the ngram
    field. BackstageQueryProcessor keeps the dot.
    """
    api, token = gauntlet_api
    case = case_named("dotted-hostname")
    _hits, body = run_case(api, token, case)

    asked = [row.get("query_to_provider")
             for row in (body.get("info") or {}).values()
             if isinstance(row, dict) and "query_to_provider" in row]
    assert asked, body.get("info")
    assert asked[0] == "foo-bar.com", asked


@pytest.mark.django_db
def test_a_dotted_hostname_is_rank_one(gauntlet_api):
    api, token = gauntlet_api
    hits, _body = run_case(api, token, case_named("dotted-hostname"))

    assert hits, "foo-bar.com returned nothing at all"
    assert hits[0]["title"] == "foo-bar.com", [
        (hit["title"], hit["score"]) for hit in hits[:5]]


@pytest.mark.django_db
def test_the_index_puts_tech_radar_first_for_tech(gauntlet_api, index_dir):
    """Gate zero's own answer, asked of the index rather than of the ranking.

    WP00 in process put tech-radar at rank 1 for "tech". The released image put
    five synthetic tech-*-service entities above it, which still satisfies the
    case (a tech-prefixed title above any team-only entity, none in the top 5)
    but is worse than gate zero. The reordering happens downstream of Tantivy,
    in CosineRelevancyPostResultProcessor, which scores every provider's results
    the same way and is not something the Backstage path may change on its own;
    no boost in this index can reach it, because tech-radar is already rank 1
    coming out of the index and rank only enters that score through a
    1 + 1/sqrt(rank) term.

    So the index-side property is what is pinned here, and the whole-path order
    is recorded in reboot-design/gauntlet-results.md instead.
    """
    hits = index_dir.search(types=[TYPE], term="tech", limit=5, fuzzy=True)

    assert hits
    assert hits[0]["title"] == "tech-radar", [
        (hit["title"], hit["score"]) for hit in hits[:5]]
    assert not any(hit["title"].startswith("team-") for hit in hits)


@pytest.mark.django_db
def test_mes_returns_nothing(gauntlet_api):
    """The substring-garbage case, which the ngram minimum decides."""
    api, token = gauntlet_api
    hits, _body = run_case(api, token, case_named("mes-no-garbage"))

    assert hits == [], [(hit["title"], hit["score"]) for hit in hits[:5]]


def case_named(name):
    for case in gauntlet.GAUNTLET_CASES:
        if case.name == name:
            return case
    raise AssertionError("no gauntlet case named {}".format(name))
