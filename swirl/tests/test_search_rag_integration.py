"""
Integration tests for the RAG fetch flow — drive the full Django view chain
via APIClient instead of unit-testing SearchRag in isolation.

These tests are the regression coverage for the 4.5.0.5 "RAG result swaps
to a different summary seconds after appearing" bug. The unit tests in
test_search_rag.py exercise SearchRag.get_rag_result()'s cache decision
directly; this file exercises the same code path through the actual HTTP
endpoint and asserts the user-visible invariant: **the Result row backing
the rag response must be stable across multiple GETs**, i.e. the auto-RAG
output is not silently deleted-and-replaced on the follow-up fetch.

This is the test layer that was missing during the 4.5.0.3 / 4.5.0.4 cycle.
A unit test of SearchRag wouldn't have caught the auth-chain ordering bug
in views.py; a unit test of the auth chain wouldn't have caught this
double-RAG cache bug. APIClient against the actual URL exercises both at
once, and runs in seconds (vs. qa-suite's 20 minutes).

Run with:  pytest swirl/tests/test_search_rag_integration.py -v
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from swirl.models import Result, Search


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='rag_user', password='pw',
        is_staff=True, is_superuser=True,
    )


@pytest.fixture
def token(db, user):
    return Token.objects.create(user=user)


@pytest.fixture
def authed_client(token):
    """APIClient with the Token header set. The /sapi/ URL prefix passes
    through swirl.middleware.TokenMiddleware, which 403s any request
    missing an ``Authorization`` header — session auth alone isn't
    enough at this layer."""
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return c


@pytest.fixture
def search(db, user):
    return Search.objects.create(
        owner=user,
        query_string='diabetes treatments',
        searchprovider_list=[1],
        status='FULL_RESULTS_READY',
    )


@pytest.fixture
def cached_rag_result(db, user, search):
    """Simulates the Result row written by the auto-RAG path
    (swirl/search.py:302 → RAGPostResultProcessor on search completion)."""
    return Result.objects.create(
        owner=user,
        search_id=search,
        searchprovider='ChatGPT',
        json_results=[{
            'rag_query_items': ['result-1', 'result-2', 'result-3'],
            'body': ['Auto-RAG summary: diabetes treatments include lifestyle changes, ...'],
            'additional_content': {'sources': [{'url': 'https://example.com/d1'}]},
        }],
    )


# ---------------------------------------------------------------------------
# Regression: detail-search-rag fetch must not delete + regenerate the
# cached Result when the URL omits ?rag_items=…
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_detail_rag_fetch_without_rag_items_serves_cache(authed_client, search, cached_rag_result):
    """REGRESSION 4.5.0.5.

    Galaxy's typical follow-up flow is:
      1. POST /swirl/search/?qs=…&rag=true → auto-RAG writes Result A
      2. GET  /swirl/sapi/detail-search-rag/?search_id=N
              (no rag_items in URL — Galaxy hasn't asked to filter)

    Pre-fix, step 2 saw set(stored_items) == set([]) → False → cache miss →
    RAGPostResultProcessor.__init__ deleted Result A and generated Result B
    against a fresh OpenAI call. User saw the summary appear, then swap.

    Post-fix, step 2 must return the cached body and NOT delete Result A.
    """
    original_pk = cached_rag_result.pk
    original_body = cached_rag_result.json_results[0]['body'][0]

    c = authed_client

    r = c.get(f'/swirl/sapi/detail-search-rag/?search_id={search.pk}')

    assert r.status_code == 200, f'expected 200; got {r.status_code} body={r.content!r:.200}'
    body = r.json()
    assert body['message'] == original_body, (
        f'expected cached body to be served verbatim; got {body["message"]!r}'
    )

    # The load-bearing assertion: the Result row must still exist with the
    # same primary key. Pre-fix this would fail because the processor
    # deleted Result A and (if RAGPostResultProcessor managed to run a full
    # generate-and-save cycle) created Result B with a different pk.
    assert Result.objects.filter(pk=original_pk).exists(), (
        'Cached Result was deleted on detail-search-rag fetch — '
        'this is the 4.5.0.5 regression (double-RAG / result swap)'
    )


@pytest.mark.django_db
def test_detail_rag_fetch_with_matching_rag_items_serves_cache(authed_client, search, cached_rag_result):
    """Symmetric positive case: caller passed the same rag_items the
    cached Result was generated for (any order) → cache hit, no regenerate."""
    original_pk = cached_rag_result.pk

    c = authed_client

    # Same set as stored, different order
    r = c.get(
        f'/swirl/sapi/detail-search-rag/?search_id={search.pk}'
        '&rag_items=result-3,result-1,result-2'
    )

    assert r.status_code == 200
    assert Result.objects.filter(pk=original_pk).exists(), (
        'Cached Result deleted despite rag_items matching stored items'
    )


@pytest.mark.django_db
def test_detail_rag_fetch_stable_across_repeated_gets(authed_client, search, cached_rag_result):
    """Hammer the endpoint. The Result pk must never change."""
    original_pk = cached_rag_result.pk

    c = authed_client

    for _ in range(5):
        r = c.get(f'/swirl/sapi/detail-search-rag/?search_id={search.pk}')
        assert r.status_code == 200

    # After 5 fetches, the same Result row must still be the one and only
    # ChatGPT Result for this search.
    chatgpt_results = Result.objects.filter(
        search_id=search.pk, searchprovider='ChatGPT'
    )
    assert chatgpt_results.count() == 1, (
        f'Expected exactly 1 ChatGPT Result after 5 fetches; '
        f'got {chatgpt_results.count()} — indicates double-RAG'
    )
    assert chatgpt_results.first().pk == original_pk, (
        'Result pk changed across repeated fetches — '
        'cached Result was deleted-and-recreated'
    )
