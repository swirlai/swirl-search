"""
Tests for who may use the user and group management API
(/swirl/users/ and /swirl/groups/): administrators (staff accounts) only.

Every request goes through the real URL, middleware and view.
"""

import pytest
from django.contrib.auth.models import Group, User
from rest_framework.test import APIClient

PASSWORD = 'not-a-real-password'

USERS = '/swirl/users/'
GROUPS = '/swirl/groups/'


@pytest.fixture
def admin(db):
    return User.objects.create_superuser('admin', 'admin@example.com', PASSWORD)


@pytest.fixture
def regular(db):
    return User.objects.create_user('regular', 'regular@example.com', PASSWORD)


@pytest.fixture
def group(db):
    return Group.objects.create(name='existing-group')


def client_for(user=None):
    client = APIClient()
    if user is not None:
        assert client.login(username=user.username, password=PASSWORD)
    return client


def requests_for(admin, group):
    """Every operation the two endpoints offer, as (method, url, body)."""
    return [
        ('get', USERS, None),
        ('get', f'{USERS}{admin.id}/', None),
        ('post', USERS, {'username': 'created', 'email': 'created@example.com', 'groups': []}),
        ('put', f'{USERS}{admin.id}/', {'username': 'renamed', 'email': 'x@example.com', 'groups': []}),
        ('patch', f'{USERS}{admin.id}/', {'email': 'changed@example.com'}),
        ('delete', f'{USERS}{admin.id}/', None),
        ('get', GROUPS, None),
        ('get', f'{GROUPS}{group.id}/', None),
        ('post', GROUPS, {'name': 'created-group'}),
        ('put', f'{GROUPS}{group.id}/', {'name': 'renamed-group'}),
        ('patch', f'{GROUPS}{group.id}/', {'name': 'renamed-group'}),
        ('delete', f'{GROUPS}{group.id}/', None),
    ]


def snapshot():
    return (sorted(User.objects.values_list('username', 'email')),
            sorted(Group.objects.values_list('name', flat=True)))


@pytest.mark.django_db
@pytest.mark.parametrize('who', ['anonymous', 'regular'])
def test_only_administrators_may_use_the_user_and_group_api(who, admin, regular, group):
    client = client_for(regular if who == 'regular' else None)
    before = snapshot()

    for method, url, body in requests_for(admin, group):
        response = getattr(client, method)(url, body, format='json')
        assert response.status_code == 403, f'{who} {method.upper()} {url}'

    assert snapshot() == before


@pytest.mark.django_db
def test_regular_user_token_cannot_use_the_user_and_group_api(admin, regular, group):
    from rest_framework.authtoken.models import Token
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=regular).key}')
    before = snapshot()

    for method, url, body in requests_for(admin, group):
        response = getattr(client, method)(url, body, format='json')
        assert response.status_code == 403, f'{method.upper()} {url}'

    assert snapshot() == before


@pytest.mark.django_db
def test_administrator_can_list_users_and_groups(admin, regular, group):
    client = client_for(admin)

    users = client.get(USERS)
    groups = client.get(GROUPS)

    assert users.status_code == 200
    assert {u['username'] for u in users.json()['results']} == {'admin', 'regular'}
    assert groups.status_code == 200
    assert 'existing-group' in {g['name'] for g in groups.json()['results']}


@pytest.mark.django_db
def test_administrator_can_create_change_and_delete(admin, regular, group):
    client = client_for(admin)

    created = client.post(USERS, {'username': 'created', 'email': 'created@example.com',
                                  'groups': []}, format='json')
    assert created.status_code == 201
    assert User.objects.filter(username='created').exists()

    changed = client.patch(f'{USERS}{regular.id}/', {'email': 'changed@example.com'}, format='json')
    assert changed.status_code == 200
    regular.refresh_from_db()
    assert regular.email == 'changed@example.com'

    assert client.delete(f'{USERS}{regular.id}/').status_code == 204
    assert not User.objects.filter(username='regular').exists()

    assert client.post(GROUPS, {'name': 'created-group'}, format='json').status_code == 201
    assert client.delete(f'{GROUPS}{group.id}/').status_code == 204
    assert not Group.objects.filter(name='existing-group').exists()
