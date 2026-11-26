"""
fetch-document can be given a provider_id, whose page-fetch settings (request
headers among them) are then used for the fetch. Those settings are used only
for a caller who could search that provider: its owner, or anyone when the
provider is shared.
"""

from unittest import mock

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from swirl.models import SearchProvider

URL = '/swirl/fetch-document/'
TARGET = 'http://documents.example.invalid/report.txt'
HEADER = 'Bearer provider-page-fetch-value'


@pytest.fixture
def owner(db):
    return User.objects.create_user('fetch_owner', 'fetch_owner@example.com', 'not-a-real-password')


@pytest.fixture
def other(db):
    return User.objects.create_user('fetch_other', 'fetch_other@example.com', 'not-a-real-password')


def provider(owner, shared):
    return SearchProvider.objects.create(
        name=f'fetch provider shared={shared}', owner=owner, shared=shared,
        page_fetch_config_json={'cache': 'false', 'headers': {'Authorization': HEADER}})


def fetch(user, provider_id=None):
    """Call fetch-document as user; return (response, headers sent upstream)."""
    client = APIClient()
    client.force_authenticate(user=user)
    upstream = mock.Mock(status_code=200, content=b'document body', text='document body',
                         headers={'Content-Type': 'text/plain'})
    params = {'url': TARGET}
    if provider_id is not None:
        params['provider_id'] = provider_id
    with mock.patch('swirl.web_page.requests.get', return_value=upstream) as get:
        response = client.get(URL, params)
    assert get.call_count == 1
    return response, get.call_args.kwargs.get('headers') or {}


def test_owner_fetch_uses_the_providers_headers(owner):
    response, sent = fetch(owner, provider(owner, shared=False).id)

    assert response.status_code == 200
    assert sent.get('Authorization') == HEADER


def test_shared_provider_headers_are_used_for_any_user(owner, other):
    response, sent = fetch(other, provider(owner, shared=True).id)

    assert response.status_code == 200
    assert sent.get('Authorization') == HEADER


def test_another_users_private_provider_is_not_used(owner, other):
    response, sent = fetch(other, provider(owner, shared=False).id)

    assert response.status_code == 200
    assert 'Authorization' not in sent
    assert HEADER not in str(sent)


def test_private_provider_and_unknown_id_fetch_the_same_way(owner, other):
    _, private = fetch(other, provider(owner, shared=False).id)
    _, unknown = fetch(other, 999999)

    assert private == unknown


def test_fetch_without_a_provider_is_unchanged(other):
    response, sent = fetch(other)

    assert response.status_code == 200
    assert 'Authorization' not in sent
