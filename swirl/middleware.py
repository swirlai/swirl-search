import json
import logging

import jwt
import yaml
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from func_timeout import FunctionTimedOut, func_timeout
from rest_framework.authtoken.models import Token

from swirl.authenticators import *
from swirl.backstage_bearer import (
    BackstagePrincipal,
    BackstageTokenError,
    authenticate_backstage_token,
    get_or_create_backstage_user,
    is_backstage_enabled,
    is_backstage_token,
)

logger = logging.getLogger(__name__)


SWIRL_API_SEARCH_URLS = ["/api/swirl/search/", "/swirl/search/"]
SWIRL_API_RAG_URLS = ["/api/swirl/rag-search/", "/api/swirl/sapi/detail-search-rag/"]

# Paths under /sapi/ that TokenMiddleware must let through unauthenticated.
# The Backstage health endpoint is AllowAny by design (TECH_DESIGN
# section 3.7): the engine module polls it before it has a token, and the
# container HEALTHCHECK calls it with no credentials at all. It returns no
# secrets.
SWIRL_API_ANONYMOUS_URLS = [
    "/swirl/sapi/health/backstage/",
    "/api/swirl/sapi/health/backstage/",
]


class BackstageTokenMiddleware:
    '''Verify Backstage plugin tokens presented as "Authorization: Bearer <jwt>".

    Sibling of TokenMiddleware rather than a replacement: it claims only a
    request whose Bearer token carries the Backstage plugin "typ", and it runs
    only when SWIRL_BACKSTAGE_JWKS_URL and SWIRL_BACKSTAGE_AUDIENCE are both
    set. Every other request passes through untouched, with
    request.backstage_principal set to None so downstream code can rely on the
    attribute existing.
    '''

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.backstage_principal = None

        if not is_backstage_enabled():
            return self.get_response(request)

        auth_header = request.headers.get('Authorization', '')
        if not auth_header.lower().startswith('bearer '):
            return self.get_response(request)

        raw = auth_header.split(' ', 1)[1].strip()
        if not is_backstage_token(raw):
            return self.get_response(request)

        try:
            principal = authenticate_backstage_token(raw)
        except BackstageTokenError as err:
            logger.warning(f'BackstageTokenMiddleware: rejected token for {request.path}: {err}')
            return self.invalid_token()

        try:
            request.user = get_or_create_backstage_user(principal)
        except Exception as err:
            logger.error(f'BackstageTokenMiddleware: user mapping failed for {principal}: {err}')
            return self.invalid_token()

        request.backstage_principal = principal
        logger.debug(f'BackstageTokenMiddleware: authenticated {principal} for {request.path}')
        return self.get_response(request)

    def invalid_token(self):
        response = JsonResponse({'detail': 'Invalid Backstage token'}, status=401)
        response['WWW-Authenticate'] = 'Bearer error="invalid_token"'
        return response


class TokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if(request.path == '/api/swirl/sapi/branding/'):
            return self.get_response(request)

        if request.path in SWIRL_API_ANONYMOUS_URLS:
            return self.get_response(request)

        # A verified Backstage plugin token has already set request.user.
        # Only BackstageTokenMiddleware can put a real BackstagePrincipal here,
        # so the isinstance check is what makes this a bypass for a verified
        # Backstage caller and nothing else.
        if isinstance(getattr(request, 'backstage_principal', None), BackstagePrincipal):
            return self.get_response(request)

        if (request.path == '/swirl/login/' or request.path == '/swirl/oidc_authenticate/' or '/sapi/' not in request.path) and request.path != '/swirl/logout/':
            return self.get_response(request)
        if 'Authorization' not in request.headers:
            return HttpResponseForbidden()

        auth_header = request.headers['Authorization']
        # Defensive split: the Authorization header is expected to be
        # ``<scheme> <credentials>`` (e.g. ``Token abc123``). Anything
        # malformed — empty value, scheme-only, no space at all — used to
        # IndexError out of ``split(' ')[1]`` and surface as a 500.
        # Treat any malformed header as Forbidden, same as a token that
        # isn't on file. Symptoms before the fix: any /sapi/ request from
        # a client that sent ``Authorization: Token `` (empty value) or
        # ``Authorization: Bearer`` (no value) crashed instead of being
        # rejected, and Galaxy's getIsAIProviderExistsStatus error path
        # hid the AI drawer (including the ai_instructions textarea).
        parts = auth_header.split(' ', 1)
        if len(parts) != 2 or not parts[1].strip():
            return HttpResponseForbidden()
        token = parts[1].strip()
        try:
            token_obj = Token.objects.get(key=token)
            request.user = token_obj.user
        except Token.DoesNotExist:
            return HttpResponseForbidden()
        return self.get_response(request)

class SpyglassAuthenticatorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.debug(f'SpyglassAuthenticatorsMiddleware: {request.path}')
        if request.path == '/swirl/sapi/search/' or request.path == '/api/swirl/sapi/search/':
            logger.debug(f'SpyglassAuthenticatorsMiddleware - in the sapi path')
            for authenticator in SWIRL_AUTHENTICATORS_DISPATCH.keys():
                logger.debug(f'SpyglassAuthenticatorsMiddleware - {authenticator}')
                if f'Authorization{authenticator}' in request.headers:
                    logger.debug(f'SpyglassAuthenticatorsMiddleware - one we care about')
                    token = request.headers[f'Authorization{authenticator}']
                    expires_in = int(jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])['exp'])
                    ## Do we need refresh token ?
                    SWIRL_AUTHENTICATORS_DISPATCH.get(authenticator)().set_session_data(request, token, '', expires_in)
                else:
                    logger.debug(f'SpyglassAuthenticatorsMiddleware - call set session data NULL TOKEN')
                    SWIRL_AUTHENTICATORS_DISPATCH.get(authenticator)().set_session_data(request, '', '', 0)
        else:
            logger.debug(f'SpyglassAuthenticatorsMiddleware - No action')
        return self.get_response(request)

class SwaggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        format = request.GET.get('format')
        if '/swirl/swagger' in request.path and format and format == 'openapi':
            response = self.get_response(request)
            if response.status_code == 200:
                openapi_data = json.loads(response.content)
                yaml_content = yaml.dump(openapi_data, default_flow_style=False)
                response = HttpResponse(yaml_content, content_type='text/yaml')
                return response
            return self.get_response(request)
        return self.get_response(request)

class TimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        min_timeout = 1
        max_timeout = 180
        timeout_param = request.GET.get("rag_timeout")
        is_rag_url = request.path in SWIRL_API_RAG_URLS
        is_search_url = request.path in SWIRL_API_SEARCH_URLS
        has_search_rag_tag = (
            request.GET.get("rag", False)
            or request.GET.get("do_rag", "").lower() == "true"
        )

        logger.info(
            f"TimeoutMiddleware - init path {request.path} rag_timeout {timeout_param} rag {has_search_rag_tag} (rag:{request.GET.get('rag','<unset>')} or do_rag:{request.GET.get('do_rag','<unset>')})"
        )

        if timeout_param and ((is_search_url and has_search_rag_tag) or is_rag_url):
            logger.debug(
                f"Enabling RAG timeout for {request.path} and {timeout_param} seconds"
            )

            ## little method to wrap the request execution
            def execute_request_with_timeout():
                return self.get_response(request)

            ## parse the timeout value or fail the request
            try:
                timeout_duration = int(timeout_param)
            except ValueError:
                return HttpResponseBadRequest("Invalid timeout value provided")

            ## validate the timeout value
            if timeout_duration < min_timeout or timeout_duration > max_timeout:
                return HttpResponseBadRequest(
                    f"Timeout value must be between {min_timeout} and {max_timeout} seconds"
                )

            try:
                logger.info(f"Request timeout set to {timeout_duration} seconds")
                response = func_timeout(timeout_duration, execute_request_with_timeout)
            except FunctionTimedOut:
                logger.debug(
                    f"Raise timeout for {request.path} after {timeout_duration} seconds"
                )
                response = HttpResponse("Rag timed out", status=504)
        else:
            logger.debug(f"Disabling RAG timeout for {request.path}")
            response = self.get_response(request)

        return response
