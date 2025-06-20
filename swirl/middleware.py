from rest_framework.authtoken.models import Token
from django.http import HttpResponseForbidden, HttpResponse
from swirl.authenticators import *
import json
import yaml
import jwt
import logging
logger = logging.getLogger(__name__)


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