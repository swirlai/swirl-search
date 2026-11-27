"""
swirl/signin_limit.py - a limit on failed password sign-ins.

After SWIRL_SIGNIN_FAILURE_LIMIT failed attempts for one username from one
client address inside a minute, further password attempts for that pair are
refused until the oldest of those failures is a minute old. It applies to
every path that checks a password through Django: the token login Galaxy uses,
the API and admin login pages, and HTTP Basic.

It slows guessing; it does not lock an account, so there is nothing to
unlock. The client address is the one the connection came from; behind a
reverse proxy that is the proxy, so the limit is per username there. The
counts live in Django's cache.
With the default in-memory cache they are per server process and are lost on
restart. Set SWIRL_SIGNIN_FAILURE_LIMIT to 0 to turn the limit off.
"""

import hashlib
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 60
LIMITED_FLAG = '_swirl_signin_limited'


def failure_limit():
    return int(getattr(settings, 'SWIRL_SIGNIN_FAILURE_LIMIT', 10) or 0)


def _key(request, username):
    # The address the connection came from. A forwarding header is not used:
    # the client writes it, so a different value on each attempt would step
    # round the limit. Behind a proxy every client shares the proxy's address
    # and the limit is then per username.
    address = (getattr(request, 'META', None) or {}).get('REMOTE_ADDR', '')
    digest = hashlib.sha256(f'{str(username).strip().lower()}|{address}'.encode()).hexdigest()
    return f'swirl-signin-failures:{digest}'


def _recent_failures(key):
    oldest = time.time() - WINDOW_SECONDS
    return [moment for moment in (cache.get(key) or []) if moment > oldest]


def seconds_until_allowed(request, username):
    """0 when a password attempt for *username* from this client may go
    ahead, else the whole seconds until it may."""
    limit = failure_limit()
    if not limit or request is None or not username:
        return 0
    failures = _recent_failures(_key(request, username))
    if len(failures) < limit:
        return 0
    return max(1, int(failures[-limit] + WINDOW_SECONDS - time.time()) + 1)


def record_failure(request, username):
    if not failure_limit() or request is None or not username:
        return
    key = _key(request, username)
    cache.set(key, _recent_failures(key) + [time.time()], WINDOW_SECONDS)


class SigninLimitBackend:
    """First in AUTHENTICATION_BACKENDS. It signs nobody in; it stops the
    password check for a username and client address that are over the limit.
    It has no get_user, so Django never records it as the backend of a session."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if password is None:
            return None
        if seconds_until_allowed(request, username):
            setattr(request, LIMITED_FLAG, True)
            logger.warning('signin_limit: too many failed sign-ins for one account from one address; attempt refused')
            raise PermissionDenied
        return None


def on_login_failed(sender, credentials=None, request=None, **kwargs):
    """Count a failed password check. An attempt this module refused is not
    counted, so the wait does not grow while a client keeps trying."""
    if request is None or getattr(request, LIMITED_FLAG, False):
        return
    record_failure(request, (credentials or {}).get('username'))
