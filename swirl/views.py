'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from swirl.mixers import *
import time
import logging as logger
from datetime import datetime

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.models import User, Group
from django.http import Http404
from django.conf import settings
from django.db import Error
from django.views.decorators.csrf import csrf_exempt

from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.core.mail import send_mail
from swirl.utils import paginate
from django.conf import settings
from .forms import RegistrationForm, QueryTransformForm

from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework import viewsets, status
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

import csv
import base64
import hashlib
import hmac

from swirl.models import *
from swirl.serializers import *
from swirl.models import SearchProvider, Search, Result, QueryTransform
from swirl.serializers import UserSerializer, GroupSerializer, SearchProviderSerializer, SearchSerializer, ResultSerializer, QueryTransformSerializer, QueryTrasnformNoCredentialsSerializer
from swirl.authenticators.authenticator import Authenticator
from swirl.authenticators import *



module_name = 'views.py'

from swirl.tasks import search_task, rescore_task
from swirl.search import search as run_search

SWIRL_OBJECT_LIST = Search.MIXER_CHOICES
SWIRL_AUTHENTICATORS_LIST = SearchProvider.AUTHENTICATOR_CHOICES

SWIRL_OBJECT_DICT = {}
for t in SWIRL_OBJECT_LIST:
    SWIRL_OBJECT_DICT[t[0]]=eval(t[0])

SWIRL_AUTHENTICATORS_DICT = {}
for t in SWIRL_AUTHENTICATORS_LIST:
    SWIRL_AUTHENTICATORS_DICT[t[0]]=eval(t[0])
SWIRL_EXPLAIN = getattr(settings, 'SWIRL_EXPLAIN', True)
SWIRL_RERUN_WAIT = getattr(settings, 'SWIRL_RERUN_WAIT', 8)
SWIRL_RESCORE_WAIT = getattr(settings, 'SWIRL_RESCORE_WAIT', 5)
SWIRL_SUBSCRIBE_WAIT = getattr(settings, 'SWIRL_SUBSCRIBE_WAIT', 20)
SWIRL_Q_WAIT = getattr(settings, 'SWIRL_Q_WAIT', 7)


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

def registration(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            login(request, user)
            # Generate and sign token
            token = base64.urlsafe_b64encode(user.id.to_bytes(4, 'big')).decode()
            secret_key = settings.SECRET_KEY.encode()
            signature = hmac.new(secret_key, token.encode(), hashlib.sha256).hexdigest()
            # Construct the confirmation URL with the signed token
            confirmation_url = reverse('registration_confirmation', args=[token, signature])
            confirmation_url = request.build_absolute_uri(confirmation_url)
            logger.info(f"{module_name}: User registered: {confirmation_url}")
            send_mail(
                'Register to try Swirl Metasearch Hosted!',
                f'Hello! You have been invited to try Swirl Metasearch! Please click the following link to complete your registration: {confirmation_url}',
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )
            return redirect('registration_confirmation_sent')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})

########################################

def registration_confirmation_sent(request):
    return render(request, 'register_sent.html')

########################################

def registration_confirmation(request, token, signature):
    # Verify the token
    secret_key = settings.SECRET_KEY.encode()
    expected_signature = hmac.new(secret_key, token.encode(), hashlib.sha256).hexdigest()
    if signature != expected_signature:
        raise Http404
    # Decode the token and activate the user
    user_id = int.from_bytes(base64.urlsafe_b64decode(token.encode()), 'big')
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    # Add user to everyone group
    group = Group.objects.get(name='everyone')
    group.user_set.add(user)
    group.save()
    logger.info(f"{module_name}: User confirmed: {user.id} {user.username}")
    login(request, user)
    return redirect('index')

########################################

from .forms import SearchForm

def search(request):

    # user = request.user
    # login(request, user)

    form = SearchForm(request.GET)
    results = []
    query = None
    search_id = 0
    search = None

    page = 1
    if 'page' in request.GET.keys():
        page = int(request.GET['page'])

    mixer = None
    if 'result_mixer' in request.GET.keys():
        mixer = str(request.GET['result_mixer'])

    explain = SWIRL_EXPLAIN
    if 'explain' in request.GET.keys():
        explain = str(request.GET['explain'])
        if explain.lower() == 'false':
            explain = False
        elif explain.lower() == 'true':
            explain = True

    if form.is_valid():
        user = request.user
        query = form.cleaned_data['q']
        # search_id = form.cleaned_data['search_id']
        # if search_id == '':
        #     search_id = 0  # or any other default value
        # else:
        #     search_id = int(search_id)
        # # end if
        ns = False
        if search_id > 0:
            search = Search.objects.get(id=search_id)
        if query:
            if search:
                if query != search.query_string:
                    ns = True
            else:
                ns = True
        # end if
        if ns:
            # new search
            try:
                new_search = Search.objects.create(query_string=query,searchprovider_list=[],owner=user)
            except Error as err:
                logger.error(f'Search.create() failed: {err}')
            new_search.status = 'NEW_SEARCH'
            new_search.save()
            search_id = new_search.id
            res = run_search(search_id, Authenticator().get_session_data(request))
            if not res:
                return Response(f'Search failed: {new_search.status}!!', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            if not Search.objects.filter(id=search_id).exists():
                return Response('Search object creation failed!', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            search = Search.objects.get(id=search_id)

        # form.cleaned_data['search_id'] = search_id

        if search.status.endswith('_READY') or search.status == 'RESCORING':
            try:
                # to do: support mixer spec above
                results = eval(search.result_mixer, {f"{search.result_mixer}": search.result_mixer, "__builtins__": None}, SWIRL_OBJECT_DICT)(search.id, search.results_requested, page, explain).mix()
                results = results['results']
            except (NameError, TypeError) as err:
                message = f'Error: {type(err).__name__}: {err}'
                logger.error(message)
                return Response('An error occurred during the search.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(f'Search error: {search.status}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # end if
    else:
        form = SearchForm()
    # end if

    return render(request, 'search.html', {'form': form, 'results': results, 'query': query})

########################################

class AuthenticatorViewSet(viewsets.ModelViewSet):
    def list(self, request):
        return return_authenticators_list(request)

def authenticators(request):
    if request.method == 'POST':
        authenticator = request.POST.get('authenticator_name')
        res = SWIRL_AUTHENTICATORS_DICT[authenticator]().update_token(request)
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
    
    @csrf_exempt
    def post(self, request):
        print('LOGOUT VIEW')
        token = Token.objects.get(user=request.user)
        if token:
            token.delete()
        return Response({'status': 'OK'})

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
        if self.request.user.is_superuser:
           request.data['shared'] = 'true'

        serializer = SearchProviderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=self.request.user)
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
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
    Add ?rescore=<query_id> to re-run post-result processing, updating relevancy scores
    Add ?update=<query_id> to update the Search with new results from all sources
    """
    queryset = Search.objects.all()
    serializer_class = SearchSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]

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

        query_string = ""
        if 'q' in request.GET.keys():
            query_string = request.GET['q']
        if query_string:
            # check permissions
            if not (request.user.has_perm('swirl.add_search') and request.user.has_perm('swirl.change_search') and request.user.has_perm('swirl.add_result') and request.user.has_perm('swirl.change_result')):
                logger.warning(f"User {self.request.user} needs permissions add_search({request.user.has_perm('swirl.add_search')}), change_search({request.user.has_perm('swirl.change_search')}), add_result({request.user.has_perm('swirl.add_result')}), change_result({request.user.has_perm('swirl.change_result')})")
                return Response(status=status.HTTP_403_FORBIDDEN)
            # run search
            logger.info(f"{module_name}: Search.create() from ?q")
            try:
                new_search = Search.objects.create(query_string=query_string,searchprovider_list=providers,owner=self.request.user)
            except Error as err:
                self.error(f'Search.create() failed: {err}')
            new_search.status = 'NEW_SEARCH'
            new_search.save()
            search_task.delay(new_search.id, Authenticator().get_session_data(request))
            time.sleep(SWIRL_Q_WAIT)
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
            logger.info(f"{module_name}: Search.create() from ?qs")
            try:
                # security review for 1.7 - OK, created with owner
                new_search = Search.objects.create(query_string=query_string,searchprovider_list=providers,owner=self.request.user,
                                                   pre_query_processors=pre_query_processor_single_list)
            except Error as err:
                self.error(f'Search.create() failed: {err}')
            new_search.status = 'NEW_SEARCH'
            new_search.save()
            res = run_search(new_search.id, Authenticator().get_session_data(request))
            if not res:
                return Response(f'Search failed: {new_search.status}!!', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            if not Search.objects.filter(id=new_search.id).exists():
                return Response('Search object creation failed!', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # security review for 1.7 - OK, search id created
            search = Search.objects.get(id=new_search.id)
            if search.status.endswith('_READY') or search.status == 'RESCORING':
                try:
                    if otf_result_mixer:
                        # call the specifixed mixer on the fly otf
                        results = eval(otf_result_mixer, {"otf_result_mixer": otf_result_mixer, "__builtins__": None}, SWIRL_OBJECT_DICT)(search.id, search.results_requested, 1, explain, provider).mix()
                    else:
                        # call the mixer for this search provider
                        results = eval(search.result_mixer, {f"{search.result_mixer}": search.result_mixer, "__builtins__": None}, SWIRL_OBJECT_DICT)(search.id, search.results_requested, 1, explain, provider).mix()
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
                tries = tries + 1
                if tries > SWIRL_RERUN_WAIT:
                    return Response(f'Timeout: {tries}, {new_search.status}!!', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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
            logger.info(f"{module_name}: ?rerun!")
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
            search_task.delay(rerun_search.id, Authenticator().get_session_data(request))
            time.sleep(SWIRL_RERUN_WAIT)
            return redirect(f'/swirl/results?search_id={rerun_search.id}')
        # end if

        ########################################

        rescore_id = 0
        if 'rescore' in request.GET.keys():
            rescore_id = request.GET['rescore']

        if rescore_id:
            # check permissions
            if not (request.user.has_perm('swirl.change_search') and request.user.has_perm('swirl.change_result')):
                logger.warning(f"User {self.request.user} needs permissions change_search({request.user.has_perm('swirl.change_search')}), change_result({request.user.has_perm('swirl.change_result')})")
                return Response(status=status.HTTP_403_FORBIDDEN)
            # security check
            if not Search.objects.filter(id=rescore_id, owner=self.request.user).exists():
                return Response('Result Object Not Found', status=status.HTTP_404_NOT_FOUND)
            logger.info(f"{module_name}: ?rescore!")
            rescore_task.delay(rescore_id)
            time.sleep(SWIRL_RESCORE_WAIT)
            return redirect(f'/swirl/results?search_id={rescore_id}')

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
            logger.info(f"{module_name}: ?update!")
            search.status = 'UPDATE_SEARCH'
            search.save()
            search_task.delay(update_id, Authenticator().get_session_data(request))
            time.sleep(SWIRL_SUBSCRIBE_WAIT)
            return redirect(f'/swirl/results?search_id={update_id}')

        ########################################

        logger.info(f"{module_name}: Search.list()!")

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

        logger.info(f"{module_name}: Search.create() from POST")

        serializer = SearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # security review for 1.7 - OK, create with owner
        serializer.save(owner=self.request.user)

        if not (self.request.user.has_perm('swirl.view_searchprovider')):
            # TO DO: SECURITY REVIEW
            if Search.objects.filter(id=serializer.data['id'], owner=self.request.user).exists():
                search = Search.objects.get(id=serializer.data['id'])
                search.status = 'ERR_NO_SEARCHPROVIDERS'
                search.save
        else:
            search_task.delay(serializer.data['id'], Authenticator().get_session_data(request))

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

        logger.info(f"{module_name}: Search.update()!")

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
            search_task.delay(search.id, Authenticator().get_session_data(request))
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    ########################################

    def destroy(self, request, pk=None):

        # check permissions
        if not request.user.has_perm('swirl.delete_search'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # security review for 1.7 - OK, filtered by owner
        if not Search.objects.filter(pk=pk, owner=self.request.user).exists():
            return Response('Search Object Not Found', status=status.HTTP_404_NOT_FOUND)

        logger.info(f"{module_name}: Search.destroy()!")

        search = Search.objects.get(pk=pk)
        search.delete()
        return Response('Search Object Deleted', status=status.HTTP_410_GONE)

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
            logger.info(f"{module_name}: Calling mixer from ?search_id")
            search = Search.objects.get(id=search_id)
            if search.status.endswith('_READY') or search.status == 'RESCORING':
                try:
                    if otf_result_mixer:
                        # call the specifixed mixer on the fly otf
                        results = eval(otf_result_mixer, {"otf_result_mixer": otf_result_mixer, "__builtins__": None}, SWIRL_OBJECT_DICT)(search.id, search.results_requested, page, explain, provider, mark_all_read).mix()
                    else:
                        # call the mixer for this search provider
                        results = eval(search.result_mixer, {"otf_result_mixer": otf_result_mixer, "__builtins__": None}, SWIRL_OBJECT_DICT)(search.id, search.results_requested, page, explain, provider, mark_all_read).mix()
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

        logger.info(f"{module_name}: Result.update()!")

        result = Result.objects.get(pk=pk)
        result.date_updated = datetime.now()
        serializer = ResultSerializer(instance=result, data=request.data)
        serializer.is_valid(raise_exception=True)
        # security review for 1.7 - OK, saved with owner
        serializer.save(owner=self.request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    ########################################

    def destroy(self, request, pk=None):

        # check permissions
        if not request.user.has_perm('swirl.delete_result'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # security review for 1.7 - OK, filtered by owner
        if not Result.objects.filter(pk=pk, owner=self.request.user).exists():
            return Response('Result Object Not Found', status=status.HTTP_404_NOT_FOUND)

        logger.info(f"{module_name}: Result.destroy()!")

        result = Result.objects.get(pk=pk)
        result.delete()
        return Response('Result Object Deleted!', status=status.HTTP_410_GONE)

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
            serializer = QueryTrasnformNoCredentialsSerializer(query_xfr)
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
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
        return Response('QueryTranformation Object Deleted', status=status.HTTP_410_GONE)

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
