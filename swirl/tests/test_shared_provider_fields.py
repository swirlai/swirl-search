"""
What the SearchProvider API returns about a provider depends on who asks:
- a superuser gets everything;
- the owner gets their own provider (the list leaves out its credentials);
- another user gets a shared provider without anything the connector signs
  in with: credentials, request headers, page-fetch settings and url.
"""

import pytest
from django.contrib.auth.models import Permission, User
from rest_framework.test import APIClient

from swirl.models import SearchProvider

WITHHELD = ('credentials', 'http_request_headers', 'page_fetch_config_json', 'url')
VALUES = ('credential-value-1', 'header-value-2', 'page-fetch-value-3', 'connection-value-4')


def user(name, superuser=False):
    if superuser:
        return User.objects.create_superuser(name, f'{name}@example.com', 'not-a-real-password')
    account = User.objects.create_user(name, f'{name}@example.com', 'not-a-real-password')
    account.user_permissions.set(Permission.objects.filter(
        content_type__app_label='swirl', codename='view_searchprovider'))
    return User.objects.get(pk=account.pk)


@pytest.fixture
def owner(db):
    return user('fields_owner')


@pytest.fixture
def reader(db):
    return user('fields_reader')


@pytest.fixture
def provider(owner):
    return SearchProvider.objects.create(
        name='shared source', owner=owner, shared=True, connector='RequestsGet',
        credentials='key=credential-value-1',
        http_request_headers={'Authorization': 'Bearer header-value-2'},
        page_fetch_config_json={'cache': 'false', 'headers': {'Cookie': 'page-fetch-value-3'}},
        url='host:5432:db:user:connection-value-4')


def get(as_user, path):
    client = APIClient()
    client.force_authenticate(user=as_user)
    response = client.get(path)
    assert response.status_code == 200
    return response


@pytest.mark.parametrize('prefix', ['/swirl/searchproviders/', '/swirl/sapi/searchproviders/'])
class TestAnotherUsersSharedProvider:

    def client_get(self, reader, path):
        client = APIClient()
        client.force_authenticate(user=reader)
        if '/sapi/' in path:
            from rest_framework.authtoken.models import Token
            client.force_authenticate(user=None)
            client.force_login(reader)
            client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.get_or_create(user=reader)[0].key}')
        response = client.get(path)
        assert response.status_code == 200, response.status_code
        return response

    def test_list_leaves_out_what_the_connector_signs_in_with(self, reader, provider, prefix):
        response = self.client_get(reader, prefix)

        row = next(r for r in response.json() if r['id'] == provider.id)
        assert row['name'] == 'shared source' and row['connector'] == 'RequestsGet'
        assert not set(WITHHELD) & set(row)
        assert not any(value in response.content.decode() for value in VALUES)

    def test_retrieve_leaves_out_what_the_connector_signs_in_with(self, reader, provider, prefix):
        response = self.client_get(reader, f'{prefix}{provider.id}/')

        assert response.json()['name'] == 'shared source'
        assert not set(WITHHELD) & set(response.json())
        assert not any(value in response.content.decode() for value in VALUES)


def test_owner_still_retrieves_the_whole_provider(owner, provider):
    row = get(owner, f'/swirl/searchproviders/{provider.id}/').json()

    assert row['credentials'] == 'key=credential-value-1'
    assert row['url'] == 'host:5432:db:user:connection-value-4'
    assert row['http_request_headers'] == {'Authorization': 'Bearer header-value-2'}


def test_owner_list_is_unchanged(owner, provider):
    row = next(r for r in get(owner, '/swirl/searchproviders/').json() if r['id'] == provider.id)

    assert 'credentials' not in row
    assert row['url'] == 'host:5432:db:user:connection-value-4'
    assert row['http_request_headers'] == {'Authorization': 'Bearer header-value-2'}
    assert row['page_fetch_config_json']['headers'] == {'Cookie': 'page-fetch-value-3'}


def test_superuser_list_is_unchanged(provider):
    admin = user('fields_admin', superuser=True)

    row = next(r for r in get(admin, '/swirl/searchproviders/').json() if r['id'] == provider.id)

    assert row['credentials'] == 'key=credential-value-1'
    assert row['url'] == 'host:5432:db:user:connection-value-4'
