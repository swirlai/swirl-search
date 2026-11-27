"""
The provider test action sends a request to the source. An inactive provider
is tested by its owner or a superuser only, and a browser request on the
session cookie is refused when the browser marks it as started by another
site.
"""

from unittest import mock

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client

from swirl.models import Search, SearchProvider


def account(name, superuser=False):
    if superuser:
        return User.objects.create_superuser(name, f'{name}@example.com', 'not-a-real-password')
    created = User.objects.create_user(name, f'{name}@example.com', 'not-a-real-password')
    created.user_permissions.set(Permission.objects.filter(
        content_type__app_label='swirl', codename__in=['view_searchprovider', 'add_searchprovider']))
    return User.objects.get(pk=created.pk)


def provider(owner, active):
    return SearchProvider.objects.create(
        owner=owner, name='source under test', shared=True, active=active, connector='RequestsGet',
        url='https://source.example.invalid/search', query_template='{url}?q={query_string}')


def run_test_action(user, source, **headers):
    client = Client()
    client.force_login(user)
    with mock.patch('swirl.connectors.requestsget.requests.get', side_effect=Exception('no network in tests')) as sent:
        response = client.get(f'/swirl/searchproviders/{source.id}/test/?q=probe', **headers)
    return response, sent


@pytest.mark.django_db
def test_another_user_cannot_test_an_inactive_shared_provider():
    source = provider(account('test_owner'), active=False)

    response, sent = run_test_action(account('test_other'), source)

    assert response.status_code == 403
    assert not sent.called
    assert Search.objects.count() == 0


@pytest.mark.django_db
def test_the_owner_can_test_an_inactive_provider():
    owner = account('test_owner2')

    response, sent = run_test_action(owner, provider(owner, active=False))

    assert response.status_code == 200
    assert sent.called


@pytest.mark.django_db
def test_a_superuser_can_test_an_inactive_provider():
    source = provider(account('test_owner3'), active=False)

    response, sent = run_test_action(account('test_root', superuser=True), source)

    assert response.status_code == 200
    assert sent.called


@pytest.mark.django_db
def test_another_user_can_test_an_active_shared_provider():
    source = provider(account('test_owner4'), active=True)

    response, sent = run_test_action(account('test_other4'), source)

    assert response.status_code == 200
    assert sent.called


@pytest.mark.django_db
def test_a_cross_site_request_on_the_session_cookie_is_refused():
    owner = account('test_owner5')

    response, sent = run_test_action(owner, provider(owner, active=True), HTTP_SEC_FETCH_SITE='cross-site')

    assert response.status_code == 403
    assert not sent.called
    assert Search.objects.count() == 0
