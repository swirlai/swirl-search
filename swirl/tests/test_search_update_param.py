"""
?update=<search id> on the search route marks the caller's stored search for
an update, runs it and redirects to its results.
"""

from unittest import mock

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client

from swirl.models import Search

PERMISSIONS = ['view_search', 'add_search', 'change_search', 'view_result', 'change_result']


def user_with_permissions(name):
    account = User.objects.create_user(name, f'{name}@example.com', 'not-a-real-password')
    account.user_permissions.set(Permission.objects.filter(
        content_type__app_label='swirl', codename__in=PERMISSIONS))
    return User.objects.get(pk=account.pk)


@pytest.fixture
def user(db):
    return user_with_permissions('update_user')


@pytest.fixture
def search(user):
    return Search.objects.create(query_string='stored query', owner=user, status='FULL_RESULTS_READY')


@pytest.fixture
def run_search():
    with mock.patch('swirl.views.run_search', return_value=True) as patched:
        yield patched


def get(user, path):
    client = Client()
    client.force_login(user)
    return client.get(path)


def test_update_marks_the_search_runs_it_and_redirects(user, search, run_search):
    response = get(user, f'/swirl/search/?update={search.id}')

    search.refresh_from_db()
    assert response.status_code == 302
    assert response['Location'] == f'/swirl/results?search_id={search.id}'
    assert search.status == 'UPDATE_SEARCH'
    assert run_search.call_count == 1
    assert str(run_search.call_args.args[0]) == str(search.id)


def test_another_users_search_is_not_found(user, search, run_search):
    response = get(user_with_permissions('update_other'), f'/swirl/search/?update={search.id}')

    search.refresh_from_db()
    assert response.status_code == 404
    assert search.status == 'FULL_RESULTS_READY'
    assert not run_search.called
