"""
Identity-provider token data kept in a browser session belongs to the user it
was stored for. Another user on the same session does not receive it, and
signing out removes it.
"""

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework.authtoken.models import Token

from swirl.authenticators.microsoft import Microsoft
from swirl.models import OauthToken
from swirl.views import get_session_data_with_db_fallback

FIRST_TOKEN = 'first-user-access-token'
FIRST_REFRESH = 'first-user-refresh-token'


class Session(dict):
    def save(self):
        pass


def request_for(user, session):
    return SimpleNamespace(user=user, session=session, headers={})


@pytest.fixture
def first(db):
    return User.objects.create_user('session_first', 'session_first@example.com', 'not-a-real-password')


@pytest.fixture
def second(db):
    return User.objects.create_user('session_second', 'session_second@example.com', 'not-a-real-password')


@pytest.fixture
def shared_session(first):
    session = Session()
    Microsoft().set_session_data(request_for(first, session), FIRST_TOKEN, FIRST_REFRESH, 9999999999)
    return session


def test_the_user_who_stored_it_gets_it_back(first, shared_session):
    data = get_session_data_with_db_fallback(request_for(first, shared_session))

    assert data['microsoft_access_token'] == FIRST_TOKEN


def test_another_user_on_the_same_session_does_not_get_it(second, shared_session):
    data = get_session_data_with_db_fallback(request_for(second, shared_session))

    assert not data or data.get('microsoft_access_token') != FIRST_TOKEN
    assert not OauthToken.objects.filter(owner=second).exists()


def test_data_stored_for_nobody_is_not_returned(second):
    session = Session(user={'microsoft_access_token': FIRST_TOKEN,
                            'microsoft_refresh_token': FIRST_REFRESH,
                            'microsoft_access_token_expiration_time': 9999999999})

    assert Microsoft().get_session_data(request_for(second, session)) is False
    assert not OauthToken.objects.filter(owner=second).exists()


def test_storing_for_a_new_user_replaces_the_earlier_data(first, second, shared_session):
    shared_session['user']['other_idp_token'] = 'first-user-other-token'

    Microsoft().set_session_data(request_for(second, shared_session), 'second-token', '', 9999999999)

    assert 'other_idp_token' not in shared_session['user']
    assert Microsoft().get_session_data(request_for(second, shared_session))['microsoft_access_token'] == 'second-token'
    assert Microsoft().get_session_data(request_for(first, shared_session)) is False


def test_sign_out_removes_the_session_token_data(first):
    client = Client()
    session = client.session
    session['user'] = {'owner_id': first.id, 'microsoft_access_token': FIRST_TOKEN}
    session['token_cache'] = 'cache'
    session.save()
    token = Token.objects.create(user=first)

    response = client.post('/swirl/swirl-logout/', HTTP_AUTHORIZATION=f'Token {token.key}')

    assert response.status_code == 200
    assert 'user' not in client.session
    assert 'token_cache' not in client.session
    assert not Token.objects.filter(user=first).exists()
