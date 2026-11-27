"""
The API token admin shows the full key to a superuser only, and only a
superuser works with a single token. Other staff who may view tokens get the
list, with the last four characters of each key.
"""

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client
from rest_framework.authtoken.models import Token

PAGE = '/admin/authtoken/tokenproxy/'


def page(account):
    client = Client()
    client.force_login(account)
    response = client.get(PAGE)
    assert response.status_code == 200, response.status_code
    return response.content.decode()


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser('token_root', 'token_root@example.com', 'not-a-real-password')


@pytest.fixture
def token(superuser):
    return Token.objects.create(user=superuser)


def token_staff(*actions):
    account = User.objects.create_user('token_staff', 'token_staff@example.com', 'not-a-real-password', is_staff=True)
    account.user_permissions.set(Permission.objects.filter(
        content_type__app_label='authtoken', codename__in=[f'{a}_tokenproxy' for a in actions]))
    return User.objects.get(pk=account.pk)


def test_view_only_staff_do_not_get_the_key(token):
    html = page(token_staff('view'))

    assert token.key not in html
    assert token.key[-4:] in html
    assert 'token_root' in html


def test_staff_who_can_change_tokens_do_not_get_the_key(token):
    html = page(token_staff('view', 'add', 'change', 'delete'))

    assert token.key not in html


def test_superuser_sees_the_key(superuser, token):
    assert token.key in page(superuser)


@pytest.mark.parametrize('path', ['{pk}/change/', '{pk}/delete/', 'add/'])
def test_staff_cannot_open_add_or_delete_a_token(token, path):
    client = Client()
    client.force_login(token_staff('view', 'add', 'change', 'delete'))

    response = client.get(PAGE + path.format(pk=token.user_id))

    assert response.status_code == 403
    assert token.key not in response.content.decode()


def test_superuser_can_open_a_token(superuser, token):
    client = Client()
    client.force_login(superuser)

    assert client.get(f'{PAGE}{token.user_id}/change/').status_code == 200
