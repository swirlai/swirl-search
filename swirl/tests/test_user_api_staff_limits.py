"""
Staff accounts may read users and groups through the API. Adding, changing or
deleting needs the model permission for that action, as in the admin, and
only a superuser may change or delete a superuser.
"""

import pytest
from django.contrib.auth.models import Group, Permission, User
from rest_framework.test import APIClient

USERS = '/swirl/users/'
GROUPS = '/swirl/groups/'


def staff(name, *codenames):
    account = User.objects.create_user(name, f'{name}@example.com', 'not-a-real-password', is_staff=True)
    account.user_permissions.set(Permission.objects.filter(
        content_type__app_label='auth', codename__in=codenames))
    return User.objects.get(pk=account.pk)


def client_for(account):
    client = APIClient()
    client.force_login(account)
    return client


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser('root_account', 'root_account@example.com', 'not-a-real-password')


@pytest.fixture
def ordinary(db):
    return User.objects.create_user('ordinary', 'ordinary@example.com', 'not-a-real-password')


@pytest.mark.django_db
class TestStaffWithoutModelPermissions:

    def test_can_read(self, ordinary):
        client = client_for(staff('staff_plain'))

        assert client.get(USERS).status_code == 200
        assert client.get(GROUPS).status_code == 200

    def test_cannot_add_change_or_delete_users(self, ordinary):
        client = client_for(staff('staff_plain'))

        assert client.post(USERS, {'username': 'made', 'email': 'made@example.com', 'groups': []},
                           format='json').status_code == 403
        assert client.patch(f'{USERS}{ordinary.id}/', {'email': 'new@example.com'}, format='json').status_code == 403
        assert client.delete(f'{USERS}{ordinary.id}/').status_code == 403
        assert User.objects.get(pk=ordinary.pk).email == 'ordinary@example.com'
        assert not User.objects.filter(username='made').exists()

    def test_cannot_add_or_delete_groups(self):
        group = Group.objects.create(name='kept')
        client = client_for(staff('staff_plain'))

        assert client.post(GROUPS, {'name': 'made'}, format='json').status_code == 403
        assert client.delete(f'{GROUPS}{group.id}/').status_code == 403
        assert Group.objects.filter(name='kept').exists()


@pytest.mark.django_db
class TestStaffWithModelPermissions:

    def test_can_change_and_delete_an_ordinary_user(self, ordinary):
        client = client_for(staff('staff_manager', 'change_user', 'delete_user'))

        assert client.patch(f'{USERS}{ordinary.id}/', {'email': 'new@example.com'}, format='json').status_code == 200
        assert client.delete(f'{USERS}{ordinary.id}/').status_code == 204

    def test_cannot_change_or_delete_a_superuser(self, superuser):
        client = client_for(staff('staff_manager', 'change_user', 'delete_user'))

        assert client.patch(f'{USERS}{superuser.id}/', {'email': 'taken@example.com'}, format='json').status_code == 403
        assert client.delete(f'{USERS}{superuser.id}/').status_code == 403
        assert User.objects.get(pk=superuser.pk).email == 'root_account@example.com'

    def test_can_still_read_a_superuser(self, superuser):
        client = client_for(staff('staff_manager', 'change_user'))

        assert client.get(f'{USERS}{superuser.id}/').status_code == 200


@pytest.mark.django_db
def test_superuser_can_change_another_superuser(superuser):
    other = User.objects.create_superuser('second_root', 'second_root@example.com', 'not-a-real-password')

    response = client_for(superuser).patch(f'{USERS}{other.id}/', {'email': 'moved@example.com'}, format='json')

    assert response.status_code == 200
