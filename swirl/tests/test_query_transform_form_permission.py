"""
The query-transform upload form creates a QueryTransform for the caller. It
needs a signed-in user who holds the add permission, as the API does.
"""

import pytest
from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from swirl.models import QueryTransform

URL = '/swirl/query_transform_form/'


def upload(name):
    return {'name': name, 'content_type': 'rewrite',
            'file': SimpleUploadedFile('rules.csv', b'foo,bar', content_type='text/csv')}


def user(name, can_add):
    account = User.objects.create_user(name, f'{name}@example.com', 'not-a-real-password')
    if can_add:
        account.user_permissions.set(Permission.objects.filter(
            content_type__app_label='swirl', codename='add_querytransform'))
    return User.objects.get(pk=account.pk)


def client_for(account):
    client = Client()
    client.force_login(account)
    return client


@pytest.mark.django_db
class TestQueryTransformForm:

    def test_user_with_the_permission_can_upload(self):
        account = user('form_adder', can_add=True)

        response = client_for(account).post(URL, upload('allowed'))

        assert response.status_code == 302
        assert QueryTransform.objects.get(name='allowed').owner == account

    def test_user_with_the_permission_sees_the_form(self):
        assert client_for(user('form_viewer', can_add=True)).get(URL).status_code == 200

    def test_user_without_the_permission_is_refused(self):
        client = client_for(user('form_plain', can_add=False))

        assert client.get(URL).status_code == 403
        assert client.post(URL, upload('refused')).status_code == 403
        assert not QueryTransform.objects.filter(name='refused').exists()

    def test_anonymous_caller_is_sent_to_sign_in(self):
        response = Client().post(URL, upload('anonymous'))

        assert response.status_code == 302
        assert '/api-auth/login' in response['Location']
        assert not QueryTransform.objects.filter(name='anonymous').exists()
