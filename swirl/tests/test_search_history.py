"""
Unit tests for the search history pagination plumbing the Galaxy UI relies on.

Covers the DS-5598 follow-up fix:
- ``swirl.utils.standard_paginate`` returns DRF-style
  ``{count, next, previous, results}`` and honours the ``items`` query param
  used by Galaxy (NOT DRF's default ``page_size``).
- ``SearchViewSet.list`` uses ``standard_paginate`` when called with
  ``?items=…``, ``?page=…``, or ``?search_only=true`` so the Galaxy
  search-history sidebar and home-dashboard widgets can read
  ``response.results`` / ``response.next``.
- Legacy callers that pass none of those params still get the raw paginated
  list (back-compat with the old behaviour).

Run with: pytest swirl/tests/test_search_history.py -v
"""

import pytest
from unittest.mock import MagicMock

from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from swirl.models import Search
from swirl.serializers import SearchSerializer
from swirl.utils import standard_paginate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _DummyRequest:
    """Just enough Request shape for standard_paginate to introspect."""

    def __init__(self, query=None, path='/api/swirl/sapi/search/', base='http://testserver'):
        from django.http.request import QueryDict
        qd = QueryDict('', mutable=True)
        qd.update(query or {})
        self.GET = qd
        self.path = path
        self._base = base

    def build_absolute_uri(self, location):
        return f"{self._base}{location}"


@pytest.fixture
def owner(db):
    user, _ = User.objects.get_or_create(username='hist_owner')
    perms = Permission.objects.filter(
        content_type=ContentType.objects.get_for_model(Search),
    )
    for perm in perms:
        user.user_permissions.add(perm)
    return User.objects.get(pk=user.pk)


@pytest.fixture
def other_owner(db):
    user, _ = User.objects.get_or_create(username='hist_other')
    return user


@pytest.fixture
def searches(owner, other_owner):
    """Five searches owned by `owner`, one by `other_owner`."""
    rows = []
    for i in range(5):
        rows.append(Search.objects.create(
            query_string=f"owner-query-{i}", owner=owner,
        ))
    # noise — should never appear in owner's history list
    Search.objects.create(query_string="other-user-query", owner=other_owner)
    return rows


# ---------------------------------------------------------------------------
# standard_paginate — pure function
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_standard_paginate_returns_drf_shape(owner, searches):
    qs = Search.objects.filter(owner=owner).order_by('-date_created')
    request = _DummyRequest(query={'items': '2', 'page': '1'})

    result = standard_paginate(qs, request, SearchSerializer)

    assert set(result.keys()) == {'count', 'next', 'previous', 'results'}
    assert result['count'] == 5
    assert len(result['results']) == 2
    assert result['previous'] is None
    assert result['next'] is not None and 'page=2' in result['next']


@pytest.mark.django_db
def test_standard_paginate_respects_items_param(owner, searches):
    qs = Search.objects.filter(owner=owner).order_by('-date_created')

    # items=3 → 3 results, has next page
    page1 = standard_paginate(qs, _DummyRequest({'items': '3', 'page': '1'}), SearchSerializer)
    assert len(page1['results']) == 3
    assert page1['next'] is not None

    # items=3 page=2 → 2 remaining results, no next
    page2 = standard_paginate(qs, _DummyRequest({'items': '3', 'page': '2'}), SearchSerializer)
    assert len(page2['results']) == 2
    assert page2['next'] is None
    assert page2['previous'] is not None and 'page=1' in page2['previous']


@pytest.mark.django_db
def test_standard_paginate_invalid_items_defaults_to_10(owner, searches):
    qs = Search.objects.filter(owner=owner)
    result = standard_paginate(
        qs, _DummyRequest({'items': 'not-a-number', 'page': '1'}), SearchSerializer,
    )
    # Default page size is 10; we have 5 searches → all returned, no next page
    assert len(result['results']) == 5
    assert result['next'] is None


@pytest.mark.django_db
def test_standard_paginate_results_ordered_newest_first(owner, searches):
    qs = Search.objects.filter(owner=owner).order_by('-date_created')
    result = standard_paginate(qs, _DummyRequest({'items': '5', 'page': '1'}), SearchSerializer)
    qs_ids = [r['id'] for r in result['results']]
    # Newest (highest id given auto-increment + same-timestamp creation) first
    assert qs_ids == sorted(qs_ids, reverse=True)


# ---------------------------------------------------------------------------
# SearchViewSet.list — endpoint integration
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_endpoint_returns_drf_pagination_with_search_only_flag(owner, searches):
    client = APIClient()
    client.force_authenticate(user=owner)
    resp = client.get('/swirl/search/?page=1&items=3&search_only=true')

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {'count', 'next', 'previous', 'results'}
    assert body['count'] == 5
    assert len(body['results']) == 3
    assert body['next'] is not None


@pytest.mark.django_db
def test_list_endpoint_returns_drf_pagination_with_items_param(owner, searches):
    """Galaxy may omit search_only; presence of items alone must trigger DRF format."""
    client = APIClient()
    client.force_authenticate(user=owner)
    resp = client.get('/swirl/search/?items=2')

    assert resp.status_code == 200
    body = resp.json()
    assert 'results' in body
    assert 'next' in body
    assert len(body['results']) == 2


@pytest.mark.django_db
def test_list_endpoint_filters_by_owner(owner, other_owner, searches):
    client = APIClient()
    client.force_authenticate(user=owner)
    resp = client.get('/swirl/search/?items=50&page=1&search_only=true')

    body = resp.json()
    queries = {r['query_string'] for r in body['results']}
    assert 'other-user-query' not in queries
    assert all(q.startswith('owner-query-') for q in queries)


@pytest.mark.django_db
def test_list_endpoint_legacy_no_params_returns_raw_list(owner, searches):
    """Back-compat: callers that don't pass items/page/search_only keep the
    pre-fix raw-list response shape so existing scripts/tests aren't broken."""
    client = APIClient()
    client.force_authenticate(user=owner)
    resp = client.get('/swirl/search/')

    assert resp.status_code == 200
    body = resp.json()
    # Old shape: raw list, not a dict
    assert isinstance(body, list)
    assert len(body) == 5
