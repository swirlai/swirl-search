"""
Tests for Backstage plugin-token verification (WP03).

The token under test is the one Backstage's search backend mints per query:
an ES256 JWT with header typ 'vnd.backstage.plugin', claims sub/aud/iat/exp,
and an optional nested 'obo' token whose sub is the user entity ref.

Every key here is generated at test time; nothing is checked in. The JWKS is
served with `responses` so no Backstage backend is needed.
"""

import json
import time
import uuid

import jwt
import pytest
import responses
from cryptography.hazmat.primitives.asymmetric import ec
from django.contrib.auth.models import User
from django.test import RequestFactory, override_settings

from swirl.backstage_bearer import (
    BACKSTAGE_GROUP_NAME,
    BACKSTAGE_SERVICE_USERNAME,
    BackstageTokenError,
    authenticate_backstage_token,
    get_or_create_backstage_user,
    is_backstage_enabled,
    is_backstage_token,
    reset_jwks_client,
)
from swirl.middleware import BackstageTokenMiddleware

JWKS_URL = 'http://backstage.test:7007/api/search/.backstage/auth/v1/jwks.json'
AUDIENCE = 'search'


# ---------------------------------------------------------------------------
# Key material and token minting, all generated per test run
# ---------------------------------------------------------------------------

def _make_es256_key():
    """Return (private_key_pem, jwk_dict) for a fresh P-256 key pair."""
    from cryptography.hazmat.primitives import serialization

    priv = ec.generate_private_key(ec.SECP256R1())
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()

    kid = uuid.uuid4().hex
    pub_jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(priv.public_key()))
    pub_jwk.update({'kid': kid, 'use': 'sig', 'alg': 'ES256'})
    return priv_pem, pub_jwk


def _mint_obo(priv_pem, kid, user_ref, exp_offset=300):
    """The nested limited user token. Its bytes are covered by the outer signature."""
    now = int(time.time())
    return jwt.encode(
        {'sub': user_ref, 'aud': AUDIENCE, 'iat': now, 'exp': now + exp_offset},
        priv_pem,
        algorithm='ES256',
        headers={'kid': kid, 'typ': 'vnd.backstage.user'},
    )


def _mint_plugin_token(priv_pem, kid, *, sub='search', aud=AUDIENCE,
                       user_ref=None, exp_offset=300, typ='vnd.backstage.plugin'):
    now = int(time.time())
    claims = {'sub': sub, 'aud': aud, 'iat': now - 1, 'exp': now + exp_offset}
    if user_ref:
        claims['obo'] = _mint_obo(priv_pem, kid, user_ref, exp_offset=exp_offset)
    return jwt.encode(
        claims, priv_pem, algorithm='ES256', headers={'kid': kid, 'typ': typ}
    )


@pytest.fixture
def keys():
    priv_pem, jwk = _make_es256_key()
    reset_jwks_client()
    yield priv_pem, jwk
    reset_jwks_client()


def _serve_jwks(jwk):
    responses.add(
        responses.GET, JWKS_URL, json={'keys': [jwk]}, status=200,
    )


backstage_on = override_settings(
    SWIRL_BACKSTAGE_JWKS_URL=JWKS_URL,
    SWIRL_BACKSTAGE_AUDIENCE=AUDIENCE,
)


# ---------------------------------------------------------------------------
# is_backstage_token / is_backstage_enabled
# ---------------------------------------------------------------------------

def test_is_backstage_token_reads_the_typ_header(keys):
    priv_pem, jwk = keys
    token = _mint_plugin_token(priv_pem, jwk['kid'])
    assert is_backstage_token(token) is True


def test_is_backstage_token_rejects_a_plain_jwt(keys):
    priv_pem, jwk = keys
    token = _mint_plugin_token(priv_pem, jwk['kid'], typ='JWT')
    assert is_backstage_token(token) is False


def test_is_backstage_token_rejects_garbage():
    assert is_backstage_token('not-a-jwt') is False
    assert is_backstage_token('') is False


@override_settings(SWIRL_BACKSTAGE_JWKS_URL='', SWIRL_BACKSTAGE_AUDIENCE=AUDIENCE)
def test_disabled_when_the_jwks_url_is_empty():
    assert is_backstage_enabled() is False


@override_settings(SWIRL_BACKSTAGE_JWKS_URL=JWKS_URL, SWIRL_BACKSTAGE_AUDIENCE='')
def test_disabled_when_the_audience_is_empty():
    assert is_backstage_enabled() is False


@backstage_on
def test_enabled_when_both_settings_are_present():
    assert is_backstage_enabled() is True


# ---------------------------------------------------------------------------
# authenticate_backstage_token
# ---------------------------------------------------------------------------

@backstage_on
@responses.activate
def test_valid_token_with_obo_yields_the_user_ref(keys):
    priv_pem, jwk = keys
    _serve_jwks(jwk)
    token = _mint_plugin_token(priv_pem, jwk['kid'], user_ref='user:default/sid')

    principal = authenticate_backstage_token(token)

    assert principal.plugin == 'search'
    assert principal.user_ref == 'user:default/sid'
    assert principal.is_service is False
    assert principal.username == 'backstage:user:default/sid'


@backstage_on
@responses.activate
def test_valid_token_without_obo_is_a_service_principal(keys):
    priv_pem, jwk = keys
    _serve_jwks(jwk)
    token = _mint_plugin_token(priv_pem, jwk['kid'])

    principal = authenticate_backstage_token(token)

    assert principal.plugin == 'search'
    assert principal.user_ref is None
    assert principal.is_service is True
    assert principal.username == BACKSTAGE_SERVICE_USERNAME


@backstage_on
@responses.activate
def test_wrong_audience_is_rejected(keys):
    priv_pem, jwk = keys
    _serve_jwks(jwk)
    token = _mint_plugin_token(priv_pem, jwk['kid'], aud='catalog')

    with pytest.raises(BackstageTokenError):
        authenticate_backstage_token(token)


@backstage_on
@responses.activate
def test_expired_token_is_rejected(keys):
    priv_pem, jwk = keys
    _serve_jwks(jwk)
    token = _mint_plugin_token(priv_pem, jwk['kid'], exp_offset=-60)

    with pytest.raises(BackstageTokenError):
        authenticate_backstage_token(token)


@backstage_on
@responses.activate
def test_token_signed_by_an_unknown_key_is_rejected(keys):
    priv_pem, jwk = keys
    _serve_jwks(jwk)
    other_pem, other_jwk = _make_es256_key()
    # Same kid so the JWKS lookup succeeds, different key so the signature fails.
    token = _mint_plugin_token(other_pem, jwk['kid'])

    with pytest.raises(BackstageTokenError):
        authenticate_backstage_token(token)


@backstage_on
@responses.activate
def test_jwks_unreachable_is_rejected(keys):
    priv_pem, jwk = keys
    responses.add(responses.GET, JWKS_URL, status=503)
    token = _mint_plugin_token(priv_pem, jwk['kid'])

    with pytest.raises(BackstageTokenError) as excinfo:
        authenticate_backstage_token(token)
    assert 'signing key' in str(excinfo.value)


@override_settings(SWIRL_BACKSTAGE_JWKS_URL='', SWIRL_BACKSTAGE_AUDIENCE='')
def test_authenticate_refuses_when_disabled(keys):
    priv_pem, jwk = keys
    token = _mint_plugin_token(priv_pem, jwk['kid'])
    with pytest.raises(BackstageTokenError):
        authenticate_backstage_token(token)


# ---------------------------------------------------------------------------
# User mapping
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@backstage_on
@responses.activate
def test_obo_user_is_mapped_into_the_backstage_group(keys):
    priv_pem, jwk = keys
    _serve_jwks(jwk)
    token = _mint_plugin_token(priv_pem, jwk['kid'], user_ref='user:default/sid')

    user = get_or_create_backstage_user(authenticate_backstage_token(token))

    assert user.username == 'backstage:user:default/sid'
    assert user.groups.filter(name=BACKSTAGE_GROUP_NAME).exists()
    # The search permissions this repo requires of a normal user.
    for perm in ('swirl.view_searchprovider', 'swirl.add_search',
                 'swirl.change_search', 'swirl.view_search',
                 'swirl.add_result', 'swirl.change_result', 'swirl.view_result'):
        assert user.has_perm(perm), perm


@pytest.mark.django_db
@backstage_on
@responses.activate
def test_service_principal_maps_to_a_single_service_user(keys):
    priv_pem, jwk = keys
    _serve_jwks(jwk)
    token = _mint_plugin_token(priv_pem, jwk['kid'])

    user = get_or_create_backstage_user(authenticate_backstage_token(token))
    again = get_or_create_backstage_user(authenticate_backstage_token(token))

    assert user.pk == again.pk
    assert user.username == BACKSTAGE_SERVICE_USERNAME
    assert User.objects.filter(username=BACKSTAGE_SERVICE_USERNAME).count() == 1
    assert user.has_perm('swirl.change_searchprovider')
    assert user.has_perm('swirl.add_search')
    assert user.has_perm('swirl.view_search')
    assert not user.has_perm('swirl.view_searchprovider')


# ---------------------------------------------------------------------------
# BackstageTokenMiddleware
# ---------------------------------------------------------------------------

def _run_middleware(request):
    seen = {}

    def get_response(req):
        seen['user'] = getattr(req, 'user', None)
        seen['principal'] = getattr(req, 'backstage_principal', None)
        from django.http import HttpResponse
        return HttpResponse('ok')

    response = BackstageTokenMiddleware(get_response)(request)
    return response, seen


@pytest.mark.django_db
@backstage_on
@responses.activate
def test_middleware_authenticates_a_valid_token(keys):
    priv_pem, jwk = keys
    _serve_jwks(jwk)
    token = _mint_plugin_token(priv_pem, jwk['kid'], user_ref='user:default/sid')
    request = RequestFactory().get('/swirl/search/', HTTP_AUTHORIZATION=f'Bearer {token}')

    response, seen = _run_middleware(request)

    assert response.status_code == 200
    assert seen['principal'].user_ref == 'user:default/sid'
    assert seen['user'].username == 'backstage:user:default/sid'


@pytest.mark.django_db
@backstage_on
@responses.activate
def test_middleware_returns_401_with_the_challenge_header(keys):
    priv_pem, jwk = keys
    _serve_jwks(jwk)
    token = _mint_plugin_token(priv_pem, jwk['kid'], aud='catalog')
    request = RequestFactory().get('/swirl/search/', HTTP_AUTHORIZATION=f'Bearer {token}')

    response, seen = _run_middleware(request)

    assert response.status_code == 401
    assert response['WWW-Authenticate'] == 'Bearer error="invalid_token"'
    assert seen == {}


@pytest.mark.django_db
@override_settings(SWIRL_BACKSTAGE_JWKS_URL='', SWIRL_BACKSTAGE_AUDIENCE='')
def test_middleware_is_a_no_op_when_disabled(keys):
    priv_pem, jwk = keys
    token = _mint_plugin_token(priv_pem, jwk['kid'], user_ref='user:default/sid')
    request = RequestFactory().get('/swirl/search/', HTTP_AUTHORIZATION=f'Bearer {token}')

    response, seen = _run_middleware(request)

    assert response.status_code == 200
    assert seen['principal'] is None
    assert not User.objects.filter(username__startswith='backstage:').exists()


@pytest.mark.django_db
@backstage_on
def test_middleware_ignores_a_non_backstage_bearer(keys):
    priv_pem, jwk = keys
    token = _mint_plugin_token(priv_pem, jwk['kid'], typ='JWT')
    request = RequestFactory().get('/swirl/search/', HTTP_AUTHORIZATION=f'Bearer {token}')

    response, seen = _run_middleware(request)

    assert response.status_code == 200
    assert seen['principal'] is None


@pytest.mark.django_db
@backstage_on
@responses.activate
def test_middleware_rejects_a_wrong_typ_that_claims_to_be_backstage(keys):
    """A token whose typ is Backstage but which fails verification still 401s."""
    priv_pem, jwk = keys
    _serve_jwks(jwk)
    other_pem, _ = _make_es256_key()
    token = _mint_plugin_token(other_pem, jwk['kid'], user_ref='user:default/sid')
    request = RequestFactory().get('/swirl/search/', HTTP_AUTHORIZATION=f'Bearer {token}')

    response, _seen = _run_middleware(request)

    assert response.status_code == 401
    assert response['WWW-Authenticate'] == 'Bearer error="invalid_token"'
