"""
The authenticators API lists the sign-in services a user's sources need.
Creating, changing or deleting an Authenticator record needs the matching
model permission, as it does in the admin.
"""

import pytest
from django.contrib.auth.models import Permission, User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from swirl.models import Authenticator

URL = '/swirl/sapi/authenticators/'


def client_for(name, permissions=()):
    account = User.objects.create_user(name, f'{name}@example.com', 'not-a-real-password')
    account.user_permissions.set(Permission.objects.filter(
        content_type__app_label='swirl', codename__in=permissions))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=account).key}')
    return client


@pytest.mark.django_db
class TestAuthenticatorsApi:

    def test_signed_in_user_can_list(self):
        assert client_for('auth_reader').get(URL).status_code == 200

    def test_user_without_permission_cannot_create(self):
        response = client_for('auth_plain').post(URL, {'name': 'added'}, format='json')

        assert response.status_code == 403
        assert not Authenticator.objects.filter(name='added').exists()

    def test_user_without_permission_cannot_change_or_delete(self):
        record = Authenticator.objects.create(name='original')
        client = client_for('auth_plain')

        assert client.patch(f'{URL}{record.pk}/', {'name': 'changed'}, format='json').status_code == 403
        assert client.delete(f'{URL}{record.pk}/').status_code == 403
        assert Authenticator.objects.get(pk=record.pk).name == 'original'

    def test_anonymous_caller_cannot_create(self):
        response = APIClient().post(URL, {'name': 'anonymous'}, format='json')

        assert response.status_code in (401, 403)
        assert not Authenticator.objects.filter(name='anonymous').exists()

    def test_user_with_permission_can_create_change_and_delete(self):
        client = client_for('auth_manager', (
            'add_authenticator', 'change_authenticator', 'delete_authenticator'))

        created = client.post(URL, {'name': 'managed'}, format='json')
        assert created.status_code == 201
        detail = f"{URL}{created.json()['id']}/"
        assert client.patch(detail, {'name': 'renamed'}, format='json').status_code == 200
        assert client.delete(detail).status_code == 204
