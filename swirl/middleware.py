import json
import logging

import jwt
import yaml
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from func_timeout import FunctionTimedOut, func_timeout
from rest_framework.authtoken.models import Token

from swirl.authenticators import *

logger = logging.getLogger(__name__)


SWIRL_API_SEARCH_URLS = ["/api/swirl/search/", "/swirl/search/"]
SWIRL_API_RAG_URLS = ["/api/swirl/rag-search/", "/api/swirl/sapi/detail-search-rag/"]


class TokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if(request.path == '/api/swirl/sapi/branding/'):
            return self.get_response(request)

        if (request.path == '/swirl/login/' or request.path == '/swirl/oidc_authenticate/' or '/sapi/' not in request.path) and request.path != '/swirl/logout/':
            return self.get_response(request)
        if 'Authorization' not in request.headers:
            return HttpResponseForbidden()

        auth_header = request.headers['Authorization']
        token = auth_header.split(' ')[1]
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
