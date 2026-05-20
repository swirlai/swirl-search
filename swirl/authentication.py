"""
Custom Django REST Framework authentication classes for SWIRL.
"""

from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication


class OptionalTokenAuthentication(TokenAuthentication):
    """
    A TokenAuthentication variant that returns ``None`` instead of raising
    ``AuthenticationFailed`` when an ``Authorization: Token <key>`` header
    is present but the key is unknown / inactive / malformed.

    Why this exists
    ---------------
    Stock ``rest_framework.authentication.TokenAuthentication`` raises
    ``AuthenticationFailed`` as soon as it sees an Authorization header
    that *looks* like Token auth but doesn't validate. DRF's auth chain
    treats that as a hard 401 — subsequent authentication classes in the
    viewset's ``authentication_classes`` list never get a chance.

    For viewsets that legitimately accept BOTH Token and Session auth
    (e.g. anything Galaxy can call), this is a problem: Galaxy stores
    its API token in localStorage and attaches it to every request, but
    the same browser also carries a Django session cookie set during
    form login. If the localStorage token is stale (expired, revoked,
    or carried over from a previous login in the same Selenium session)
    while the session cookie is still valid, the stock behaviour is:

        TokenAuthentication.authenticate() raises -> DRF returns 401
        SessionAuthentication.authenticate() never runs

    This class makes that case fall through instead — the request gets
    a chance to authenticate via the session cookie. Concrete impact:
    the SWIRL search-history delete flow used to round-trip a 403 (from
    CSRF on SessionAuth) and the Galaxy interceptor over-reacted by
    clearing localStorage. The original fix put Token auth first to
    bypass CSRF on safe-Token requests, but that exposed the
    stale-Token-but-valid-session 401 documented above. This class
    resolves both: Token wins when valid; Session is tried when Token
    is invalid.

    Security note
    -------------
    A bogus Token header from an unauthenticated client now returns 401
    via the BasicAuth/SessionAuth tail of the chain rather than the more
    specific "Invalid token" message TokenAuthentication would have
    produced. That is intentional — the failure mode is the same (401)
    and the diagnostic difference doesn't aid an attacker.
    """

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except exceptions.AuthenticationFailed:
            return None
