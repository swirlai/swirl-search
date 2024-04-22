from rest_framework.authtoken.models import Token
from django.http import HttpResponseForbidden, HttpResponse
from swirl.models import Search
from swirl.authenticators import *
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from urllib.parse import parse_qs
from django.core.exceptions import ObjectDoesNotExist
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


class WebSocketTokenMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        token_key = query_params.get("token", [""])[0]
        rag_query_items = query_params.get("rag_items", [""])[0]
        if rag_query_items:
            scope['rag_query_items'] = rag_query_items.split(',')
        else:
            scope['rag_query_items'] = []

        ### DJANGO TOKEN CHECKING

        if token_key:
            logger.debug(f'WebSocketTokenMiddleware - Token exists')
            user = await self.get_user_from_token(token_key)
            if user:
                logger.debug(f'WebSocketTokenMiddleware - Token is valid')
                scope["user"] = user
                print(user.username)

                search_id = query_params.get("search_id", [""])[0]
                if search_id:
                    logger.debug(f'WebSocketTokenMiddleware - Search ID exists')
                    found = await self.get_search_by_id_and_user(search_id, user)
                    if found:
                        logger.debug(f'WebSocketTokenMiddleware - Search for current user {user} was found')
                        scope["search_id"] = search_id
                    else:
                        logger.debug(f'WebSocketTokenMiddleware - Search for current user {user} was not found')
                else:
                    logger.debug(f'WebSocketTokenMiddleware - Search ID does not exist')
            else:
                logger.debug(f'WebSocketTokenMiddleware - Token is not valid')
        else:
            logger.debug(f'WebSocketTokenMiddleware - Token does not exist')

        return await super().__call__(scope, receive, send)


    @database_sync_to_async
    def get_user_from_token(self, token_key):
        try:
            return Token.objects.get(key=token_key).user
        except Token.DoesNotExist:
            return None

    @database_sync_to_async
    def get_search_by_id_and_user(self, search_id, user):
        try:
            return Search.objects.filter(pk=search_id, owner=user).exists()
        except ObjectDoesNotExist:
            return None

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