"""
The admin activity page lists users' queries. It opens for staff who may view
searches and answers 403 for staff who may not.
"""

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client

from swirl.models import Result, Search

QUERY = 'activity page query text'


def staff(name, *codenames):
    account = User.objects.create_user(name, f'{name}@example.com', 'not-a-real-password', is_staff=True)
    account.user_permissions.set(Permission.objects.filter(
        content_type__app_label='swirl', codename__in=codenames))
    return User.objects.get(pk=account.pk)


def activity_page(account):
    client = Client()
    client.force_login(account)
    return client.get('/admin/activity/')


@pytest.fixture
def empty_search(db):
    owner = User.objects.create_user('activity_owner', 'activity_owner@example.com', 'not-a-real-password')
    search = Search.objects.create(query_string=QUERY, owner=owner, status='FULL_RESULTS_READY')
    Result.objects.create(search_id=search, owner=owner, searchprovider='source', retrieved=0, found=0)
    return search


def test_staff_without_the_view_permission_get_403(empty_search):
    response = activity_page(staff('activity_other', 'view_searchprovider'))

    assert response.status_code == 403
    assert QUERY not in response.content.decode()


def test_staff_with_the_view_permission_see_the_page(empty_search):
    response = activity_page(staff('activity_viewer', 'view_search'))

    assert response.status_code == 200
    assert QUERY in response.content.decode()


def test_superuser_sees_the_page(empty_search):
    response = activity_page(User.objects.create_superuser(
        'activity_admin', 'activity_admin@example.com', 'not-a-real-password'))

    assert response.status_code == 200
