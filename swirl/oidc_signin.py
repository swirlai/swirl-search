"""
swirl/oidc_signin.py - verification of the token a browser presents to sign in.

Galaxy signs a user in with Microsoft by POSTing the ID token it received to
``/swirl/oidc_authenticate/`` in the ``OIDC-Token`` header.  The token must be
an ID token that Microsoft Entra ID issued to this instance's own app
registration:

  * signature  - a key from Microsoft's published key set
  * ``iss``    - ``https://login.microsoftonline.com/<tenant>/v2.0``
  * ``aud``    - ``MICROSOFT_CLIENT_ID``
  * ``exp``    - required and in the future
  * ``sub``    - required

Tenant, the same rule as SWIRL Enterprise:

  * ``MICROSOFT_TENANT_ID`` set (the Directory (tenant) ID, a GUID): only that
    tenant's issuer is accepted, and the keys are that tenant's.
  * not set: the issuer of the tenant named in the token's ``tid`` claim is
    expected, and signature and audience are still enforced against
    Microsoft's common key set.  A multi-tenant app registration then lets
    any Entra tenant sign in, so a WARNING is logged once per process, at
    start-up and again at the first sign-in if start-up did not log it.  Set
    ``MICROSOFT_TENANT_ID`` to restrict sign-in to one tenant.

Sign-in is refused when ``MICROSOFT_CLIENT_ID`` is not configured.  Only v2.0
tokens are accepted; the legacy ``sts.windows.net`` issuer is not.
"""

import logging
import re
import threading

import jwt
from django.conf import settings

# The requests-based JWKS transport, so key fetches use the same proxy and TLS
# configuration as every other outbound call.
from swirl.backstage_bearer import BackstageJWKClient

logger = logging.getLogger(__name__)

MS_AUTHORITY = 'https://login.microsoftonline.com'
MS_COMMON_JWKS_URI = f'{MS_AUTHORITY}/common/discovery/v2.0/keys'

ALLOWED_ALGORITHMS = ('RS256',)
REQUIRED_CLAIMS = ('exp', 'iss', 'aud', 'sub')
IDENTITY_CLAIMS = ('email', 'upn', 'preferred_username')
LEEWAY_SECONDS = 30

_GUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')

_jwks_clients: dict = {}
_lock = threading.Lock()
_warned: set = set()


class SigninTokenError(Exception):
    """The sign-in token was rejected.

    ``reason`` is for logs only; callers answer a bare 403 so nothing about
    the configuration or the token is echoed to the browser.
    """

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _setting(name: str) -> str:
    value = getattr(settings, name, '')
    return value.strip() if isinstance(value, str) else ''


def signin_client_id() -> str:
    return _setting('MICROSOFT_CLIENT_ID')


def signin_tenant_id() -> str:
    return _setting('MICROSOFT_TENANT_ID').lower()


def _get_jwks_client(jwks_uri: str):
    with _lock:
        client = _jwks_clients.get(jwks_uri)
        if client is None:
            client = BackstageJWKClient(jwks_uri)
            _jwks_clients[jwks_uri] = client
        return client


def clear_jwks_cache():
    """Test hook / ops hook: drop cached key sets and the one-time warning."""
    with _lock:
        _jwks_clients.clear()
        _warned.clear()


def _warn_once(key: str, message: str):
    with _lock:
        if key in _warned:
            return
        _warned.add(key)
    logger.warning(message)


TENANT_NOT_SET_MESSAGE = (
    'oidc_signin: MICROSOFT_TENANT_ID is not set, so a sign-in token from '
    'any Entra tenant is accepted for this app registration. Set '
    'MICROSOFT_TENANT_ID to the Directory (tenant) ID to restrict sign-in '
    'to one tenant.')


def warn_if_any_tenant_can_sign_in():
    """Log the tenant notice now, if it applies: Microsoft sign-in is
    configured (``MICROSOFT_CLIENT_ID``) and no tenant is.  Called when a
    SWIRL process starts, so the notice does not wait for the first sign-in.
    Once per process, shared with the sign-in path."""
    if signin_client_id() and not signin_tenant_id():
        _warn_once('tenant-not-set', TENANT_NOT_SET_MESSAGE)


def _issuer_and_keys(raw_token: str):
    """Return ``(issuer, jwks_uri)`` to verify *raw_token* against.

    The token's own claims are consulted only when no tenant is configured,
    and only to name the tenant whose issuer must then verify.
    """
    tenant = signin_tenant_id()
    if tenant:
        if not _GUID_RE.match(tenant):
            logger.warning('oidc_signin: MICROSOFT_TENANT_ID is not a Directory '
                           '(tenant) ID; refusing sign-in token')
            raise SigninTokenError('tenant id is not a GUID')
        return (f'{MS_AUTHORITY}/{tenant}/v2.0',
                f'{MS_AUTHORITY}/{tenant}/discovery/v2.0/keys')

    try:
        unverified = jwt.decode(raw_token, options={'verify_signature': False})
    except Exception:
        raise SigninTokenError('not a JWT')
    tid = unverified.get('tid')
    tid = tid.strip().lower() if isinstance(tid, str) else ''
    if not _GUID_RE.match(tid):
        raise SigninTokenError('token has no valid tid')
    _warn_once('tenant-not-set', TENANT_NOT_SET_MESSAGE)
    return f'{MS_AUTHORITY}/{tid}/v2.0', MS_COMMON_JWKS_URI


def verify_signin_token(raw_token: str) -> dict:
    """Verify *raw_token* for sign-in and return its claims.

    Raises SigninTokenError for anything that is not a currently valid ID
    token issued by Microsoft Entra ID to ``MICROSOFT_CLIENT_ID``.  Opaque
    tokens and tokens issued for another audience are rejected.
    """
    client_id = signin_client_id()
    if not client_id:
        logger.warning('oidc_signin: MICROSOFT_CLIENT_ID is not configured; '
                       'refusing sign-in token')
        raise SigninTokenError('client id not configured')

    issuer, jwks_uri = _issuer_and_keys(raw_token)

    try:
        key = _get_jwks_client(jwks_uri).get_signing_key_from_jwt(raw_token).key
    except Exception as err:
        logger.warning('oidc_signin: could not obtain signing key: %s',
                       err.__class__.__name__)
        raise SigninTokenError('no signing key')

    try:
        claims = jwt.decode(
            raw_token,
            key,
            algorithms=list(ALLOWED_ALGORITHMS),
            audience=client_id,
            issuer=issuer,
            leeway=LEEWAY_SECONDS,
            options={
                'verify_signature': True,
                'verify_exp': True,
                'verify_aud': True,
                'verify_iss': True,
                'require': list(REQUIRED_CLAIMS),
            },
        )
    except jwt.ExpiredSignatureError:
        raise SigninTokenError('token expired')
    except jwt.InvalidAudienceError:
        raise SigninTokenError('invalid audience')
    except jwt.InvalidIssuerError:
        raise SigninTokenError('invalid issuer')
    except Exception as err:
        logger.warning('oidc_signin: token verification failed: %s',
                       err.__class__.__name__)
        raise SigninTokenError('invalid token')

    if str(claims.get('email_verified', True)).lower() == 'false':
        raise SigninTokenError('email not verified')
    return claims


def identity_from_claims(claims: dict) -> str:
    """The lower-cased login identity: ``email``, then ``upn``, then
    ``preferred_username`` (the Entra user principal name)."""
    for claim in IDENTITY_CLAIMS:
        value = claims.get(claim)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return ''
