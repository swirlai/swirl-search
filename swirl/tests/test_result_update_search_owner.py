"""
A Result belongs to one of its owner's searches. Updating it can move it to
another search of the same owner, not to a search that belongs to someone else.
"""

import pytest
from django.contrib.auth.models import Permission, User
from rest_framework.test import APIClient

from swirl.models import Result, Search

ITEM = {'title': 't', 'body': 'b', 'url': 'https://example.com/p', 'searchprovider': 'x',
        'searchprovider_rank': 1, 'swirl_score': 1, 'date_published': 'unknown'}


def user(name):
    account = User.objects.create_user(name, f'{name}@example.com', 'not-a-real-password')
    account.user_permissions.set(Permission.objects.filter(
        content_type__app_label='swirl', codename='change_result'))
    return User.objects.get(pk=account.pk)


def search_of(account):
    return Search.objects.create(owner=account, query_string='q', status='FULL_RESULTS_READY')


def update(account, result, search):
    client = APIClient()
    client.force_authenticate(account)
    body = {'search_id': search.id, 'searchprovider': 'x', 'json_results': [ITEM]}
    return client.patch(f'/swirl/results/{result.pk}/', body, format='json')


@pytest.mark.django_db
class TestResultUpdate:

    def test_result_cannot_be_moved_to_another_users_search(self):
        alice, bob = user('result_alice'), user('result_bob')
        theirs, mine = search_of(alice), search_of(bob)
        result = Result.objects.create(owner=bob, search_id=mine, searchprovider='x', json_results=[])

        response = update(bob, result, theirs)

        assert response.status_code == 404
        result.refresh_from_db()
        assert result.search_id_id == mine.id
        assert result.json_results == []
        assert not Result.objects.filter(search_id=theirs).exists()

    def test_result_can_be_updated_in_place(self):
        bob = user('result_bob')
        mine = search_of(bob)
        result = Result.objects.create(owner=bob, search_id=mine, searchprovider='x', json_results=[])

        assert update(bob, result, mine).status_code == 200
        result.refresh_from_db()
        assert result.json_results[0]['title'] == 't'

    def test_result_can_be_moved_to_another_search_of_the_same_owner(self):
        bob = user('result_bob')
        first, second = search_of(bob), search_of(bob)
        result = Result.objects.create(owner=bob, search_id=first, searchprovider='x', json_results=[])

        assert update(bob, result, second).status_code == 200
        result.refresh_from_db()
        assert result.search_id_id == second.id
