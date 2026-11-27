"""
The SearchProvider admin page leaves the connection fields off the page for an
account that may view a provider but not change it. An account that can change
it works with them as before.
"""

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client

from swirl.models import SearchProvider

CREDENTIALS = 'admin-page-credentials-value'
HEADER = 'admin-page-header-value'
FETCH_HEADER = 'admin-page-fetch-header-value'


def staff(name, *codenames):
    account = User.objects.create_user(name, f'{name}@example.com', 'not-a-real-password', is_staff=True)
    account.user_permissions.set(Permission.objects.filter(
        content_type__app_label='swirl', codename__in=codenames))
    return User.objects.get(pk=account.pk)


def page(account, path):
    client = Client()
    client.force_login(account)
    response = client.get(path)
    assert response.status_code == 200, response.status_code
    return response.content.decode()


@pytest.fixture
def owner(db):
    return User.objects.create_superuser('sp_page_owner', 'sp_page_owner@example.com', 'not-a-real-password')


@pytest.fixture
def provider(owner):
    return SearchProvider.objects.create(
        name='admin page source', owner=owner, connector='RequestsGet',
        url='https://source.example.com/search', credentials=CREDENTIALS,
        http_request_headers={'X-Source-Key': HEADER},
        page_fetch_config_json={'headers': {'X-Fetch-Key': FETCH_HEADER}},
    )


def change_page(provider):
    return f'/admin/swirl/searchprovider/{provider.id}/change/'


def test_view_only_staff_do_not_see_the_connection_fields(provider):
    html = page(staff('sp_viewer', 'view_searchprovider'), change_page(provider))

    assert 'admin page source' in html
    assert CREDENTIALS not in html
    assert HEADER not in html
    assert FETCH_HEADER not in html


def test_view_only_staff_still_see_the_other_fields(provider):
    html = page(staff('sp_viewer2', 'view_searchprovider'), change_page(provider))

    assert 'https://source.example.com/search' in html


def test_staff_who_can_change_it_still_edit_the_fields(provider):
    html = page(staff('sp_editor', 'view_searchprovider', 'change_searchprovider'), change_page(provider))

    assert 'name="credentials"' in html
    assert 'name="http_request_headers"' in html and HEADER in html
    assert 'name="page_fetch_config_json"' in html and FETCH_HEADER in html


def test_superuser_page_is_unchanged(owner, provider):
    html = page(owner, change_page(provider))

    assert 'name="credentials"' in html and CREDENTIALS in html
    assert HEADER in html
