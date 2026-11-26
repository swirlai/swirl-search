"""
The subscriber re-runs every user's subscribed searches. One search it cannot
update must not stop the rest.
"""

from unittest import mock

import pytest
from django.contrib.auth.models import Permission, User

from swirl import subscriber as subscriber_module
from swirl.models import Search
from swirl.subscriber import subscriber


def owner(name, can_update=True):
    account = User.objects.create_user(name, f'{name}@example.com', 'not-a-real-password')
    if can_update:
        account.user_permissions.set(Permission.objects.filter(
            content_type__app_label='swirl', codename__in=('change_search', 'change_result')))
    return User.objects.get(pk=account.pk)


def subscribed(account):
    return Search.objects.create(
        owner=account, query_string='q', subscribe=True, status='FULL_RESULTS_READY')


@pytest.fixture
def no_sources():
    with mock.patch.object(subscriber_module, 'get_query_selected_provider_list', return_value=[]):
        yield


@pytest.mark.django_db
def test_subscribed_searches_are_rerun(no_sources):
    first, second = subscribed(owner('sub_one')), subscribed(owner('sub_two'))

    with mock.patch.object(subscriber_module, 'run_search', return_value=True) as run:
        assert subscriber() is True

    assert sorted(call.args[0] for call in run.call_args_list) == [first.id, second.id]


@pytest.mark.django_db
def test_one_failing_search_does_not_stop_the_others(no_sources):
    searches = {subscribed(owner('sub_one')).id, subscribed(owner('sub_two')).id}
    attempted, updated = [], []

    def run(search_id, session_data):
        attempted.append(search_id)
        if len(attempted) == 1:
            raise RuntimeError('cannot update this one')
        updated.append(search_id)
        return True

    with mock.patch.object(subscriber_module, 'run_search', side_effect=run):
        assert subscriber() is True

    assert set(attempted) == searches
    assert len(updated) == 1


@pytest.mark.django_db
def test_owner_without_permission_is_unsubscribed_and_the_rest_continue(no_sources):
    refused, healthy = subscribed(owner('sub_plain', can_update=False)), subscribed(owner('sub_two'))

    with mock.patch.object(subscriber_module, 'run_search', return_value=True) as run:
        subscriber()

    refused.refresh_from_db()
    assert refused.subscribe is False
    assert refused.status == 'ERR_SUBSCRIBE_PERMISSIONS'
    assert [call.args[0] for call in run.call_args_list] == [healthy.id]
