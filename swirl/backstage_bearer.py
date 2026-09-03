'''
Backstage plugin-token verification for SWIRL.

Backstage's search backend mints one plugin token per query and hands it to
the search engine, which forwards it to SWIRL unchanged. The token is an
ES256 JWT with:

  header   typ  = 'vnd.backstage.plugin'
  claims   sub  = source plugin id   (e.g. 'search')
           aud  = target plugin id   (e.g. 'search')
           iat, exp
           obo  = optional nested limited user token whose 'sub' is the user
                  entity ref, e.g. 'user:default/sid'

There is no 'iss' claim, so this is a sibling verification path rather than a
general OIDC bearer path. Public keys are served by the Backstage backend at
  <backend>/api/search/.backstage/auth/v1/jwks.json

Settings:
  SWIRL_BACKSTAGE_JWKS_URL   full JWKS URL; empty disables the path
  SWIRL_BACKSTAGE_AUDIENCE   expected 'aud', default 'search'

Both empty means the path is disabled and no Bearer token is treated as a
Backstage token.
'''

import logging
import threading

import jwt
import requests
from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from rest_framework.authentication import BaseAuthentication

logger = logging.getLogger(__name__)

BACKSTAGE_TOKEN_TYP = 'vnd.backstage.plugin'
BACKSTAGE_ALGORITHMS = ['ES256', 'ES384', 'RS256']
BACKSTAGE_REQUIRED_CLAIMS = ['exp', 'iat', 'sub', 'aud']

BACKSTAGE_GROUP_NAME = 'Backstage Users'
BACKSTAGE_SERVICE_USERNAME = 'backstage:service'
BACKSTAGE_USER_PREFIX = 'backstage:'

# The permission set this repo requires of a normal search user. swirl/search.py
# needs view_searchprovider; swirl/views.py needs the search and result
# permissions below to create and read a Search.
BACKSTAGE_USER_PERMISSIONS = [
    ('searchprovider', 'view_searchprovider'),
    ('search', 'add_search'),
    ('search', 'change_search'),
    ('search', 'view_search'),
    ('result', 'add_result'),
    ('result', 'change_result'),
    ('result', 'view_result'),
]

# A service principal (a plugin token with no obo) only ingests and drives
# provider configuration; it is not a search user.
BACKSTAGE_SERVICE_PERMISSIONS = [
    ('searchprovider', 'change_searchprovider'),
    ('search', 'add_search'),
    ('search', 'view_search'),
]

BACKSTAGE_JWKS_TIMEOUT = 10

_jwks_client = None
_jwks_client_url = None
_jwks_client_lock = threading.Lock()


class BackstageTokenError(Exception):
    '''Raised when a Backstage plugin token cannot be verified.'''


class BackstageJWKClient(jwt.PyJWKClient):
    '''PyJWKClient that fetches over `requests` instead of urllib.

    Everything else (kid lookup, the JWK set cache and its lifespan, the
    signing-key LRU) is PyJWT's. Only the transport changes, so the whole
    stack, SWIRL's proxy and TLS configuration included, behaves the way
    every other outbound call in this code base does.
    '''

    def fetch_data(self):
        try:
            response = requests.get(
                self.uri, headers=self.headers, timeout=BACKSTAGE_JWKS_TIMEOUT,
            )
            response.raise_for_status()
            jwk_set = response.json()
        except Exception as err:
            raise jwt.exceptions.PyJWKClientConnectionError(
                f'Fail to fetch data from the url, err: "{err}"'
            ) from err
        if self.jwk_set_cache is not None:
            self.jwk_set_cache.put(jwk_set)
        return jwk_set


class BackstagePrincipal:
    '''The verified identity carried by a Backstage plugin token.'''

    def __init__(self, plugin, user_ref=None):
        self.plugin = plugin
        self.user_ref = user_ref

    @property
    def is_service(self):
        return not self.user_ref

    @property
    def username(self):
        if self.user_ref:
            return BACKSTAGE_USER_PREFIX + self.user_ref
        return BACKSTAGE_SERVICE_USERNAME

    def __repr__(self):
        return f'BackstagePrincipal(plugin={self.plugin!r}, user_ref={self.user_ref!r})'


def backstage_jwks_url():
    return (getattr(settings, 'SWIRL_BACKSTAGE_JWKS_URL', '') or '').strip()


def backstage_audience():
    return (getattr(settings, 'SWIRL_BACKSTAGE_AUDIENCE', '') or '').strip()


def is_backstage_enabled():
    '''The path is on only when a JWKS URL and an audience are both configured.'''
    return bool(backstage_jwks_url()) and bool(backstage_audience())


def is_backstage_token(raw):
    '''Unverified header read: does this look like a Backstage plugin token?'''
    if not raw:
        return False
    try:
        header = jwt.get_unverified_header(raw)
    except Exception as err:
        logger.debug(f'is_backstage_token: unreadable header: {err}')
        return False
    return header.get('typ') == BACKSTAGE_TOKEN_TYP


def _get_jwks_client():
    '''Return a PyJWKClient for the configured URL, rebuilt when the URL changes.'''
    global _jwks_client, _jwks_client_url
    url = backstage_jwks_url()
    if not url:
        raise BackstageTokenError('Backstage bearer verification is not configured')
    with _jwks_client_lock:
        if _jwks_client is None or _jwks_client_url != url:
            _jwks_client = BackstageJWKClient(url)
            _jwks_client_url = url
        return _jwks_client


def reset_jwks_client():
    '''Drop the cached client. Used by tests and by settings reloads.'''
    global _jwks_client, _jwks_client_url
    with _jwks_client_lock:
        _jwks_client = None
        _jwks_client_url = None


def _read_obo(claims):
    '''Return the user entity ref from the nested obo token, or None.

    The obo token's bytes are covered by the outer signature, so it is decoded
    without signature verification. Only its 'sub' is used.
    '''
    obo = claims.get('obo')
    if not obo:
        return None
    try:
        inner = jwt.decode(
            obo,
            options={'verify_signature': False, 'verify_exp': False, 'verify_aud': False},
        )
    except Exception as err:
        raise BackstageTokenError(f'Unreadable obo token: {err}')
    user_ref = inner.get('sub')
    if not user_ref:
        raise BackstageTokenError('obo token has no sub')
    return user_ref


def authenticate_backstage_token(raw):
    '''Verify a Backstage plugin token and return a BackstagePrincipal.

    Raises BackstageTokenError on any failure.
    '''
    if not is_backstage_enabled():
        raise BackstageTokenError('Backstage bearer verification is not configured')

    client = _get_jwks_client()
    try:
        signing_key = client.get_signing_key_from_jwt(raw)
    except Exception as err:
        raise BackstageTokenError(f'Unable to fetch the Backstage signing key: {err}')

    try:
        claims = jwt.decode(
            raw,
            signing_key.key,
            algorithms=BACKSTAGE_ALGORITHMS,
            audience=backstage_audience(),
            options={'require': BACKSTAGE_REQUIRED_CLAIMS},
        )
    except Exception as err:
        raise BackstageTokenError(f'Invalid Backstage token: {err}')

    plugin = claims.get('sub')
    if not plugin:
        raise BackstageTokenError('Backstage token has no sub')

    return BackstagePrincipal(plugin=plugin, user_ref=_read_obo(claims))


def _permission_objects(pairs):
    '''Resolve (model, codename) pairs to Permission rows in the swirl app.'''
    permissions = []
    for model, codename in pairs:
        try:
            content_type = ContentType.objects.get(app_label='swirl', model=model)
        except ContentType.DoesNotExist:
            logger.warning(f'backstage_bearer: no content type for swirl.{model}')
            continue
        try:
            permissions.append(
                Permission.objects.get(content_type=content_type, codename=codename)
            )
        except Permission.DoesNotExist:
            logger.warning(f'backstage_bearer: no permission {codename} for swirl.{model}')
    return permissions


def get_backstage_group():
    '''The 'Backstage Users' group, created with the normal search permissions.'''
    group, created = Group.objects.get_or_create(name=BACKSTAGE_GROUP_NAME)
    if created or not group.permissions.exists():
        group.permissions.set(_permission_objects(BACKSTAGE_USER_PERMISSIONS))
    return group


def get_or_create_backstage_user(principal):
    '''Map a principal to its Django user, provisioning on first sight.

    A user principal joins 'Backstage Users'. A service principal gets the
    narrower ingest permission set directly and does not join the group.
    '''
    user, created = User.objects.get_or_create(
        username=principal.username,
        defaults={'is_active': True},
    )
    if principal.is_service:
        if created or not user.user_permissions.exists():
            user.user_permissions.set(_permission_objects(BACKSTAGE_SERVICE_PERMISSIONS))
    else:
        group = get_backstage_group()
        if not user.groups.filter(pk=group.pk).exists():
            user.groups.add(group)
    if created:
        logger.info(f'backstage_bearer: provisioned {principal.username}')
    # Re-read so the permission cache reflects the group and permissions above.
    return User.objects.get(pk=user.pk)


class BackstagePrincipalAuthentication(BaseAuthentication):
    '''DRF authentication for a request BackstageTokenMiddleware already verified.

    The middleware runs before the view, verifies the plugin token and sets
    request.backstage_principal plus request.user on the Django request. DRF
    then resolves request.user again from its own authentication_classes and
    would otherwise fall back to AnonymousUser, so views that a Backstage
    principal must reach list this class first. It never verifies anything
    itself; it only carries the middleware's decision into DRF.

    The principal is returned as the auth object, so a view can tell a
    Backstage caller from a Token or Basic one with request.auth.
    '''

    def authenticate(self, request):
        principal = getattr(request._request, 'backstage_principal', None)
        if not isinstance(principal, BackstagePrincipal):
            return None
        user = getattr(request._request, 'user', None)
        if user is None or not user.is_authenticated:
            return None
        return (user, principal)

    def authenticate_header(self, request):
        return 'Bearer'
