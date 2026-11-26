"""
fetch-document fetches a document found by a search:
- it fetches only a url that one of the caller's own searches returned;
- given a provider_id, it uses that provider's page-fetch settings (request
  headers among them) only when that provider returned the url, and only for
  a caller who could search the provider (its owner, or anyone when shared).
"""

from unittest import mock

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from swirl.models import Result, Search, SearchProvider

URL = '/swirl/fetch-document/'
TARGET = 'http://documents.example.invalid/reports/annual report.txt'
HEADER = 'Bearer provider-page-fetch-value'


@pytest.fixture
def owner(db):
    return User.objects.create_user('fetch_owner', 'fetch_owner@example.com', 'not-a-real-password')


@pytest.fixture
def other(db):
    return User.objects.create_user('fetch_other', 'fetch_other@example.com', 'not-a-real-password')


def provider(owner, shared, name='fetch provider'):
    return SearchProvider.objects.create(
        name=name, owner=owner, shared=shared,
        page_fetch_config_json={'cache': 'false', 'headers': {'Authorization': HEADER}})


def found(user, url=TARGET, provider_id=0):
    """Give user a search whose results list url, returned by provider_id."""
    search = Search.objects.create(owner=user, query_string='q', status='FULL_RESULTS_READY')
    return Result.objects.create(owner=user, search_id=search, provider_id=provider_id, searchprovider='p',
                                 json_results=[{'title': 'other', 'url': 'http://documents.example.invalid/other'},
                                               {'title': 'report', 'url': url}])


def fetch(user, url=TARGET, provider_id=None):
    """Call fetch-document as user; return (response, upstream calls)."""
    client = APIClient()
    client.force_authenticate(user=user)
    upstream = mock.Mock(status_code=200, content=b'document body', text='document body',
                         headers={'Content-Type': 'text/plain'})
    params = {'url': url}
    if provider_id is not None:
        params['provider_id'] = provider_id
    with mock.patch('swirl.web_page.requests.get', return_value=upstream) as get:
        response = client.get(URL, params)
    return response, get


def headers_sent(get):
    assert get.call_count == 1
    return get.call_args.kwargs.get('headers') or {}


class TestOnlyUrlsFromTheCallersResults:

    def test_a_url_from_the_callers_results_is_fetched(self, other):
        found(other)

        response, get = fetch(other)

        assert response.status_code == 200
        assert response.content == b'document body'
        assert get.call_args.args[0] == TARGET

    @pytest.mark.parametrize('url', [
        'http://127.0.0.1:6379/info',
        'http://169.254.169.254/latest/meta-data/',
        'http://documents.example.invalid/reports/annual report.txt.bak',
        'http://elsewhere.example.invalid/reports/annual report.txt',
    ])
    def test_any_other_url_is_not_fetched(self, other, url):
        found(other)

        response, get = fetch(other, url=url)

        assert response.status_code == 404
        assert get.call_count == 0

    def test_a_url_from_another_users_results_is_not_fetched(self, owner, other):
        found(owner)

        response, get = fetch(other)

        assert response.status_code == 404
        assert get.call_count == 0

    def test_a_user_with_no_results_fetches_nothing(self, other):
        response, get = fetch(other)

        assert response.status_code == 404
        assert get.call_count == 0

    @pytest.mark.parametrize('asked', [
        'http://documents.example.invalid/reports/annual%20report.txt',
        'http://documents.example.invalid/reports/annual report.txt#page=2',
        'http://documents.example.invalid/reports/annual report.txt/',
    ])
    def test_the_same_document_written_another_way_is_fetched(self, other, asked):
        found(other)

        response, _ = fetch(other, url=asked)

        assert response.status_code == 200

    def test_a_missing_url_is_still_a_bad_request(self, other):
        client = APIClient()
        client.force_authenticate(user=other)

        assert client.get(URL).status_code == 400


class TestProviderSettings:

    def test_owner_fetch_uses_the_headers_of_the_provider_that_returned_the_url(self, owner):
        source = provider(owner, shared=False)
        found(owner, provider_id=source.id)

        response, get = fetch(owner, provider_id=source.id)

        assert response.status_code == 200
        assert headers_sent(get).get('Authorization') == HEADER

    def test_shared_provider_headers_are_used_for_a_url_it_returned(self, owner, other):
        source = provider(owner, shared=True)
        found(other, provider_id=source.id)

        _, get = fetch(other, provider_id=source.id)

        assert headers_sent(get).get('Authorization') == HEADER

    def test_shared_provider_headers_are_not_used_for_a_url_another_provider_returned(self, owner, other):
        source = provider(owner, shared=True)
        elsewhere = provider(other, shared=False, name='the callers own provider')
        found(other, provider_id=elsewhere.id)

        response, get = fetch(other, provider_id=source.id)

        assert response.status_code == 200
        assert HEADER not in str(headers_sent(get))

    def test_another_users_private_provider_is_not_used(self, owner, other):
        source = provider(owner, shared=False)
        found(other, provider_id=source.id)

        response, get = fetch(other, provider_id=source.id)

        assert response.status_code == 200
        assert HEADER not in str(headers_sent(get))

    def test_fetch_without_a_provider_sends_no_provider_headers(self, owner, other):
        source = provider(owner, shared=True)
        found(other, provider_id=source.id)

        _, get = fetch(other)

        assert 'Authorization' not in headers_sent(get)
