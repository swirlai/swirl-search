"""
End to end integration across the two SWIRL for Backstage lanes.

Lane A built the Tantivy index, the ingest API (WP02), the TantivyIndex
connector and the Backstage search params (WP04). Lane B built the plugin-token
bearer path (WP03). This module tests the seam between them: one Backstage
plugin token, minted here, drives the whole lifecycle over HTTP.

  1. A service principal (a plugin token with no obo, mapped to the user
     'backstage:service') calls begin, docs and finalize on /swirl/index/.
  2. A user principal (the same token shape with an obo carrying the user
     entity ref, mapped to 'backstage:user:default/sid') calls
     GET /swirl/search/?qs=petstore&providers=backstage-index
     &backstage_types=software-catalog and gets a result whose
     payload.backstage.document is the document that was ingested in step 1.

Neither user is created up front: BackstageTokenMiddleware provisions both from
the token, and BackstagePrincipalAuthentication carries the middleware's
decision into DRF so the ingest and search views see the right user.

The key pair and the JWKS are generated per test run and served with
`responses`; nothing is checked in. The token helpers are reused from
test_backstage_bearer.py (WP03).

/swirl/search/ federates through Celery. There is no worker in the suite and
lane A's test_tantivy_connector.py said so explicitly rather than starting one,
so this test puts Celery in eager mode: swirl.search.search() already runs
in-process, and eager mode makes the federate_task group run in-process too.
The connector path itself is unchanged, which is the point of the test.

Run with: pytest swirl/tests/test_backstage_integration.py -v
"""

import pytest

tantivy = pytest.importorskip("tantivy", reason="tantivy is not installed")

import responses                                              # noqa: E402
from django.contrib.auth.models import User                   # noqa: E402
from rest_framework.test import APIClient                     # noqa: E402

from swirl.backstage_bearer import (                          # noqa: E402
    BACKSTAGE_SERVICE_USERNAME,
    reset_jwks_client,
)
from swirl.models import Search, SearchProvider               # noqa: E402
from swirl.tantivy_index.manager import TantivyIndexManager   # noqa: E402

# WP03's token helpers. swirl/tests has no __init__.py, so pytest puts the
# directory on sys.path and the module imports by its bare name.
from test_backstage_bearer import (                           # noqa: E402
    _make_es256_key,
    _mint_plugin_token,
    _serve_jwks,
    backstage_on,
)

TYPE = "software-catalog"
USER_REF = "user:default/sid"
BACKSTAGE_USERNAME = "backstage:" + USER_REF
INDEX = "/swirl/index/"


def doc(name, **extra):
    payload = {
        "title": name,
        "text": "The {} component of the platform.".format(name),
        "location": "/catalog/default/component/{}".format(name),
        "kind": "Component",
    }
    payload.update(extra)
    return payload


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def keys():
    priv_pem, jwk = _make_es256_key()
    reset_jwks_client()
    yield priv_pem, jwk
    reset_jwks_client()


@pytest.fixture
def index_dir(tmp_path, settings, monkeypatch):
    """Point every holder of the process wide manager at a throwaway directory.

    The ingest views, the connector and the manager module each import
    default_manager by name, so all three are patched; the search runs in this
    process, so one instance serves the write side and the read side.
    """
    from swirl.connectors import tantivy_index as connector_module
    from swirl.tantivy_index import manager as manager_module
    import swirl.views_index as views_index

    settings.SWIRL_TANTIVY_DATA_DIR = str(tmp_path / "tantivy")
    settings.SWIRL_TANTIVY_WRITER_HEAP_MB = 15
    settings.SWIRL_TANTIVY_BEGIN_TTL = 3600
    instance = TantivyIndexManager()
    monkeypatch.setattr(manager_module, "default_manager", instance)
    monkeypatch.setattr(connector_module, "default_manager", instance)
    monkeypatch.setattr(views_index, "default_manager", instance, raising=False)
    return instance


@pytest.fixture
def celery_eager(settings):
    """Run federate_task in this process; there is no worker in the suite.

    swirl_server/celery.py reads its configuration from Django settings under
    the CELERY_ namespace, and it reads them live, so overriding the setting is
    what actually turns eager mode on; assigning to app.conf does not.
    """
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = False
    from swirl_server.celery import app as celery_app
    assert celery_app.conf.task_always_eager is True
    return celery_app


@pytest.fixture
def provider(db):
    """The preloaded Backstage provider, shared so any Backstage user sees it.

    swirl.search.get_query_selected_provider_list() only offers a provider the
    search owner owns or that is shared, and a Backstage user is provisioned by
    the middleware rather than owning anything.
    """
    owner = User.objects.create_user(username="backstage_integration_owner")
    return SearchProvider.objects.create(
        name="Backstage Index - SWIRL",
        owner=owner,
        shared=True,
        active=True,
        default=True,
        connector="TantivyIndex",
        results_per_query=100,
        result_processors=["MappingResultProcessor", "CosineRelevancyResultProcessor"],
        tags=["backstage", "backstage-index"],
    )


def bearer(token):
    return {"HTTP_AUTHORIZATION": "Bearer {}".format(token)}


# ---------------------------------------------------------------------------
# The seam: ingest with a service token, search with a user token
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@backstage_on
@responses.activate
def test_ingest_with_a_service_token_then_search_with_a_user_token(
        keys, index_dir, provider, celery_eager):
    priv_pem, jwk = keys
    _serve_jwks(jwk)
    api = APIClient()

    # --- 1. ingest, authenticated only by a Backstage plugin token ----------
    service_token = _mint_plugin_token(priv_pem, jwk["kid"])

    begin = api.post("{}{}/begin/".format(INDEX, TYPE), {}, format="json",
                     **bearer(service_token))
    assert begin.status_code == 201, begin.data
    generation = begin.data["generation"]

    # The service principal was provisioned by the middleware and reached the
    # view with the ingest permission; no SWIRL API token was involved.
    service_user = User.objects.get(username=BACKSTAGE_SERVICE_USERNAME)
    assert service_user.has_perm("swirl.change_searchprovider")

    documents = [
        doc("petstore", lifecycle="production", owner="team-c"),
        doc("wayback-search", lifecycle="production", owner="team-a"),
    ]
    docs = api.post("{}{}/{}/docs/".format(INDEX, TYPE, generation),
                    {"documents": documents}, format="json",
                    **bearer(service_token))
    assert docs.status_code == 202, docs.data
    assert docs.data["accepted"] == 2

    finalize = api.post("{}{}/{}/finalize/".format(INDEX, TYPE, generation),
                        {}, format="json", **bearer(service_token))
    assert finalize.status_code == 200, finalize.data
    assert finalize.data["count"] == 2
    assert finalize.data["live"] == generation

    # --- 2. search, authenticated by a plugin token carrying an obo ---------
    user_token = _mint_plugin_token(priv_pem, jwk["kid"], user_ref=USER_REF)

    response = api.get("/swirl/search/", {
        "qs": "petstore",
        "providers": "backstage-index",
        "backstage_types": TYPE,
    }, **bearer(user_token))

    assert response.status_code == 200, response.data
    body = response.json()
    results = body["results"]
    assert results, body

    # The search ran as the Backstage user, not as the service principal.
    search = Search.objects.order_by("-id").first()
    assert search.owner.username == BACKSTAGE_USERNAME
    assert search.query_template_json == {"backstage": {"types": [TYPE]}}

    # The whole Backstage document rides in payload.backstage.document, which
    # is what the engine module renders.
    petstore = [item for item in results
                if item["payload"]["backstage"]["document"]["title"] == "petstore"]
    assert len(petstore) == 1, results
    hit = petstore[0]
    assert hit["searchprovider"] == provider.name
    backstage = hit["payload"]["backstage"]
    assert backstage["type"] == TYPE
    assert backstage["document"] == doc("petstore", lifecycle="production",
                                        owner="team-c")
    assert hit["url"] == "/catalog/default/component/petstore"


@pytest.mark.django_db
@backstage_on
@responses.activate
def test_a_user_principal_may_not_ingest(keys, index_dir, provider):
    """The obo user is a search user, not an indexer: begin answers 403.

    The two principals are deliberately different permission sets in WP03, and
    the ingest view has to keep honouring that now that it accepts Backstage
    principals at all.
    """
    priv_pem, jwk = keys
    _serve_jwks(jwk)
    user_token = _mint_plugin_token(priv_pem, jwk["kid"], user_ref=USER_REF)

    response = APIClient().post("{}{}/begin/".format(INDEX, TYPE), {},
                                format="json", **bearer(user_token))

    assert response.status_code == 403, response.data
    assert User.objects.filter(username=BACKSTAGE_USERNAME).exists()


@pytest.mark.django_db
@backstage_on
@responses.activate
def test_an_invalid_token_never_reaches_the_ingest_view(keys, index_dir):
    """A token signed by an unknown key is stopped by the middleware with 401."""
    priv_pem, jwk = keys
    _serve_jwks(jwk)
    other_pem, _ = _make_es256_key()
    forged = _mint_plugin_token(other_pem, jwk["kid"])

    response = APIClient().post("{}{}/begin/".format(INDEX, TYPE), {},
                                format="json", **bearer(forged))

    assert response.status_code == 401
    assert response["WWW-Authenticate"] == 'Bearer error="invalid_token"'
    assert not User.objects.filter(username__startswith="backstage:").exists()
