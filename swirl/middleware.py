from rest_framework.authtoken.models import Token
from django.http import HttpResponseForbidden
from swirl.models import SearchProvider
from swirl.authenticators import *
import jwt
import logging as logger


SWIRL_AUTHENTICATORS_LIST = SearchProvider.AUTHENTICATOR_CHOICES
SWIRL_AUTHENTICATORS_DICT = {}
for t in SWIRL_AUTHENTICATORS_LIST:
    SWIRL_AUTHENTICATORS_DICT[t[0]]=eval(t[0])

class TokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(request.path)
        if (request.path == '/swirl/login/' or '/sapi/' not in request.path) and request.path != '/swirl/logout/':
            print('return')
            return self.get_response(request)
        if 'Authorization' not in request.headers:
            print('Authorization not in request.headers')
            return HttpResponseForbidden()

        auth_header = request.headers['Authorization']
        token = auth_header.split(' ')[1]
        try:
            token_obj = Token.objects.get(key=token)
            print(request.user)
            request.user = token_obj.user
        except Token.DoesNotExist:
            print('Token.DoesNotExist')
            return HttpResponseForbidden()
        print('return response')
        return self.get_response(request)

class SpyglassAuthenticatorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.debug(f'SpyglassAuthenticatorsMiddleware: {request.path}')
        if request.path == '/swirl/sapi/search/' or request.path == '/api/swirl/sapi/search/':
            logger.debug(f'SpyglassAuthenticatorsMiddleware - in the sapi path')
            for authenticator in SWIRL_AUTHENTICATORS_DICT:
                logger.debug(f'SpyglassAuthenticatorsMiddleware - {authenticator}')
                if f'{authenticator}-Authorization' in request.headers:
                    logger.debug(f'SpyglassAuthenticatorsMiddleware - one we care about')
                    token = request.headers[f'{authenticator}-Authorization']
                    expires_in = int(jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])['exp'])
                    ## Do we need refresh token ?
                    SWIRL_AUTHENTICATORS_DICT[authenticator]().set_session_data(request, token, '', expires_in)
                else:
                    logger.debug(f'SpyglassAuthenticatorsMiddleware - call set session data NULL TOKEN')
                    SWIRL_AUTHENTICATORS_DICT[authenticator]().set_session_data(request, '', '', 0)
        else:
            logger.debug(f'SpyglassAuthenticatorsMiddleware - No action')
        return self.get_response(request)
