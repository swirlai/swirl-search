"""
The admin masks a provider's secret fields for an account that can edit it.
An account that may only view it does not see those fields at all, and the
stored value is not in the page for anyone.
"""

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client

from swirl.models import AIProvider

KEY = 'admin-page-api-key-value'


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
    return User.objects.create_superuser('page_owner', 'page_owner@example.com', 'not-a-real-password')


@pytest.fixture
def ai_provider(owner):
    return AIProvider.objects.create(name='admin page model', owner=owner, api_key=KEY, model='some-model')


def test_view_only_staff_do_not_see_the_api_key(ai_provider):
    html = page(staff('ai_viewer', 'view_aiprovider'), f'/admin/swirl/aiprovider/{ai_provider.id}/change/')

    assert 'admin page model' in html
    assert KEY not in html


def test_staff_who_can_change_it_get_a_masked_field(ai_provider):
    html = page(staff('ai_editor', 'view_aiprovider', 'change_aiprovider'),
                f'/admin/swirl/aiprovider/{ai_provider.id}/change/')

    assert KEY not in html
    assert 'name="api_key"' in html and 'type="password"' in html


def test_superuser_page_is_unchanged(owner, ai_provider):
    html = page(owner, f'/admin/swirl/aiprovider/{ai_provider.id}/change/')

    assert KEY not in html
    assert 'name="api_key"' in html


def test_view_only_staff_still_see_the_other_fields(ai_provider):
    html = page(staff('ai_viewer2', 'view_aiprovider'), f'/admin/swirl/aiprovider/{ai_provider.id}/change/')

    assert 'some-model' in html


def test_saving_with_the_field_left_blank_keeps_the_key(owner, ai_provider):
    client = Client()
    client.force_login(owner)
    response = client.post(f'/admin/swirl/aiprovider/{ai_provider.id}/change/', {
        'name': 'renamed model', 'owner': owner.id, 'shared': 'on', 'active': 'on',
        'model': 'some-model', 'api_key': '', 'config': '{}', 'prompt_overrides': '{}',
    })

    ai_provider.refresh_from_db()
    assert response.status_code in (200, 302)
    assert ai_provider.api_key == KEY
