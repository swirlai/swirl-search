"""
Regression tests for GitHub issue #1941:

  1. OIDC sign-in must NOT provision superuser/staff accounts, and must not
     install a shared, usable password (Basic-auth backdoor).
  2. The Microsoft OauthToken DB fallback must be scoped to the requesting
     user — it must never return another user's token (cross-user exposure).

Run with:  pytest swirl/tests/test_security_1941.py -v
"""

from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory

from swirl.models import OauthToken
from swirl.views import OidcAuthView, get_session_data_with_db_fallback


# ---------------------------------------------------------------------------
# Bug #2 — cross-user Microsoft token fallback
# ---------------------------------------------------------------------------

def _make_request(user):
    req = RequestFactory().get('/api/swirl/search/')
    req.user = user
    req.session = {}          # no browser session -> Authenticator returns False
    return req


@pytest.mark.django_db
def test_no_cross_user_token_fallback():
    """User A (no token) must NOT receive User B's Microsoft token."""
    user_a = User.objects.create_user(username='alice', password='pw')
    user_b = User.objects.create_user(username='bob', password='pw')
    OauthToken.objects.create(owner=user_b, idp='Microsoft', token='BOB-SECRET-TOKEN')

    result = get_session_data_with_db_fallback(_make_request(user_a))

    # Alice has no token of her own; she must get nothing — never Bob's.
    assert not result or result.get('microsoft_access_token') != 'BOB-SECRET-TOKEN'


@pytest.mark.django_db
def test_own_token_still_returned():
    """A user WITH a token still gets their own token back (no regression)."""
    user_a = User.objects.create_user(username='alice', password='pw')
    OauthToken.objects.create(owner=user_a, idp='Microsoft', token='ALICE-TOKEN')

    result = get_session_data_with_db_fallback(_make_request(user_a))

    assert result['microsoft_access_token'] == 'ALICE-TOKEN'


# ---------------------------------------------------------------------------
# Bug #1 — OIDC superuser provisioning
# ---------------------------------------------------------------------------

def _oidc_post():
    req = APIRequestFactory().post('/swirl/oidc_authenticate/')
    req.META['HTTP_OIDC_TOKEN'] = 'Bearer graph-access-token'
    return req


@pytest.mark.django_db
def test_oidc_provisions_non_privileged_user():
    """A new OIDC user must be created without superuser/staff or a usable password."""
    with patch('swirl.views.Microsoft.get_user', return_value={'mail': 'newbie@example.com'}):
        response = OidcAuthView().post(_oidc_post())

    assert response.status_code == 200
    user = User.objects.get(email='newbie@example.com')
    assert user.is_superuser is False
    assert user.is_staff is False
    assert user.has_usable_password() is False
    assert response.data['is_superuser'] is False


@pytest.mark.django_db
def test_oidc_invalid_token_forbidden():
    """A token with no mail (e.g. expired/invalid) must return 403, not 500."""
    with patch('swirl.views.Microsoft.get_user', return_value={'error': 'invalid'}):
        response = OidcAuthView().post(_oidc_post())

    assert response.status_code == 403
