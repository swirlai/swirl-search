"""
Unit + integration tests for swirl.authentication.OptionalTokenAuthentication.

The unit tests exercise the class in isolation.

The integration tests against SearchViewSet are the regression coverage for
4.5.0.3: that release reordered SearchViewSet's authentication_classes to put
stock TokenAuthentication first, which short-circuited the auth chain when the
client sent an invalid/stale Token header alongside a valid session cookie —
exactly the state Selenium / Galaxy ends up in across qa-suite scenarios.
qa-suite caught it (~50 min into the run); this test catches it in unit-tests
(seconds).

Run with:  pytest swirl/tests/test_authentication.py -v
"""

from unittest.mock import MagicMock

import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from swirl.authentication import OptionalTokenAuthentication


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    # Superuser so the test bypasses SearchViewSet's per-method has_perm()
    # checks. We're testing the auth chain, not the permission layer.
    return User.objects.create_user(
        username='auth_user', password='pw',
        is_staff=True, is_superuser=True,
    )


@pytest.fixture
def valid_token(db, user):
    return Token.objects.create(user=user)


# ---------------------------------------------------------------------------
# Unit tests — OptionalTokenAuthentication in isolation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_optional_token_auth_valid_token_authenticates(user, valid_token):
    """Valid Token header → returns (user, token) tuple (matches stock behaviour)."""
    rf = RequestFactory()
    req = rf.get('/api/swirl/sapi/search/', HTTP_AUTHORIZATION=f'Token {valid_token.key}')
    result = OptionalTokenAuthentication().authenticate(req)
    assert result is not None
    auth_user, auth_token = result
    assert auth_user == user
    assert auth_token == valid_token


@pytest.mark.django_db
def test_optional_token_auth_invalid_token_returns_none(db):
    """Invalid Token header → returns None (NOT raise) so the next auth class can try.

    This is the behaviour that distinguishes OptionalToken from stock Token.
    Stock TokenAuthentication raises AuthenticationFailed here, which DRF
    converts to a hard 401 — short-circuiting the auth chain.
    """
    rf = RequestFactory()
    req = rf.get('/api/swirl/sapi/search/', HTTP_AUTHORIZATION='Token nosuchtoken')
    result = OptionalTokenAuthentication().authenticate(req)
    assert result is None


def test_optional_token_auth_no_header_returns_none():
    """No Authorization header → returns None (matches stock behaviour)."""
    rf = RequestFactory()
    req = rf.get('/api/swirl/sapi/search/')
    result = OptionalTokenAuthentication().authenticate(req)
    assert result is None


def test_optional_token_auth_non_token_header_returns_none():
    """Authorization header that isn't Token-scheme → returns None.

    Stock TokenAuthentication also returns None in this case (lets other
    auth classes — e.g. Basic — handle their own scheme).
    """
    rf = RequestFactory()
    req = rf.get('/api/swirl/sapi/search/', HTTP_AUTHORIZATION='Bearer something.jwt.shape')
    result = OptionalTokenAuthentication().authenticate(req)
    assert result is None


# ---------------------------------------------------------------------------
# Integration tests — SearchViewSet auth chain
#
# These tests are the explicit regression for 4.5.0.3. They drive the full
# DRF chain (OptionalTokenAuthentication -> SessionAuthentication ->
# BasicAuthentication) via APIClient and assert that BOTH halves of the bug
# stay fixed simultaneously:
#
#   (a) Valid Token wins cleanly without CSRF enforcement on unsafe methods
#       — this was the original DELETE-403 cascade fix.
#   (b) Invalid Token alongside a valid session falls through and Session
#       still authenticates — this is what regressed in 4.5.0.3 and tripped
#       qa-suite an hour into the run.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_searchviewset_valid_token_alone_authenticates(user, valid_token):
    """Plain Token-only auth (no session) → 200 on GET /swirl/sapi/search/.

    Hits the /swirl/search/ path (not /api/swirl/sapi/search/) because the
    sapi-prefixed path passes through swirl.middleware.TokenMiddleware,
    which has its own auth handling; the goal of these tests is to exercise
    DRF's authentication_classes chain on SearchViewSet directly.
    """
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f'Token {valid_token.key}')
    r = c.get('/swirl/search/')
    assert r.status_code == 200, f'Token auth should succeed; got {r.status_code} body={r.content!r:.200}'


@pytest.mark.django_db
def test_searchviewset_session_alone_authenticates(user):
    """Session cookie alone (no Token header) → 200. Django admin / browsable
    API depend on this path."""
    c = APIClient()
    c.force_login(user)
    r = c.get('/swirl/search/')
    assert r.status_code == 200, f'Session auth should succeed; got {r.status_code} body={r.content!r:.200}'


@pytest.mark.django_db
def test_searchviewset_stale_token_plus_valid_session_authenticates(user):
    """REGRESSION TEST FOR 4.5.0.3.

    Client sends an invalid Token header (e.g. a stale value carried over
    from a previous login) AND a valid session cookie. The session is
    sufficient — auth must succeed.

    With stock TokenAuthentication listed first (4.5.0.3 behaviour), this
    returned 401: TokenAuthentication raised AuthenticationFailed on the
    stale token and short-circuited the auth chain. With
    OptionalTokenAuthentication first, the invalid token is dropped
    silently (returns None) and SessionAuthentication picks up the session
    cookie.
    """
    c = APIClient()
    c.force_login(user)
    c.credentials(HTTP_AUTHORIZATION='Token stale_invalid_value')
    r = c.get('/swirl/search/')
    assert r.status_code == 200, (
        f'Stale-token + valid-session should still authenticate via session; '
        f'got {r.status_code} body={r.content!r:.200}'
    )


@pytest.mark.django_db
def test_searchviewset_no_credentials_is_rejected():
    """No auth at all → 401 (DRF authentication failure) OR 403 (the
    SearchViewSet.list() per-method has_perm check fires for the resulting
    AnonymousUser). Sanity check that the chain still rejects anonymous
    requests after the reorder + new auth class — we don't care which of
    the two negative statuses comes out, just that the request is denied."""
    c = APIClient()
    r = c.get('/swirl/search/')
    assert r.status_code in (401, 403), (
        f'Anonymous request should be 401 or 403; got {r.status_code}'
    )
