"""
Tests for Microsoft sign-in through /swirl/oidc_authenticate/.

Sign-in requires an ID token issued by Microsoft Entra ID to this instance's
app registration (MICROSOFT_CLIENT_ID), from the configured tenant when
MICROSOFT_TENANT_ID is set; see swirl/oidc_signin.py.

Every request goes through the real URL, middleware and view. Keys are
generated at test time; nothing is checked in. Microsoft's key set and Graph
are served with `responses`, so no network is used.
"""

import json
import time

import jwt
import pytest
import responses
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from swirl import oidc_signin

URL = '/swirl/oidc_authenticate/'

CLIENT_ID = '11111111-1111-4111-8111-111111111111'
TENANT = '22222222-2222-4222-8222-222222222222'
OTHER_TENANT = '33333333-3333-4333-8333-333333333333'
GRAPH_AUDIENCE = '00000003-0000-0000-c000-000000000000'

COMMON_KEYS = 'https://login.microsoftonline.com/common/discovery/v2.0/keys'
GRAPH_ME = 'https://graph.microsoft.com/v1.0/me'

EMAIL = 'alice@example.com'
NOW = int(time.time())


def issuer(tenant=TENANT):
    return f'https://login.microsoftonline.com/{tenant}/v2.0'


def tenant_keys(tenant=TENANT):
    return f'https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys'


# ---------------------------------------------------------------------------
# keys, tokens, fakes
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope='module')
def other_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def jwks_for(private_key, kid='k1'):
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({'kid': kid, 'use': 'sig', 'alg': 'RS256'})
    return {'keys': [jwk]}


def mint(private_key, alg='RS256', kid='k1', **claims):
    payload = {'iss': issuer(), 'aud': CLIENT_ID, 'sub': 'subject-1',
               'tid': TENANT, 'iat': NOW, 'exp': NOW + 600, 'email': EMAIL}
    payload.update(claims)
    payload = {k: v for k, v in payload.items() if v is not None}
    return jwt.encode(payload, private_key, algorithm=alg, headers={'kid': kid})


@pytest.fixture(autouse=True)
def microsoft(key, settings):
    """An instance configured for one tenant, Microsoft's key sets, and a
    Graph that answers every token with a mailbox. Graph must never be asked."""
    settings.MICROSOFT_CLIENT_ID = CLIENT_ID
    settings.MICROSOFT_TENANT_ID = TENANT
    oidc_signin.clear_jwks_cache()
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        keys = jwks_for(key)
        mock.get(tenant_keys(TENANT), json=keys)
        mock.get(COMMON_KEYS, json=keys)
        mock.get(tenant_keys(OTHER_TENANT), json=keys)
        mock.get(GRAPH_ME, json={'mail': EMAIL, 'displayName': 'Alice'})
        yield mock
    oidc_signin.clear_jwks_cache()


def post(token=None, header=None):
    headers = {}
    if header is not None:
        headers['OIDC-Token'] = header
    elif token is not None:
        headers['OIDC-Token'] = f'Bearer {token}'
    return APIClient(raise_request_exception=False).post(URL, headers=headers)


def graph_calls(mock):
    return [c for c in mock.calls if c.request.url.startswith(GRAPH_ME)]


def assert_refused(response, mock):
    assert response.status_code == 403
    assert response.content == b''
    assert not User.objects.filter(email__iexact=EMAIL).exists()
    assert Token.objects.count() == 0
    assert graph_calls(mock) == []


# ---------------------------------------------------------------------------
# a valid ID token signs in
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestValidToken:

    def test_id_token_signs_in_and_provisions_a_regular_user(self, key, microsoft):
        response = post(mint(key))

        assert response.status_code == 200
        user = User.objects.get(email=EMAIL)
        assert response.json()['user'] == user.username == EMAIL
        assert response.json()['token'] == Token.objects.get(user=user).key
        assert response.json()['is_superuser'] is False
        assert user.is_superuser is False
        assert user.is_staff is False
        assert user.has_usable_password() is False
        assert graph_calls(microsoft) == []

    def test_returned_token_is_accepted_by_the_api(self, key):
        token = post(mint(key)).json()['token']

        client = APIClient()
        assert client.get('/swirl/sapi/authenticators/').status_code == 403
        client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        assert client.get('/swirl/sapi/authenticators/').status_code == 200

    def test_new_account_has_no_permissions(self, key):
        post(mint(key))

        assert User.objects.get(email=EMAIL).get_all_permissions() == set()

    def test_existing_user_is_reused_whatever_the_case_of_the_address(self, key):
        existing = User.objects.create_user(username='Alice@Example.com',
                                            email='Alice@Example.com')

        response = post(mint(key))

        assert response.status_code == 200
        assert response.json()['user'] == existing.username
        assert User.objects.count() == 1

    def test_second_sign_in_returns_the_same_user_and_token(self, key):
        first = post(mint(key)).json()
        second = post(mint(key)).json()

        assert first['token'] == second['token']
        assert User.objects.filter(email=EMAIL).count() == 1

    def test_audience_list_containing_the_client_id_is_accepted(self, key):
        assert post(mint(key, aud=[CLIENT_ID, 'something-else'])).status_code == 200

    def test_preferred_username_is_used_when_there_is_no_email(self, key):
        response = post(mint(key, email=None, preferred_username='Bob@Example.com'))

        assert response.status_code == 200
        assert response.json()['user'] == 'bob@example.com'

    def test_header_without_a_scheme_is_accepted(self, key):
        assert post(header=mint(key)).status_code == 200


# ---------------------------------------------------------------------------
# anything else is refused
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRefused:

    def test_token_issued_for_another_audience(self, key, microsoft):
        assert_refused(post(mint(key, aud=GRAPH_AUDIENCE)), microsoft)

    def test_token_issued_to_another_app_registration(self, key, microsoft):
        other_app = '44444444-4444-4444-8444-444444444444'
        assert_refused(post(mint(key, aud=other_app)), microsoft)

    def test_opaque_token(self, microsoft):
        assert_refused(post('opaque-access-token'), microsoft)

    def test_missing_audience(self, key, microsoft):
        assert_refused(post(mint(key, aud=None)), microsoft)

    def test_wrong_issuer(self, key, microsoft):
        assert_refused(post(mint(key, iss='https://issuer.example.com/v2.0')), microsoft)

    def test_legacy_v1_issuer(self, key, microsoft):
        assert_refused(post(mint(key, iss=f'https://sts.windows.net/{TENANT}/')), microsoft)

    def test_token_from_another_tenant(self, key, microsoft):
        token = mint(key, iss=issuer(OTHER_TENANT), tid=OTHER_TENANT)
        assert_refused(post(token), microsoft)

    def test_issuer_is_not_taken_from_the_tid_claim(self, key, microsoft):
        assert_refused(post(mint(key, iss=issuer(OTHER_TENANT), tid=TENANT)), microsoft)

    def test_expired(self, key, microsoft):
        assert_refused(post(mint(key, iat=NOW - 7200, exp=NOW - 3600)), microsoft)

    def test_missing_expiry(self, key, microsoft):
        assert_refused(post(mint(key, exp=None)), microsoft)

    def test_missing_subject(self, key, microsoft):
        assert_refused(post(mint(key, sub=None)), microsoft)

    def test_signed_with_an_unknown_key(self, other_key, microsoft):
        assert_refused(post(mint(other_key)), microsoft)

    def test_unknown_key_id(self, key, microsoft):
        assert_refused(post(mint(key, kid='not-published')), microsoft)

    def test_hs256_token(self, microsoft):
        token = jwt.encode({'iss': issuer(), 'aud': CLIENT_ID, 'sub': 's', 'tid': TENANT,
                            'exp': NOW + 600, 'email': EMAIL},
                           'x' * 32, algorithm='HS256', headers={'kid': 'k1'})
        assert_refused(post(token), microsoft)

    def test_unsigned_token(self, microsoft):
        token = jwt.encode({'iss': issuer(), 'aud': CLIENT_ID, 'sub': 's', 'tid': TENANT,
                            'exp': NOW + 600, 'email': EMAIL},
                           None, algorithm='none', headers={'kid': 'k1'})
        assert_refused(post(token), microsoft)

    def test_email_not_verified(self, key, microsoft):
        assert_refused(post(mint(key, email_verified=False)), microsoft)

    def test_no_identity_claim(self, key, microsoft):
        assert_refused(post(mint(key, email=None)), microsoft)

    def test_key_set_unavailable(self, key, microsoft):
        microsoft.replace(responses.GET, tenant_keys(TENANT), status=503)
        assert_refused(post(mint(key)), microsoft)


@pytest.mark.django_db
class TestHeader:

    def test_no_header(self, microsoft):
        assert_refused(post(), microsoft)

    def test_empty_header(self, microsoft):
        assert_refused(post(header=''), microsoft)

    def test_scheme_without_a_token(self, microsoft):
        assert_refused(post(header='Bearer '), microsoft)

    def test_single_word_that_is_not_a_token(self, microsoft):
        assert_refused(post(header='x'), microsoft)

    def test_get_is_not_allowed(self):
        assert APIClient().get(URL).status_code == 405


# ---------------------------------------------------------------------------
# accounts
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAccounts:

    def test_address_shared_by_two_accounts_is_refused(self, key, microsoft):
        User.objects.create_user(username='alice-1', email=EMAIL)
        User.objects.create_user(username='alice-2', email=EMAIL.upper())

        response = post(mint(key))

        assert response.status_code == 403
        assert Token.objects.count() == 0
        assert User.objects.count() == 2

    def test_username_taken_by_an_account_with_another_address_is_refused(self, key, microsoft):
        User.objects.create_user(username=EMAIL, email='someone-else@example.com')

        response = post(mint(key))

        assert response.status_code == 403
        assert Token.objects.count() == 0
        assert User.objects.count() == 1

    def test_existing_superuser_keeps_its_rights(self, key):
        User.objects.create_superuser(username='admin', email=EMAIL, password=None)

        response = post(mint(key))

        assert response.status_code == 200
        assert response.json()['user'] == 'admin'
        assert response.json()['is_superuser'] is True


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestConfiguration:

    def test_refused_when_no_client_id_is_configured(self, key, microsoft, settings):
        settings.MICROSOFT_CLIENT_ID = ''
        assert_refused(post(mint(key, aud='')), microsoft)
        assert_refused(post(mint(key)), microsoft)

    @pytest.mark.parametrize('tenant', ['common', 'organizations', 'consumers',
                                        'contoso.onmicrosoft.com', 'not-a-guid'])
    def test_refused_when_the_tenant_is_not_a_tenant_id(self, tenant, key, microsoft, settings):
        settings.MICROSOFT_TENANT_ID = tenant
        assert_refused(post(mint(key)), microsoft)
        assert len(microsoft.calls) == 0

    def test_tenant_id_is_matched_whatever_its_case(self, key, microsoft, settings):
        settings.MICROSOFT_TENANT_ID = f' {TENANT.upper()} '

        assert post(mint(key)).status_code == 200
        assert [c.request.url for c in microsoft.calls] == [tenant_keys(TENANT)]

    def test_key_set_is_fetched_once(self, key, microsoft):
        post(mint(key))
        post(mint(key))

        assert [c.request.url for c in microsoft.calls] == [tenant_keys(TENANT)]

    def test_rejections_do_not_log_the_token(self, key, microsoft, caplog):
        token = mint(key, aud=GRAPH_AUDIENCE)

        with caplog.at_level('DEBUG'):
            post(token)

        assert token not in caplog.text
        assert token.split('.')[2] not in caplog.text


# ---------------------------------------------------------------------------
# no tenant configured: the token's own tenant, audience still enforced
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNoTenantConfigured:

    @pytest.fixture(autouse=True)
    def no_tenant(self, settings):
        settings.MICROSOFT_TENANT_ID = ''

    def test_token_from_any_tenant_signs_in_using_the_common_key_set(self, key, microsoft):
        token = mint(key, iss=issuer(OTHER_TENANT), tid=OTHER_TENANT)

        assert post(token).status_code == 200
        assert [c.request.url for c in microsoft.calls] == [COMMON_KEYS]

    def test_a_warning_is_logged_once(self, key, caplog):
        with caplog.at_level('WARNING', logger='swirl.oidc_signin'):
            assert post(mint(key)).status_code == 200
            assert post(mint(key)).status_code == 200

        warnings = [r for r in caplog.records
                    if 'MICROSOFT_TENANT_ID is not set' in r.getMessage()]
        assert len(warnings) == 1

    def test_token_issued_for_another_audience(self, key, microsoft):
        assert_refused(post(mint(key, aud=GRAPH_AUDIENCE)), microsoft)

    def test_opaque_token(self, microsoft):
        assert_refused(post('opaque-access-token'), microsoft)

    def test_issuer_of_a_different_tenant_than_tid(self, key, microsoft):
        assert_refused(post(mint(key, iss=issuer(OTHER_TENANT))), microsoft)

    def test_issuer_outside_microsoft(self, key, microsoft):
        assert_refused(post(mint(key, iss='https://issuer.example.com/v2.0')), microsoft)

    def test_legacy_v1_issuer(self, key, microsoft):
        assert_refused(post(mint(key, iss=f'https://sts.windows.net/{TENANT}/')), microsoft)

    @pytest.mark.parametrize('tid', ['common', 'organizations', '../common', '', 12345])
    def test_tid_that_is_not_a_tenant_id(self, tid, key, microsoft):
        assert_refused(post(mint(key, tid=tid)), microsoft)
        assert len(microsoft.calls) == 0

    def test_missing_tid(self, key, microsoft):
        assert_refused(post(mint(key, tid=None)), microsoft)

    def test_signed_with_an_unknown_key(self, other_key, microsoft):
        assert_refused(post(mint(other_key)), microsoft)

    def test_expired(self, key, microsoft):
        assert_refused(post(mint(key, iat=NOW - 7200, exp=NOW - 3600)), microsoft)

    def test_refused_when_no_client_id_is_configured(self, key, microsoft, settings):
        settings.MICROSOFT_CLIENT_ID = ''
        assert_refused(post(mint(key)), microsoft)
