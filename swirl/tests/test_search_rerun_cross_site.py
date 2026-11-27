"""
?rerun= and ?update= on the search route change a stored search. A browser
request signed in by the session cookie alone is refused when the browser
marks it as started by another site. Requests from the same site, typed
addresses, and token or Basic callers are served as before.
"""

from unittest import mock

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client
from rest_framework.authtoken.models import Token

from swirl.models import Result, Search

PERMISSIONS = ['view_search', 'add_search', 'change_search',
               'view_result', 'add_result', 'change_result', 'delete_result']


@pytest.fixture
def user(db):
    account = User.objects.create_user('rerun_user', 'rerun_user@example.com', 'not-a-real-password')
    account.user_permissions.set(Permission.objects.filter(
        content_type__app_label='swirl', codename__in=PERMISSIONS))
    return User.objects.get(pk=account.pk)


@pytest.fixture
def search(user):
    stored = Search.objects.create(query_string='stored query', owner=user, status='FULL_RESULTS_READY')
    Result.objects.create(search_id=stored, owner=user, searchprovider='source', retrieved=1, found=1)
    return stored


@pytest.fixture
def run_search():
    with mock.patch('swirl.views.run_search', return_value=True) as patched:
        yield patched


def session_client(user):
    client = Client()
    client.force_login(user)
    return client


def test_cross_site_rerun_on_the_session_cookie_is_refused(user, search, run_search):
    response = session_client(user).get(f'/swirl/search/?rerun={search.id}', HTTP_SEC_FETCH_SITE='cross-site')

    assert response.status_code == 403
    assert Result.objects.filter(search_id=search).count() == 1
    assert not run_search.called


def test_cross_site_update_on_the_session_cookie_is_refused(user, search, run_search):
    response = session_client(user).get(f'/swirl/search/?update={search.id}', HTTP_SEC_FETCH_SITE='cross-site')

    assert response.status_code == 403
    assert not run_search.called


@pytest.mark.parametrize('headers', [
    {},
    {'HTTP_SEC_FETCH_SITE': 'none'},
    {'HTTP_SEC_FETCH_SITE': 'same-origin'},
    {'HTTP_SEC_FETCH_SITE': 'same-site'},
])
def test_rerun_from_the_same_site_or_a_typed_address_still_runs(user, search, run_search, headers):
    response = session_client(user).get(f'/swirl/search/?rerun={search.id}', **headers)

    assert response.status_code == 302
    assert Result.objects.filter(search_id=search).count() == 0
    assert run_search.called


def test_a_token_caller_is_not_affected(user, search, run_search):
    token = Token.objects.create(user=user)

    response = Client().get(f'/swirl/search/?rerun={search.id}',
                            HTTP_AUTHORIZATION=f'Token {token.key}', HTTP_SEC_FETCH_SITE='cross-site')

    assert response.status_code == 302
    assert run_search.called


def test_a_cross_site_link_can_still_start_a_new_search(user, run_search):
    response = session_client(user).get('/swirl/search/?q=linked+query', HTTP_SEC_FETCH_SITE='cross-site')

    assert response.status_code == 302
    assert Search.objects.filter(owner=user, query_string='linked query').count() == 1
