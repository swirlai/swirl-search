'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from swirl.mixers import *
import time
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.models import User, Group
from django.http import Http404, HttpResponseForbidden, FileResponse, JsonResponse, HttpResponse
from django.conf import settings
from django.db import Error
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.core.mail import send_mail
from swirl.utils import paginate
from django.conf import settings
from .forms import QueryTransformForm

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

import csv
import base64
import hashlib
import hmac

from swirl.models import *
from swirl.serializers import *
from swirl.models import SearchProvider, Search, Result, QueryTransform, Authenticator as AuthenticatorModel, OauthToken, AIProvider
from swirl.serializers import UserSerializer, DetailSearchRagSerializer, GroupSerializer, SearchProviderSerializer, SearchSerializer, ResultSerializer, QueryTransformSerializer, QueryTransformNoCredentialsSerializer, LoginRequestSerializer, StatusResponseSerializer, AuthResponseSerializer, AIProviderSerializer, AIProviderNoCredentialsSerializer
from swirl.authenticators.authenticator import Authenticator
from swirl.authenticators import *
from swirl.views_helpers.search_rag import SearchRag

module_name = 'views.py'

from swirl.tasks import update_microsoft_token_task
from swirl.search import search as run_search

def get_session_data_with_db_fallback(request):
    """
    Return session data for the authenticated user.

    For browser/Galaxy sessions the Microsoft token lives in request.session['user']
    (put there by the SWIRL middleware which extracts the Bearer the Angular MSAL
    client sends).  We also write-through to OauthToken so that API callers (e.g.
    Mike, which authenticates via Basic auth with no browser session) always have
    access to a fresh token.

    For API callers with no session we fall back to the OauthToken DB row.  If that
    token is expired we attempt a silent refresh via the stored refresh token before
    returning it.
    """
    import jwt as _jwt

    session_data = Authenticator().get_session_data(request)

    if session_data:
        # Write-through: keep the OauthToken DB in sync with the browser session so
        # that API callers always have the latest token without needing a browser.
        token = session_data.get('microsoft_access_token')
        refresh = session_data.get('microsoft_refresh_token', '')
        if token and getattr(request, 'user', None) and request.user.is_authenticated:
            try:
                OauthToken.objects.update_or_create(
                    owner=request.user, idp='Microsoft',
                    defaults={'token': token, 'refresh_token': refresh},
                )
                logger.debug(f"get_session_data_with_db_fallback: synced session token to DB for {request.user}")
            except Exception as _e:
                logger.debug(f"get_session_data_with_db_fallback: DB sync skipped: {_e}")
        return session_data

    # No browser session — look up the OauthToken DB row.
    oauth_token = None
    if getattr(request, 'user', None) and request.user.is_authenticated:
        try:
            oauth_token = OauthToken.objects.get(owner=request.user, idp='Microsoft')
            logger.debug(f"get_session_data_with_db_fallback: loaded token from DB for {request.user}")
        except OauthToken.DoesNotExist:
            logger.debug(f"get_session_data_with_db_fallback: no token for {request.user}, trying any Microsoft token")
    if oauth_token is None:
        oauth_token = OauthToken.objects.filter(idp='Microsoft').first()
        if oauth_token:
            logger.debug(f"get_session_data_with_db_fallback: using Microsoft token from owner={oauth_token.owner}")

    if oauth_token:
        # Decode the real JWT expiry so we can decide whether to refresh.
        exp = 9999999999
        try:
            payload = _jwt.decode(oauth_token.token, options={"verify_signature": False}, algorithms=["RS256"])
            exp = payload.get('exp', 0)
        except Exception:
            pass

        import time as _time
        if exp < int(_time.time()) and oauth_token.refresh_token:
            # Token is expired — try a silent refresh before giving up.
            logger.info(f"get_session_data_with_db_fallback: token expired for {oauth_token.owner}, attempting refresh")
            try:
                from swirl.authenticators.microsoft import Microsoft as _MicrosoftAuth
                _MicrosoftAuth().update_access_from_refresh_token(oauth_token.owner, oauth_token.refresh_token)
                oauth_token = OauthToken.objects.get(owner=oauth_token.owner, idp='Microsoft')
                logger.info(f"get_session_data_with_db_fallback: token refreshed for {oauth_token.owner}")
            except Exception as _e:
                logger.error(f"get_session_data_with_db_fallback: token refresh failed: {_e}")

        session_data = {
            'microsoft_access_token': oauth_token.token,
            'microsoft_refresh_token': oauth_token.refresh_token,
            'microsoft_access_token_expiration_time': 9999999999,
        }

    return session_data

from swirl.banner import SWIRL_VERSION

SWIRL_EXPLAIN = getattr(settings, 'SWIRL_EXPLAIN', True)
SWIRL_SUBSCRIBE_WAIT = getattr(settings, 'SWIRL_SUBSCRIBE_WAIT', 20)

def remove_duplicates(my_list):
    new_list = []
    seen = set()
    for d in my_list:
        key = (d['name'])
        if key not in seen:
            new_list.append(d)
            seen.add(key)
    return new_list


def return_authenticators(request):
    if not request.user.is_authenticated:
        return redirect('/swirl/api-auth/login?next=/swirl/authenticators.html')
    providers = SearchProvider.objects.filter(active=True, owner=request.user) | SearchProvider.objects.filter(active=True, shared=True)
    results = list()
    for provider in providers:
        name = None
        try:
            name = SearchProvider.CONNECTORS_AUTHENTICATORS[provider.connector]
            if not name:
                continue
        except:
            continue
        results.append({
            'name': name
        })
    results = remove_duplicates(results)
    return render(request, 'authenticators.html', {'authenticators': results})

def return_authenticators_list(request):
    if not request.user.is_authenticated:
        return redirect('/swirl/api-auth/login?next=/swirl/authenticators.html')
    providers = SearchProvider.objects.filter(active=True, owner=request.user) | SearchProvider.objects.filter(active=True, shared=True)
    results = list()
    for provider in providers:
        name = None
        try:
            name = SearchProvider.CONNECTORS_AUTHENTICATORS[provider.connector]
            if not name:
                continue
        except:
            continue
        results.append({
            'name': name
        })
    results = remove_duplicates(results)
    return Response(results, status=status.HTTP_200_OK)

########################################

def index(request):
    from swirl.banner import SWIRL_VERSION
    from swirl.models import SearchProvider
    from swirl.utils import is_running_celery_redis
    context = {
        'swirl_version': SWIRL_VERSION,
        'search_provider_count': SearchProvider.objects.filter(active=True).count(),
        'celery_status': 'Running' if is_running_celery_redis() else 'Not running',
    }
    return render(request, 'index.html', context)

########################################

class AuthenticatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthenticatorModel
        fields = '__all__'  # Replace with the actual fields you want to include

class AuthenticatorViewSet(viewsets.ModelViewSet):
    serializer_class = AuthenticatorSerializer

    def get_queryset(self):
        return AuthenticatorModel.objects.all()

    def list(self, request):
        return return_authenticators_list(request)

def authenticators(request):
    if request.method == 'POST':
        authenticator = request.POST.get('authenticator_name')

        res = SWIRL_AUTHENTICATORS_DISPATCH.get(authenticator)().update_token(request)
        if res == True:
            return return_authenticators(request)
        return res
    else:
        return return_authenticators(request)

########################################

def error(request):
    return render(request, 'error.html')

########################################
########################################

class LoginView(APIView):
    @extend_schema(request=LoginRequestSerializer, responses={200: AuthResponseSerializer})
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key, 'user': user.username, 'swirl_version': SWIRL_VERSION, 'is_superuser': user.is_superuser})
        else:
            return Response({'error': 'Invalid credentials'})

class LogoutView(APIView):
    serializer_class = None

    @extend_schema(
        responses={200: StatusResponseSerializer},
        parameters=[
            OpenApiParameter(name="Authorization", description="Authorization token", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER),
        ]
    )
    def post(self, request):
        auth_header = request.headers['Authorization']
        token = auth_header.split(' ')[1]
        token_obj = Token.objects.get(key=token)
        token = Token.objects.get(user=token_obj.user)
        if token:
            token.delete()
        return Response({'status': 'OK'})

@extend_schema(exclude=True)  # This excludes the entire viewset from Swagger documentation
class OidcAuthView(APIView):

    def post(self, request):
        if 'OIDC-Token' in request.headers:
            header = request.headers['OIDC-Token']
            token = header.split(' ')[1]
            if token:
                data = Microsoft().get_user(token)
                if data['mail']:
                    user = None
                    try:
                        user = User.objects.get(email=data['mail'])
                    except User.DoesNotExist:
                        user = User.objects.create_user(
                            username=data['mail'],
                            password='WQasdmwq2319dqwmk',
                            email=data['mail'],
                            is_superuser=True,
                            is_staff=True
                        )
                    token, created = Token.objects.get_or_create(user=user)
                    return Response({ 'user': user.username, 'token': token.key, 'swirl_version': SWIRL_VERSION, 'is_superuser': user.is_superuser })
                return HttpResponseForbidden()
            return HttpResponseForbidden()
        return HttpResponseForbidden()


@extend_schema(exclude=True)  # This excludes the entire viewset from Swagger documentation
class UpdateMicrosoftToken(APIView):

    def post(self, request):
        try:
            # just return success, don't call the task
            # result = update_microsoft_token_task.delay(headers).get()
            result = { 'user': request.user.username, 'status': 'success' }
            return Response(result)
        except:
            return HttpResponseForbidden()

class SearchProviderViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing SearchProviders.
    Use GET to list all, POST to create a new one.
    Add /<id>/ to DELETE, PUT or PATCH one.
    """
    queryset = SearchProvider.objects.all()
    serializer_class = SearchProviderSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    # pagination_class = None


    def list(self, request):

        # check permissions
        if not request.user.has_perm('swirl.view_searchprovider'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        shared_providers = SearchProvider.objects.filter(shared=True)
        self.queryset = shared_providers | SearchProvider.objects.filter(owner=self.request.user)

        serializer = SearchProviderNoCredentialsSerializer(self.queryset, many=True)
        if self.request.user.is_superuser:
            serializer = SearchProviderSerializer(self.queryset, many=True)
        return Response(paginate(serializer.data, self.request), status=status.HTTP_200_OK)

    ########################################

    def create(self, request):

        # check permissions
        if not request.user.has_perm('swirl.add_searchprovider'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # by default, if the user is superuser, the searchprovider is shared
        # if self.request.user.is_superuser:
        #    request.data['shared'] = 'true'
        # serializer = SearchProviderSerializer(data=request.data)
        # serializer.is_valid(raise_exception=True)
        # serializer.save(owner=self.request.user)
        # return Response(serializer.data, status=status.HTTP_201_CREATED)

        is_list = isinstance(request.data, list)

        # Modify data if the user is a superuser
        if request.user.is_superuser:
            if is_list:
                # Apply changes to each item in the list
                for item in request.data:
                    item['shared'] = 'true'
            else:
                # Apply changes to the single object
                request.data['shared'] = 'true'

        # Use 'many' parameter based on whether request.data is a list or not
        serializer = SearchProviderSerializer(data=request.data, many=is_list)
        serializer.is_valid(raise_exception=True)

        # Save the serialized data
        serializer.save(owner=request.user)

        # Return response
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    ########################################

    def retrieve(self, request, pk=None):

        # check permissions
        if not request.user.has_perm('swirl.view_searchprovider'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # security review for 1.7 - OK, filtered by owner
        if not (SearchProvider.objects.filter(pk=pk, owner=self.request.user).exists() or SearchProvider.objects.filter(pk=pk, shared=True).exists()):
            return Response('SearchProvider Object Not Found', status=status.HTTP_404_NOT_FOUND)

        searchprovider = SearchProvider.objects.get(pk=pk)

        if not self.request.user == searchprovider.owner:
            serializer = SearchProviderNoCredentialsSerializer(searchprovider)
        else:
            serializer = SearchProviderSerializer(searchprovider)

        return Response(serializer.data, status=status.HTTP_200_OK)

    ########################################

    def update(self, request, pk=None):

        # check permissions
        if not request.user.has_perm('swirl.change_searchprovider'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        # security review for 1.7 - OK, filtered by owner
        # note: shared providers cannot be updated
        if not SearchProvider.objects.filter(pk=pk, owner=self.request.user).exists():
            return Response('SearchProvider Object Not Found', status=status.HTTP_404_NOT_FOUND)

        searchprovider = SearchProvider.objects.get(pk=pk)
        searchprovider.date_updated = datetime.now()
        serializer = SearchProviderSerializer(instance=searchprovider, data=request.data)
        serializer.is_valid(raise_exception=True)
        # security review for 1.7 - OK, saved with owner
        serializer.save(owner=self.request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    ########################################

    def destroy(self, request, pk=None):

        # check permissions
        if not request.user.has_perm('swirl.delete_searchprovider'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # security review for 1.7 - OK, filtered by owner
        # note: shared providers cannot be destroyed
        if not SearchProvider.objects.filter(pk=pk, owner=self.request.user).exists():
            return Response('SearchProvider Object Not Found', status=status.HTTP_404_NOT_FOUND)

        searchprovider = SearchProvider.objects.get(pk=pk)
        searchprovider.delete()
        return Response('SearchProvider Object Deleted', status=status.HTTP_410_GONE)

    def partial_update(self, request, pk=None):
        return self.update(request, pk)

    # 10a: health-check endpoint — GET /swirl/searchproviders/{id}/test/
    # Runs a minimal test query against the provider and reports OK or FAIL.
    from rest_framework.decorators import action as drf_action

    @drf_action(detail=True, methods=['get'], url_path='test')
    def test_provider(self, request, pk=None):
        """Quick connectivity test for a single SearchProvider."""
        from swirl.models import Search
        from swirl.tasks import federate_task
        import uuid

        if not request.user.has_perm('swirl.view_searchprovider'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            provider = SearchProvider.objects.get(pk=pk)
        except SearchProvider.DoesNotExist:
            return Response({'status': 'FAIL', 'error': 'SearchProvider not found'},
                            status=status.HTTP_404_NOT_FOUND)

        if not (provider.owner == request.user or provider.shared):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # Create a transient Search object for the test query
        test_query = request.GET.get('q', 'test')
        try:
            test_search = Search.objects.create(
                owner=request.user,
                query_string=test_query,
                query_string_processed=test_query,
                searchprovider_list=[provider.id],
                status='NEW_SEARCH',
            )
            result = federate_task.apply(
                args=[test_search.id, provider.id, provider.connector, False, None, str(uuid.uuid4())],
                timeout=10,
            )
            test_search.delete()
            if result and result.successful():
                return Response({'status': 'OK', 'provider': provider.name,
                                 'retrieved': result.result if isinstance(result.result, int) else 0})
            else:
                return Response({'status': 'FAIL', 'provider': provider.name,
                                 'error': str(result.result) if result else 'No result'})
        except Exception as err:
            return Response({'status': 'FAIL', 'provider': provider.name, 'error': str(err)})

########################################
########################################

class SearchViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Search objects.
    Use GET to list all, POST to create a new one.
    Add /<id>/ to DELETE, PUT or PATCH one.
    Add ?q=<query_string> to the URL to create a Search with default settings
    Add ?qs=<query_string> to the URL to run a Search and get results directly
    Add &providers=<provider1_id>,<provider2_tag> etc to specify SearchProvider(s)
    Add ?rerun=<query_id> to fully re-execute a query, discarding previous results
    Add ?update=<query_id> to update the Search with new results from all sources
    Add ?search_tags=<list-of-tags> to add tags to this search
    """
    queryset = Search.objects.all()
    serializer_class = SearchSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]

    def report(self):
        return self.queryset

    def list(self, request):
        # check permissions
        if not request.user.has_perm('swirl.view_search'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        ########################################

        pre_query_processor_in = request.GET.get('pre_query_processor', None)
        if pre_query_processor_in:
            pre_query_processor_single_list = [pre_query_processor_in]
        else:
            pre_query_processor_single_list = []

        providers = []
        if 'providers' in request.GET.keys():
            providers = request.GET['providers']
            if ',' in providers:
                providers = providers.split(',')
            else:
                providers = [providers]

        tags = request.GET.get('search_tags', [])
        if tags:
            tags = tags.split(',')

        query_string = ""
        if 'q' in request.GET.keys():
            query_string = request.GET['q']
        if query_string:
            # check permissions
            if not (request.user.has_perm('swirl.add_search') and request.user.has_perm('swirl.change_search') and request.user.has_perm('swirl.add_result') and request.user.has_perm('swirl.change_result')):
                logger.warning(f"User {self.request.user} needs permissions add_search({request.user.has_perm('swirl.add_search')}), change_search({request.user.has_perm('swirl.change_search')}), add_result({request.user.has_perm('swirl.add_result')}), change_result({request.user.has_perm('swirl.change_result')})")
                return Response(status=status.HTTP_403_FORBIDDEN)
            # run search
            logger.debug(f"{module_name}: Search.create() from ?q")
            try:
                new_search = Search.objects.create(query_string=query_string,searchprovider_list=providers,owner=self.request.user, tags=tags)
            except Error as err:
                self.error(f'Search.create() failed: {err}')
            new_search.status = 'NEW_SEARCH'
            new_search.save()
            logger.info(f"{request.user} search_q {new_search.id}")
            # search_task.delay(new_search.id, get_session_data_with_db_fallback(request))
            run_search(new_search.id, get_session_data_with_db_fallback(request),request=request)
            return redirect(f'/swirl/results?search_id={new_search.id}')

        ########################################

        otf_result_mixer = None
        if 'result_mixer' in request.GET.keys():
            otf_result_mixer = str(request.GET['result_mixer'])

        explain = SWIRL_EXPLAIN
        if 'explain' in request.GET.keys():
            explain = str(request.GET['explain'])
            if explain.lower() == 'false':
                explain = False
            elif explain.lower() == 'true':
                explain = True

        provider = None
        if 'provider' in request.GET.keys():
            provider = int(request.GET['provider'])

        query_string = ""
        if 'qs' in request.GET.keys():
            query_string = request.GET['qs']
        if query_string:
            # check permissions
            if not (request.user.has_perm('swirl.add_search') and request.user.has_perm('swirl.change_search') and request.user.has_perm('swirl.add_result') and request.user.has_perm('swirl.change_result')):
                logger.warning(f"User {self.request.user} needs permissions add_search({request.user.has_perm('swirl.add_search')}), change_search({request.user.has_perm('swirl.change_search')}), add_result({request.user.has_perm('swirl.add_result')}), change_result({request.user.has_perm('swirl.change_result')})")
                return Response(status=status.HTTP_403_FORBIDDEN)
            # run search
            logger.debug(f"{module_name}: Search.create() from ?qs")
            try:
                # security review for 1.7 - OK, created with owner
                new_search = Search.objects.create(query_string=query_string,searchprovider_list=providers,owner=self.request.user,
                                                   pre_query_processors=pre_query_processor_single_list,tags=tags)
            except Error as err:
                self.error(f'Search.create() failed: {err}')
            new_search.status = 'NEW_SEARCH'
            new_search.save()
            # log info
            logger.info(f"{request.user} search_qs {new_search.id}")
            res = run_search(new_search.id, get_session_data_with_db_fallback(request), request=request)
            if not res:
                logger.info(f'Search failed: {new_search.status}!!')
                return Response(f'Search failed: {new_search.status}!!', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            if not Search.objects.filter(id=new_search.id).exists():
                logger.info('Search object creation failed!', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                return Response('Search object creation failed!', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # security review for 1.7 - OK, search id created
            search = Search.objects.get(id=new_search.id)
            tries = 0
            if search.status.endswith('_READY') or search.status == 'RESCORING':
                try:
                    if otf_result_mixer:
                        # call the specifixed mixer on the fly otf
                        results = alloc_mixer(otf_result_mixer)(search.id, search.results_requested, 1, explain, provider,request=request).mix()
                    else:
                        # call the mixer for this search provider
                        results = alloc_mixer(search.result_mixer)(search.id, search.results_requested, 1, explain, provider,request=request).mix()
                except NameError as err:
                    message = f'Error: NameError: {err}'
                    logger.error(f'{module_name}: {message}')
                    return
                except TypeError as err:
                    message = f'Error: TypeError: {err}'
                    logger.error(f'{module_name}: {message}')
                    return
                return Response(paginate(results, self.request), status=status.HTTP_200_OK)
            else:
                time.sleep(1)
            # end if
        # end if

        ########################################

        rerun_id = 0
        if 'rerun' in request.GET.keys():
            rerun_id = int(request.GET['rerun'])

        if rerun_id:
            # check permissions
            if not (request.user.has_perm('swirl.change_search') and request.user.has_perm('swirl.delete_result') and request.user.has_perm('swirl.add_result') and request.user.has_perm('swirl.change_result')):
                logger.warning(f"User {self.request.user} needs permissions change_search({request.user.has_perm('swirl.change_search')}), delete_result({request.user.has_perm('swirl.delete_result')}), add_result({request.user.has_perm('swirl.add_result')}), change_result({request.user.has_perm('swirl.change_result')})")
                return Response(status=status.HTTP_403_FORBIDDEN)
            # security check
            if not Search.objects.filter(id=rerun_id, owner=self.request.user).exists():
                return Response('Result Object Not Found', status=status.HTTP_404_NOT_FOUND)
            # security review for 1.7 - OK, filtered by search
            logger.debug(f"{module_name}: ?rerun!")
            rerun_search = Search.objects.get(id=rerun_id)
            old_results = Result.objects.filter(search_id=rerun_search.id)
            logger.warning(f"{module_name}: deleting Result objects associated with search {rerun_id}")
            for old_result in old_results:
                old_result.delete()
            rerun_search.status = 'NEW_SEARCH'
            # fix for https://github.com/swirlai/swirl-search/issues/35
            message = f"[{datetime.now()}] Rerun requested"
            rerun_search.messages = []
            rerun_search.messages.append(message)
            rerun_search.save()
            logger.info(f"{request.user} rerun {rerun_id}")
            # search_task.delay(rerun_search.id, get_session_data_with_db_fallback(request))
            run_search(rerun_search.id, get_session_data_with_db_fallback(request), request=request)
            return redirect(f'/swirl/results?search_id={rerun_search.id}')
        # end if

        ########################################

        update_id = 0
        if 'update' in request.GET.keys():
            update_id = request.GET['update']

        if update_id:
            # check permissions
            if not (request.user.has_perm('swirl.change_search') and request.user.has_perm('swirl.change_result')):
                logger.warning(f"User {self.request.user} needs permissions change_search({request.user.has_perm('swirl.change_search')}), change_result({request.user.has_perm('swirl.change_result')})")
                return Response(status=status.HTTP_403_FORBIDDEN)
            # security check
            if not Search.objects.filter(id=update_id, owner=self.request.user).exists():
                return Response('Result Object Not Found', status=status.HTTP_404_NOT_FOUND)
            logger.debug(f"{module_name}: ?update!")
            search.status = 'UPDATE_SEARCH'
            search.save()
            logger.info(f"{request.user} update {update_id}")
            # search_task.delay(update_id, get_session_data_with_db_fallback(request))
            # time.sleep(SWIRL_SUBSCRIBE_WAIT)
            run_search(update_id, get_session_data_with_db_fallback(request), request=request)
            return redirect(f'/swirl/results?search_id={update_id}')

        ########################################

        logger.debug(f"{module_name}: Search.list()!")

        # security review for 1.7 - OK, filtered by owner
        self.queryset = Search.objects.filter(owner=self.request.user)
        serializer = SearchSerializer(self.queryset, many=True)
        return Response(paginate(serializer.data, self.request), status=status.HTTP_200_OK)

    ########################################

    def create(self, request):

        # check permissions
        if not (request.user.has_perm('swirl.add_search') and request.user.has_perm('swirl.change_search') and request.user.has_perm('swirl.add_result') and request.user.has_perm('swirl.change_result')):
            logger.warning(f"User {self.request.user} needs permissions add_search({request.user.has_perm('swirl.add_search')}), change_search({request.user.has_perm('swirl.change_search')}), add_result({request.user.has_perm('swirl.add_result')}), change_result({request.user.has_perm('swirl.change_result')})")
            return Response(status=status.HTTP_403_FORBIDDEN)

        logger.debug(f"{module_name}: Search.create() from POST")

        serializer = SearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # security review for 1.7 - OK, create with owner
        serializer.save(owner=self.request.user)

        if not (self.request.user.has_perm('swirl.view_searchprovider')):
            # TO DO: SECURITY REVIEW
            if Search.objects.filter(id=serializer.data['id'], owner=self.request.user).exists():
                search = Search.objects.get(id=serializer.data['id'])
                search.status = 'ERR_NO_SEARCHPROVIDERS'
                search.save()
        else:
            # search_task.delay(serializer.data['id'], get_session_data_with_db_fallback(request))
            logger.info(f"{request.user} search_post")
            run_search(serializer.data['id'], get_session_data_with_db_fallback(request), request=request)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    ########################################

    def retrieve(self, request, pk=None):

        # check permissions
        if not request.user.has_perm('swirl.view_search'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # security check
        if not Search.objects.filter(pk=pk, owner=self.request.user).exists():
            return Response('Search Object Not Found', status=status.HTTP_404_NOT_FOUND)

        # security review for 1.7 - OK, filtered by owner
        self.queryset = Search.objects.get(pk=pk)
        serializer = SearchSerializer(self.queryset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    ########################################

    def update(self, request, pk=None):

        # check permissions
        if not (request.user.has_perm('swirl.change_search')):
            logger.warning(f"User {self.request.user} needs permissions change_search({request.user.has_perm('swirl.change_search')})")
            return Response(status=status.HTTP_403_FORBIDDEN)

        # security review for 1.7 - OK, filtered by owner
        if not Search.objects.filter(pk=pk, owner=self.request.user).exists():
            return Response('Search Object Not Found', status=status.HTTP_404_NOT_FOUND)

        logger.debug(f"{module_name}: Search.update()!")

        search = Search.objects.get(pk=pk)
        search.date_updated = datetime.now()
        serializer = SearchSerializer(instance=search, data=request.data)
        serializer.is_valid(raise_exception=True)
        # security review for 1.7 - OK, create with owner
        serializer.save(owner=self.request.user)
        # re-start queries if status appropriate
        if search.status == 'NEW_SEARCH':
            # check permissions
            if not (request.user.has_perm('swirl.add_search') and request.user.has_perm('swirl.change_search') and request.user.has_perm('swirl.add_result') and request.user.has_perm('swirl.change_result')):
                logger.warning(f"User {self.request.user} needs permissions add_search({request.user.has_perm('swirl.add_search')}), change_search({request.user.has_perm('swirl.change_search')}), add_result({request.user.has_perm('swirl.add_result')}), change_result({request.user.has_perm('swirl.change_result')})")
                return Response(status=status.HTTP_403_FORBIDDEN)
            # search_task.delay(search.id, get_session_data_with_db_fallback(request))
            logger.info(f"{request.user} search_put {search.id}")
            run_search(search.id, get_session_data_with_db_fallback(request), request=request)
        return Response(serializer.data, status=status.HTTP_200_OK)

    ########################################

    def destroy(self, request, pk=None):

        # check permissions
        if not request.user.has_perm('swirl.delete_search'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # security review for 1.7 - OK, filtered by owner
        if not Search.objects.filter(pk=pk, owner=self.request.user).exists():
            return Response('Search Object Not Found', status=status.HTTP_404_NOT_FOUND)

        logger.debug(f"{module_name}: Search.destroy()!")

        search = Search.objects.get(pk=pk)
        search.delete()
        return Response('Search Object Deleted', status=status.HTTP_410_GONE)

    def partial_update(self, request, pk=None):
        return self.update(request, pk)

########################################
########################################

class DetailSearchRagView(APIView):
    serializer_class = DetailSearchRagSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = []

    def get(self, request):
        logger.debug(f"DetailSearchRagView: {request.GET}")
        search_rag = SearchRag(request)
        result = search_rag.process_rag()
        serializer = DetailSearchRagSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

########################################
########################################


class ResultViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Result objects, including Mixed Results
    Use GET to list all, POST to create a new one.
    Add /<id>/ to DELETE, PUT or PATCH one.
    Add ?search_id=<search_id> to the base URL to view mixed results with the default mixer
    Add &result_mixer=<MixerName> to the above URL specify the result mixer to use
    Add &explain=False to hide the relevancy explanation for each result
    Add &provider=<provider_id> to filter results to one SearchProvider
    """
    queryset = Result.objects.all()
    serializer_class = ResultSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]

    def list(self, request):
        # check permissions
        if not (request.user.has_perm('swirl.view_search') and request.user.has_perm('swirl.view_result')):
            logger.warning(f"User {self.request.user} needs permissions view_search({request.user.has_perm('swirl.view_search')}), view_result({request.user.has_perm('swirl.view_result')})")
            return Response(status=status.HTTP_403_FORBIDDEN)

        search_id = 0
        if 'search_id' in request.GET.keys():
            search_id = int(request.GET['search_id'])

        page = 1
        if 'page' in request.GET.keys():
            page = int(request.GET['page'])

        otf_result_mixer = None
        if 'result_mixer' in request.GET.keys():
            otf_result_mixer = str(request.GET['result_mixer'])

        explain = SWIRL_EXPLAIN
        if 'explain' in request.GET.keys():
            explain = str(request.GET['explain'])
            if explain.lower() == 'false':
                explain = False
            elif explain.lower() == 'true':
                explain = True

        providers = []
        if 'providers' in request.GET.keys():
            providers = request.GET['providers']
            if ',' in providers:
                providers = providers.split(',')
            else:
                providers = [providers]

        provider = None
        if 'provider' in request.GET.keys():
            provider = int(request.GET['provider'])

        if len(providers) > 0:
            # ignore provider if providers is specified
            provider = providers

        mark_all_read = False
        if 'mark_all_read' in request.GET.keys():
            mark_all_read = bool(request.GET['mark_all_read'])

        if search_id:
            # security review for 1.7 - OK, filtered by owner
            if not Search.objects.filter(id=search_id, owner=self.request.user).exists():
                return Response('Result Object Not Found', status=status.HTTP_404_NOT_FOUND)
            # security review for 1.7 - OK, filtered by owner
            logger.debug(f"{module_name}: Calling mixer from ?search_id")
            search = Search.objects.get(id=search_id)
            if search.status.endswith('_READY') or search.status == 'RESCORING':
                try:
                    if otf_result_mixer:
                        # call the specifixed mixer on the fly otf
                        results = alloc_mixer(otf_result_mixer)(search.id, search.results_requested, page, explain, provider, mark_all_read,request=request).mix()
                    else:
                        # call the mixer for this search provider
                        results = alloc_mixer(search.result_mixer)(search.id, search.results_requested, page, explain, provider, mark_all_read, request=request).mix()
                except NameError as err:
                    message = f'Error: NameError: {err}'
                    logger.error(f'{module_name}: {message}')
                    return
                except TypeError as err:
                    message = f'Error: TypeError: {err}'
                    logger.error(f'{module_name}: {message}')
                    return
                return Response(paginate(results, self.request), status=status.HTTP_200_OK)
            else:
                return Response('Result Object Not Ready Yet', status=status.HTTP_503_SERVICE_UNAVAILABLE)
            # end if
        else:
            # security review for 1.7 - OK, filtered by owner
            self.queryset = Result.objects.filter(owner=self.request.user)
            serializer = ResultSerializer(self.queryset, many=True)
            return Response(paginate(serializer.data, self.request), status=status.HTTP_200_OK)
        # end if

    ########################################

    def retrieve(self, request, pk=None):

        # check permissions
        if not request.user.has_perm('swirl.view_result'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # security review for 1.7 - OK, filtered by owner
        if not Result.objects.filter(pk=pk, owner=self.request.user).exists():
            return Response('Result Object Not Found', status=status.HTTP_404_NOT_FOUND)

        result = Result.objects.get(pk=pk)
        serializer = ResultSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)

    ########################################

    def update(self, request, pk=None):

        # check permissions
        if not request.user.has_perm('swirl.change_result'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # security review for 1.7 - OK, filtered by owner
        if not Result.objects.filter(pk=pk, owner=self.request.user).exists():
            return Response('Search Object Not Found', status=status.HTTP_404_NOT_FOUND)

        logger.debug(f"{module_name}: Result.update()!")

        result = Result.objects.get(pk=pk)
        result.date_updated = datetime.now()
        serializer = ResultSerializer(instance=result, data=request.data)
        serializer.is_valid(raise_exception=True)
        # security review for 1.7 - OK, saved with owner
        serializer.save(owner=self.request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    ########################################

    def destroy(self, request, pk=None):

        # check permissions
        if not request.user.has_perm('swirl.delete_result'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # security review for 1.7 - OK, filtered by owner
        if not Result.objects.filter(pk=pk, owner=self.request.user).exists():
            return Response('Result Object Not Found', status=status.HTTP_404_NOT_FOUND)

        logger.debug(f"{module_name}: Result.destroy()!")

        result = Result.objects.get(pk=pk)
        result.delete()
        return Response('Result Object Deleted!', status=status.HTTP_410_GONE)

    def partial_update(self, request, pk=None):
        return self.update(request, pk)

########################################
########################################

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows management of Users objects.
    Use GET to list all objects, POST to create a new one.
    Add /<id>/ to DELETE, PUT or PATCH one.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]

########################################
########################################

class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows management of Group objects.
    Use GET to list all objects, POST to create a new one.
    Add /<id>/ to DELETE, PUT or PATCH one.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]

########################################
########################################

class QueryTransformViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing SearchProviders.
    Use GET to list all, POST to create a new one.
    Add /<id>/ to DELETE, PUT or PATCH one.
    """
    queryset = QueryTransform.objects.all()
    serializer_class = QueryTransformSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    # pagination_class = None

    def list(self, request):

        # check permissions
        if not request.user.has_perm('swirl.view_querytransform'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        shared_xforms = QueryTransform.objects.filter(shared=True)
        self.queryset = shared_xforms | QueryTransform.objects.filter(owner=self.request.user)

        serializer = QueryTransformSerializer(self.queryset, many=True)
        if self.request.user.is_superuser:
            serializer = QueryTransformSerializer(self.queryset, many=True)
        return Response(paginate(serializer.data, self.request), status=status.HTTP_200_OK)

    ########################################

    def create(self, request):

        # check permissions
        if not request.user.has_perm('swirl.add_querytransform'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # by default, if the user is superuser, the searchprovider is shared
        if self.request.user.is_superuser:
           request.data['shared'] = 'true'

        serializer = QueryTransformSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=self.request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    ########################################

    def retrieve(self, request, pk=None):
        if not request.user.has_perm('swirl.view_querytransform'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # security review for 1.7 - OK, filtered by owner
        if not (QueryTransform.objects.filter(pk=pk, owner=self.request.user).exists() or QueryTransform.objects.filter(pk=pk, shared=True).exists()):
            return Response('QueryTransform Object Not Found', status=status.HTTP_404_NOT_FOUND)

        query_xfr = QueryTransform.objects.get(pk=pk)

        if not self.request.user == query_xfr.owner:
            serializer = QueryTransformNoCredentialsSerializer(query_xfr)
        else:
            serializer = QueryTransformSerializer(query_xfr)

        return Response(serializer.data, status=status.HTTP_200_OK)

    ########################################

    def update(self, request, pk=None):

        # check permissions
        if not request.user.has_perm('swirl.change_querytransform'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # security review for 1.7 - OK, filtered by owner
        # note: shared providers cannot be updated
        if not QueryTransform.objects.filter(pk=pk, owner=self.request.user).exists():
            return Response('QueryTransform Object Not Found', status=status.HTTP_404_NOT_FOUND)

        query_xfr = QueryTransform.objects.get(pk=pk)
        query_xfr.date_updated = datetime.now()
        serializer = QueryTransformSerializer(instance=query_xfr, data=request.data)
        serializer.is_valid(raise_exception=True)
        # security review for 1.7 - OK, saved with owner
        serializer.save(owner=self.request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    ########################################

    def destroy(self, request, pk=None):
        # check permissions
        if not request.user.has_perm('swirl.delete_querytransform'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # security review for 1.7 - OK, filtered by owner
        # note: shared providers cannot be destroyed
        if not QueryTransform.objects.filter(pk=pk, owner=self.request.user).exists():
            return Response('QueryTransform Object Not Found', status=status.HTTP_404_NOT_FOUND)

        searchprovider = QueryTransform.objects.get(pk=pk)
        searchprovider.delete()
        return Response('QueryTransformation Object Deleted', status=status.HTTP_410_GONE)

    def partial_update(self, request, pk=None):
        return self.update(request, pk)

def query_transform_form(request):
    if request.method == 'POST':
        form = QueryTransformForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['file']
            content = csv_file.read().decode('utf-8')
            reader = csv.reader(content.splitlines())

            # Convert the CSV data to a string format suitable for the TextField
            csv_content = "\n".join([",".join(row) for row in reader])

            # Get the name from the form or set it to None if it's not provided
            qrx_name = form.cleaned_data['name'] or None

            # Get the type of the transform
            in_type = form.cleaned_data.get('content_type')

            # Save the content in a new CSVData object
            qrx_data = QueryTransform(config_content=csv_content, qrx_type=in_type, owner=request.user, name=qrx_name)

            # Persist it
            qrx_data.save()

            return redirect('index') # Replace 'success' with the name of your success URL
    else:
        form = QueryTransformForm
    return render(request, 'query_transform.html', {'form': form})

@extend_schema(exclude=True)  # This excludes the entire viewset from Swagger documentation
class BrandingConfigurationViewSet(viewsets.ModelViewSet):
    """
    fetch logos unconditionally from the upload
    """

    def list(self, request):

        logger.debug(f"{module_name}: TRACE LIST permission on Branding")

        target = request.GET.get('target', '')

        # If the target parameter is light or dark, only serve the requested image
        if target == 'light' or target == 'dark':
            location = f'{settings.MEDIA_ROOT}logo_highres_{target}.png'
            image = open(location, 'rb')
            logger.debug(f'returning logo from image {location}')
            return FileResponse(image, status=status.HTTP_200_OK)
        elif target == 'config':
            ## return not found and let the UI use its own defaults
            logger.debug(f'returning empty config {target}')
            return JsonResponse({}, status=status.HTTP_200_OK)
        else:
            return Response('Logo Object Not Found', status=status.HTTP_404_NOT_FOUND)


class IsChatAIProviderExists(viewsets.ModelViewSet):

    def list(self, request):
        # TODO: The Community Edition does not include an AI provider model.
        # For now, we are setting the status to True as a temporary workaround.
        # This should be updated once the AI provider model is implemented.
        # This validation is used to enable or disable the second row of Search RAG.
        return Response({'status': 'True'}, status=status.HTTP_200_OK)


class FetchDocumentView(APIView):
    """
    Proxy endpoint for fetching document bytes on behalf of the LLM / Mike integration.

    GET /swirl/fetch-document/?url=<encoded_url>[&provider_id=<int>]

    If provider_id is supplied the SearchProvider's page_fetch_config_json headers
    are forwarded to the upstream request so that authenticated connectors (e.g.
    SharePoint with a pre-configured Authorization header) work correctly.
    """

    permission_classes = [IsAuthenticated]

    # Hostname patterns that require a Microsoft Bearer token.
    M365_HOSTS = (
        'sharepoint.com',
        'graph.microsoft.com',
        'outlook.office365.com',
        'teams.microsoft.com',
    )

    def _get_microsoft_bearer(self, request):
        """Return a 'Bearer <token>' string if a valid Microsoft token is available, else None."""
        session_data = get_session_data_with_db_fallback(request)
        if session_data and session_data.get('microsoft_access_token'):
            return f"Bearer {session_data['microsoft_access_token']}"
        return None

    @staticmethod
    def _is_sharepoint_url(url: str) -> bool:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        return host.endswith('sharepoint.com') and '/_api/' not in url and 'graph.microsoft.com' not in host

    @staticmethod
    def _parse_sharepoint_url(url: str):
        """
        Parse a SharePoint web-viewer URL into components.
        Returns (host, site_name, sub_path) or None if not parseable.
        sub_path is the path within the library (after library name).
        """
        from urllib.parse import urlparse, unquote
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = unquote(parsed.path)  # decode %20 etc for clean parsing
        # Expect: /sites/{site}/{library}/{sub-path...}
        parts = path.lstrip('/').split('/')
        if len(parts) < 4 or parts[0] != 'sites':
            return None
        site_name = parts[1]
        # parts[2] is the document library name ("Shared Documents") — skip it,
        # it IS the drive root for the default library.
        sub_path = '/'.join(parts[3:])
        return host, site_name, sub_path

    def _fetch_sharepoint_bytes(self, original_url: str, bearer: str):
        """
        Fetch a SharePoint document via a proper three-step Graph API flow:

          1. Resolve site → GET /v1.0/sites/{host}:/sites/{name}  → site ID
          2. Get file metadata → GET /v1.0/sites/{id}/drive/root:/{path}
             → extract @microsoft.graph.downloadUrl (pre-auth blob URL)
          3. Download blob (no auth needed)

        Using the site ID in step 2 avoids the chained path-based syntax
        that Graph rejects in certain edge cases.
        """
        import requests as _requests
        from urllib.parse import quote

        parsed = self._parse_sharepoint_url(original_url)
        if not parsed:
            raise ValueError(f"Cannot parse SharePoint URL: {original_url}")
        host, site_name, sub_path = parsed

        auth_headers = {'Authorization': bearer, 'Accept': 'application/json'}

        # Step 1: resolve site to get its ID
        site_url = f"https://graph.microsoft.com/v1.0/sites/{host}:/sites/{quote(site_name)}"
        logger.debug(f"FetchDocumentView: Graph site lookup: {site_url}")
        site_resp = _requests.get(site_url, headers=auth_headers, timeout=15)
        logger.debug(f"FetchDocumentView: Graph site response: {site_resp.status_code}")
        if not site_resp.ok:
            raise ValueError(f"Graph site lookup returned {site_resp.status_code}: {site_resp.text[:300]}")
        site_id = site_resp.json().get('id')
        if not site_id:
            raise ValueError(f"No id in Graph site response: {list(site_resp.json().keys())}")

        # Step 2: get file metadata using site ID (avoids chained path syntax)
        file_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{quote(sub_path, safe='/')}"
        logger.debug(f"FetchDocumentView: Graph file metadata: {file_url}")
        file_resp = _requests.get(file_url, headers=auth_headers, timeout=15)
        logger.debug(f"FetchDocumentView: Graph file response: {file_resp.status_code}")
        if not file_resp.ok:
            raise ValueError(f"Graph file metadata returned {file_resp.status_code}: {file_resp.text[:300]}")

        download_url = file_resp.json().get('@microsoft.graph.downloadUrl')
        if not download_url:
            raise ValueError(f"No @microsoft.graph.downloadUrl in response: {list(file_resp.json().keys())}")

        # Step 3: download from pre-authenticated blob URL (no Bearer needed)
        logger.debug("FetchDocumentView: downloading from pre-auth blob URL")
        dl_resp = _requests.get(download_url, timeout=60)
        if not dl_resp.ok:
            raise ValueError(f"Blob download returned {dl_resp.status_code}")

        content_type = dl_resp.headers.get('Content-Type', 'application/octet-stream').split(';')[0].strip()
        return dl_resp.content, content_type

    def get(self, request):
        from swirl.web_page import PageFetcherFactory
        from urllib.parse import urlparse

        fetch_url = request.GET.get('url', '').strip()
        if not fetch_url:
            return Response({'error': 'url parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        # ── SharePoint URLs: use Graph two-step fetch (metadata → downloadUrl) ──
        if self._is_sharepoint_url(fetch_url):
            bearer = self._get_microsoft_bearer(request)
            if not bearer:
                logger.warning(f"FetchDocumentView: SharePoint URL but no Microsoft token for {request.user}")
                return Response({'error': 'No Microsoft token available'}, status=status.HTTP_502_BAD_GATEWAY)
            try:
                content, content_type = self._fetch_sharepoint_bytes(fetch_url, bearer)
                filename = fetch_url.rstrip('/').split('/')[-1].split('?')[0] or 'document'
                response = HttpResponse(content, content_type=content_type)
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            except Exception as err:
                logger.warning(f"FetchDocumentView: SharePoint fetch failed: {err}")
                return Response({'error': str(err)}, status=status.HTTP_502_BAD_GATEWAY)

        # ── All other URLs: use PageFetcher as before ──
        provider_id = request.GET.get('provider_id', None)
        options = {"cache": "false"}

        if provider_id:
            try:
                provider = SearchProvider.objects.get(pk=int(provider_id))
                cfg = provider.page_fetch_config_json or {}
                if isinstance(cfg, dict):
                    options.update(cfg)
            except (SearchProvider.DoesNotExist, ValueError):
                pass

        try:
            parsed_host = urlparse(fetch_url).netloc.lower()
            if any(parsed_host.endswith(h) for h in self.M365_HOSTS):
                bearer = self._get_microsoft_bearer(request)
                if bearer:
                    options.setdefault('headers', {})
                    options['headers']['Authorization'] = bearer
                    logger.debug(f"FetchDocumentView: injected Microsoft Bearer for {parsed_host}")

            pf = PageFetcherFactory.alloc_page_fetcher(url=fetch_url, options=options)
            if pf is None:
                return Response({'error': f'No page fetcher available for {fetch_url}'}, status=status.HTTP_502_BAD_GATEWAY)

            page = pf.get_page()
            content = page.get_content()
            content_type = page._response.headers.get('Content-Type', 'application/octet-stream')

        except Exception as err:
            logger.warning(f"FetchDocumentView: error fetching {fetch_url}: {err}")
            return Response({'error': str(err)}, status=status.HTTP_502_BAD_GATEWAY)

        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{fetch_url.split("/")[-1].split("?")[0] or "document"}"'
        return response


# ---------------------------------------------------------------------------
# AIProvider CRUD viewset
# ---------------------------------------------------------------------------

class AIProviderViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing AIProvider objects.
    GET lists all shared + owned providers; POST creates a new one.
    Add /<id>/ for GET, PUT, PATCH, DELETE on a single object.
    Superusers receive api_key in responses; other users receive the
    no-credentials serializer so keys are never echoed back.
    """
    queryset = AIProvider.objects.all()
    serializer_class = AIProviderSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]

    def list(self, request):
        if not request.user.has_perm('swirl.view_aiprovider'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        qs = (
            AIProvider.objects.filter(shared=True) |
            AIProvider.objects.filter(owner=request.user)
        )
        if request.user.is_superuser:
            serializer = AIProviderSerializer(qs, many=True)
        else:
            serializer = AIProviderNoCredentialsSerializer(qs, many=True)
        return Response(paginate(serializer.data, request), status=status.HTTP_200_OK)

    def create(self, request):
        if not request.user.has_perm('swirl.add_aiprovider'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        if request.user.is_superuser:
            data['shared'] = 'true'
        serializer = AIProviderSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        if not request.user.has_perm('swirl.view_aiprovider'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        qs = (
            AIProvider.objects.filter(pk=pk, owner=request.user) |
            AIProvider.objects.filter(pk=pk, shared=True)
        )
        if not qs.exists():
            return Response('AIProvider Object Not Found', status=status.HTTP_404_NOT_FOUND)
        obj = AIProvider.objects.get(pk=pk)
        if request.user == obj.owner or request.user.is_superuser:
            serializer = AIProviderSerializer(obj)
        else:
            serializer = AIProviderNoCredentialsSerializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, pk=None, partial=False):
        if not request.user.has_perm('swirl.change_aiprovider'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not AIProvider.objects.filter(pk=pk, owner=request.user).exists():
            return Response('AIProvider Object Not Found', status=status.HTTP_404_NOT_FOUND)
        obj = AIProvider.objects.get(pk=pk)
        obj.date_updated = datetime.now()
        serializer = AIProviderSerializer(instance=obj, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, pk=None):
        return self.update(request, pk=pk, partial=True)

    def destroy(self, request, pk=None):
        if not request.user.has_perm('swirl.delete_aiprovider'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not AIProvider.objects.filter(pk=pk, owner=request.user).exists():
            return Response('AIProvider Object Not Found', status=status.HTTP_404_NOT_FOUND)
        AIProvider.objects.get(pk=pk).delete()
        return Response('AIProvider Object Deleted', status=status.HTTP_204_NO_CONTENT)