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
from django.http import Http404, HttpResponseForbidden, FileResponse, JsonResponse
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
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

import csv
import base64
import hashlib
import hmac

from swirl.models import *
from swirl.serializers import *
from swirl.models import SearchProvider, Search, Result, QueryTransform, Authenticator as AuthenticatorModel, OauthToken
from swirl.serializers import UserSerializer, GroupSerializer, SearchProviderSerializer, SearchSerializer, ResultSerializer, QueryTransformSerializer, QueryTransformNoCredentialsSerializer, LoginRequestSerializer, StatusResponseSerializer, AuthResponseSerializer
from swirl.authenticators.authenticator import Authenticator
from swirl.authenticators import *

module_name = 'views.py'

from swirl.tasks import update_microsoft_token_task
from swirl.search import search as run_search

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
    return render(request, 'index.html')

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
            return Response({'token': token.key, 'user': user.username})
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
                    return Response({ 'user': user.username, 'token': token.key })
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
    authentication_classes = [SessionAuthentication, BasicAuthentication]

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
            # search_task.delay(new_search.id, Authenticator().get_session_data(request))
            run_search(new_search.id, Authenticator().get_session_data(request),request=request)
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
            res = run_search(new_search.id, Authenticator().get_session_data(request), request=request)
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
            # search_task.delay(rerun_search.id, Authenticator().get_session_data(request))
            run_search(rerun_search.id, Authenticator().get_session_data(request), request=request)
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
            # search_task.delay(update_id, Authenticator().get_session_data(request))
            # time.sleep(SWIRL_SUBSCRIBE_WAIT)
            run_search(update_id, Authenticator().get_session_data(request), request=request)
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
            # search_task.delay(serializer.data['id'], Authenticator().get_session_data(request))
            logger.info(f"{request.user} search_post")
            run_search(serializer.data['id'], Authenticator().get_session_data(request), request=request)

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
            # search_task.delay(search.id, Authenticator().get_session_data(request))
            logger.info(f"{request.user} search_put {search.id}")
            run_search(search.id, Authenticator().get_session_data(request), request=request)
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
