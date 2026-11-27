"""
The index admin actions end or unblock an ingest run. They are offered to, and
run for, staff who hold the permission the index API asks for; staff who may
only view the rows do not get them.
"""

from unittest import mock

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client

from swirl.models import SearchIndexGeneration

CHANGELIST = '/admin/swirl/searchindexgeneration/'


def staff(name, *codenames):
    account = User.objects.create_user(name, f'{name}@example.com', 'not-a-real-password', is_staff=True)
    account.user_permissions.set(Permission.objects.filter(
        content_type__app_label='swirl', codename__in=codenames))
    return User.objects.get(pk=account.pk)


@pytest.fixture
def open_row(db):
    return SearchIndexGeneration.objects.create(
        type='catalog', generation='20260101T000000', state=SearchIndexGeneration.STATE_OPEN)


def run_abort(account, row):
    client = Client()
    client.force_login(account)
    with mock.patch('swirl.tantivy_index.manager.default_manager') as manager:
        response = client.post(CHANGELIST, {
            'action': 'abort_open_generations', '_selected_action': [str(row.pk)]}, follow=True)
    row.refresh_from_db()
    return response, manager


def test_view_only_staff_cannot_abort(open_row):
    response, manager = run_abort(staff('index_viewer', 'view_searchindexgeneration'), open_row)

    assert open_row.state == SearchIndexGeneration.STATE_OPEN
    assert not manager.abort.called
    assert not manager.rollback_begin.called


def test_view_only_staff_are_not_offered_the_actions(open_row):
    client = Client()
    client.force_login(staff('index_viewer2', 'view_searchindexgeneration'))
    html = client.get(CHANGELIST).content.decode()

    assert 'abort_open_generations' not in html
    assert 'clear_stale_open_locks' not in html


def test_staff_with_the_ingest_permission_can_abort(open_row):
    response, manager = run_abort(
        staff('index_operator', 'view_searchindexgeneration', 'change_searchprovider'), open_row)

    assert open_row.state == SearchIndexGeneration.STATE_ABORTED
    assert manager.abort.called
