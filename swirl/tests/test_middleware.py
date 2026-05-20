"""
Unit tests for swirl.middleware.TokenMiddleware.

Covers the Authorization-header defensive parsing fix: malformed headers
(empty value, scheme-only, no-space) used to ``IndexError`` out of
``auth_header.split(' ')[1]`` and surface as a 500. They should now
return 403 Forbidden, matching the policy for unknown tokens.

Symptom in 4.5.0.x without this fix: any /sapi/ request from a client
that sent ``Authorization: Token`` (no value) or ``Authorization: Bearer``
crashed the request, and Galaxy's getIsAIProviderExistsStatus error path
hid the AI drawer (including the new ai_instructions textarea).

Run with:  pytest swirl/tests/test_middleware.py -v
"""

from unittest.mock import MagicMock

import pytest

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

from swirl.middleware import TokenMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _request(path='/api/swirl/sapi/ai_providers/', headers=None):
    """Minimal Django-like request stub. .path + .headers (dict) are all
    the auth-check branch of TokenMiddleware reads."""
    req = MagicMock(name='request')
    req.path = path
    req.headers = headers or {}
    return req


def _middleware():
    """Returns (middleware_instance, get_response_mock, downstream_sentinel)."""
    sentinel = MagicMock(name='downstream_response')
    get_response = MagicMock(name='get_response', return_value=sentinel)
    return TokenMiddleware(get_response), get_response, sentinel


# ---------------------------------------------------------------------------
# Valid-path behaviour (sanity checks so the malformed tests aren't false-
# positive: we want to confirm the auth-check branch is actually reached).
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_valid_token_passes_through():
    user = User.objects.create_user(username='mw_valid', password='pw')
    token = Token.objects.create(user=user)

    mw, get_response, sentinel = _middleware()
    req = _request(headers={'Authorization': f'Token {token.key}'})

    result = mw(req)

    assert result is sentinel
    assert req.user == user
    get_response.assert_called_once_with(req)


@pytest.mark.django_db
def test_unknown_token_returns_403():
    mw, get_response, _ = _middleware()
    req = _request(headers={'Authorization': 'Token nosuchtoken'})

    result = mw(req)

    assert result.status_code == 403
    get_response.assert_not_called()


def test_missing_authorization_header_returns_403():
    mw, get_response, _ = _middleware()
    req = _request(headers={})

    result = mw(req)

    assert result.status_code == 403
    get_response.assert_not_called()


# ---------------------------------------------------------------------------
# Malformed-header regression coverage. Each of these used to IndexError
# out of `auth_header.split(' ')[1]` and surface as a 500. They should now
# all return 403 Forbidden.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('header_value', [
    'Token',           # scheme only, no space, no value
    'Bearer',          # ditto
    'Token ',          # scheme + trailing space, empty value
    'Token   ',        # scheme + multiple spaces, empty value
    'tokenwithoutscheme',
    '',                # empty header value
    '   ',             # whitespace-only header
])
def test_malformed_header_returns_403_not_500(header_value):
    mw, get_response, _ = _middleware()
    req = _request(headers={'Authorization': header_value})

    result = mw(req)

    assert result.status_code == 403, (
        f'Expected 403 Forbidden for malformed header {header_value!r}, '
        f'got status {getattr(result, "status_code", "n/a")}'
    )
    get_response.assert_not_called()


# ---------------------------------------------------------------------------
# Path-routing sanity: the malformed-header path only matters when the
# auth-check branch is reached. Confirm non-/sapi/ paths still skip auth.
# ---------------------------------------------------------------------------

def test_non_sapi_path_skips_auth_check():
    """Paths that don't contain /sapi/ (and aren't /swirl/logout/) bypass
    the token check entirely — no Authorization header required."""
    mw, get_response, sentinel = _middleware()
    req = _request(path='/swirl/admin/', headers={})

    result = mw(req)

    assert result is sentinel
    get_response.assert_called_once_with(req)


def test_branding_path_bypasses_auth():
    """The /api/swirl/sapi/branding/ path is explicitly whitelisted at the
    top of __call__ — the login page hits it before any auth."""
    mw, get_response, sentinel = _middleware()
    req = _request(path='/api/swirl/sapi/branding/', headers={})

    result = mw(req)

    assert result is sentinel
    get_response.assert_called_once_with(req)
