"""
What the AIProvider API returns about a provider depends on who asks:
- a superuser gets everything;
- the owner gets their own provider (the list leaves out its api_key);
- another user gets a shared provider without anything it signs in with:
  the api_key and config, which can hold request headers and keys.
"""

import pytest
from django.contrib.auth.models import Permission, User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from swirl.models import AIProvider

CONFIG = {'headers': {'Authorization': 'Bearer config-header-value'}, 'SOME_API_KEY': 'config-key-value'}
VALUES = ('api-key-value', 'config-header-value', 'config-key-value')


def user(name, superuser=False):
    if superuser:
        return User.objects.create_superuser(name, f'{name}@example.com', 'not-a-real-password')
    account = User.objects.create_user(name, f'{name}@example.com', 'not-a-real-password')
    account.user_permissions.set(Permission.objects.filter(
        content_type__app_label='swirl', codename='view_aiprovider'))
    return User.objects.get(pk=account.pk)


@pytest.fixture
def owner(db):
    return user('ai_owner')


@pytest.fixture
def reader(db):
    return user('ai_reader')


@pytest.fixture
def provider(owner):
    return AIProvider.objects.create(name='shared model', owner=owner, shared=True, active=True,
                                     api_key='api-key-value', model='some-model', tags=['rag'],
                                     defaults=['rag'], config=CONFIG)


def get(as_user, path):
    client = APIClient()
    client.force_login(as_user)
    client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.get_or_create(user=as_user)[0].key}')
    response = client.get(path)
    if response.status_code == 403:
        client = APIClient()
        client.force_authenticate(user=as_user)
        response = client.get(path)
    assert response.status_code == 200, response.status_code
    return response


def row_for(response, provider):
    rows = response.json()
    return next(r for r in rows if r['id'] == provider.id)


@pytest.mark.parametrize('prefix', ['/swirl/aiproviders/', '/swirl/sapi/ai_providers/'])
class TestAnotherUsersSharedProvider:

    def test_list_leaves_out_config_and_key(self, reader, provider, prefix):
        response = get(reader, prefix)

        row = row_for(response, provider)
        assert row['name'] == 'shared model' and row['model'] == 'some-model'
        assert 'config' not in row and 'api_key' not in row
        assert not any(value in response.content.decode() for value in VALUES)

    def test_retrieve_leaves_out_config_and_key(self, reader, provider, prefix):
        response = get(reader, f'{prefix}{provider.id}/')

        assert response.json()['name'] == 'shared model'
        assert 'config' not in response.json() and 'api_key' not in response.json()
        assert not any(value in response.content.decode() for value in VALUES)


def test_owner_still_retrieves_the_whole_provider(owner, provider):
    row = get(owner, f'/swirl/aiproviders/{provider.id}/').json()

    assert row['api_key'] == 'api-key-value'
    assert row['config'] == CONFIG


def test_owner_list_is_unchanged(owner, provider):
    row = row_for(get(owner, '/swirl/aiproviders/'), provider)

    assert 'api_key' not in row
    assert row['config'] == CONFIG


def test_superuser_list_is_unchanged(provider):
    row = row_for(get(user('ai_admin', superuser=True), '/swirl/aiproviders/'), provider)

    assert row['api_key'] == 'api-key-value'
    assert row['config'] == CONFIG
