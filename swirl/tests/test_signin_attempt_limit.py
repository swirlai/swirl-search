"""
Failed password sign-ins are limited per username and client address
(swirl/signin_limit.py): after SWIRL_SIGNIN_FAILURE_LIMIT failures in a
minute, further attempts for that pair are refused until the minute is up.
"""

import base64
from unittest import mock

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client
from rest_framework.authtoken.models import Token

from swirl import signin_limit

PASSWORD = 'correct-not-a-real-password'
LIMIT = 3


@pytest.fixture(autouse=True)
def clean_counts(settings):
    settings.SWIRL_SIGNIN_FAILURE_LIMIT = LIMIT
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_superuser('limit_user', 'limit_user@example.com', PASSWORD)


def sign_in(password, username='limit_user', address='203.0.113.5'):
    return Client().post('/swirl/login/', {'username': username, 'password': password},
                         content_type='application/json', REMOTE_ADDR=address).json()


def fail(times, **kwargs):
    for _ in range(times):
        assert 'token' not in sign_in('wrong-password', **kwargs)


def test_the_right_password_is_refused_after_too_many_failures(user):
    fail(LIMIT)

    answer = sign_in(PASSWORD)

    assert 'token' not in answer
    assert 'Too many failed sign-in attempts' in answer['error']
    assert Token.objects.count() == 0


def test_failures_under_the_limit_do_not_block(user):
    fail(LIMIT - 1)

    assert 'token' in sign_in(PASSWORD)


def test_a_wrong_password_is_still_called_invalid_under_the_limit(user):
    assert sign_in('wrong-password') == {'error': 'Invalid credentials'}


def test_another_client_address_is_not_affected(user):
    fail(LIMIT)

    assert 'token' in sign_in(PASSWORD, address='203.0.113.99')


def test_a_forwarding_header_does_not_step_round_the_limit(user):
    for attempt in range(LIMIT):
        Client().post('/swirl/login/', {'username': 'limit_user', 'password': 'wrong-password'},
                      content_type='application/json', REMOTE_ADDR='203.0.113.5',
                      HTTP_X_FORWARDED_FOR=f'198.51.100.{attempt}')

    answer = Client().post('/swirl/login/', {'username': 'limit_user', 'password': PASSWORD},
                           content_type='application/json', REMOTE_ADDR='203.0.113.5',
                           HTTP_X_FORWARDED_FOR='198.51.100.200').json()

    assert 'token' not in answer


def test_another_account_is_not_affected(user):
    User.objects.create_user('limit_other', 'limit_other@example.com', PASSWORD)
    fail(LIMIT)

    assert 'token' in sign_in(PASSWORD, username='limit_other')


def test_the_username_is_matched_whatever_its_case(user):
    fail(LIMIT, username='LIMIT_USER')

    assert 'token' not in sign_in(PASSWORD)


def test_sign_in_works_again_after_a_minute(user):
    fail(LIMIT)
    later = signin_limit.time.time() + signin_limit.WINDOW_SECONDS + 1

    with mock.patch.object(signin_limit.time, 'time', return_value=later):
        assert 'token' in sign_in(PASSWORD)


def test_refused_attempts_do_not_extend_the_wait(user):
    fail(LIMIT)
    for _ in range(5):
        sign_in(PASSWORD)
    later = signin_limit.time.time() + signin_limit.WINDOW_SECONDS + 1

    with mock.patch.object(signin_limit.time, 'time', return_value=later):
        assert 'token' in sign_in(PASSWORD)


def test_zero_turns_the_limit_off(user, settings):
    settings.SWIRL_SIGNIN_FAILURE_LIMIT = 0
    fail(LIMIT + 2)

    assert 'token' in sign_in(PASSWORD)


def test_the_admin_login_page_is_covered(user):
    fail(LIMIT)

    client = Client()
    response = client.post('/admin/login/', {'username': 'limit_user', 'password': PASSWORD},
                           REMOTE_ADDR='203.0.113.5')

    assert response.status_code == 200, 'the form is shown again, not a redirect into the admin'
    assert '_auth_user_id' not in client.session


def test_http_basic_is_covered(user):
    fail(LIMIT)
    header = 'Basic ' + base64.b64encode(f'limit_user:{PASSWORD}'.encode()).decode()

    response = Client().get('/swirl/searchproviders/', HTTP_AUTHORIZATION=header, REMOTE_ADDR='203.0.113.5')

    assert response.status_code in (401, 403)


def test_http_basic_works_under_the_limit(user):
    header = 'Basic ' + base64.b64encode(f'limit_user:{PASSWORD}'.encode()).decode()

    response = Client().get('/swirl/searchproviders/', HTTP_AUTHORIZATION=header, REMOTE_ADDR='203.0.113.5')

    assert response.status_code == 200
