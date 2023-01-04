'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import time
import logging as logger
from datetime import datetime

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.models import User, Group
from django.http import Http404, HttpResponse, HttpRequest
from django.conf import settings
from django.db import Error
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework import viewsets, status
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView

from swirl.models import *
from swirl.serializers import *
from swirl.models import SearchProvider, Search, Result
from swirl.serializers import UserSerializer, GroupSerializer, SearchProviderSerializer, SearchSerializer, ResultSerializer
from swirl.mixers import *

module_name = 'views.py'

from swirl.tasks import search_task, rescore_task
from swirl.search import search as execute_search

SWIRL_OBJECT_LIST = Search.MIXER_CHOICES

SWIRL_OBJECT_DICT = {}
for t in SWIRL_OBJECT_LIST:
    SWIRL_OBJECT_DICT[t[0]]=eval(t[0])

########################################

def index(request):
    context = {'index': []}
    return render(request, 'index.html', context)

########################################
########################################

class SearchProviderViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing SearchProviders. 
    Use GET to list all, POST to create a new one. 
    Add /<id>/ to DELETE, PUT or PATCH one.
    """
    queryset = SearchProvider.objects.all()
    serializer_class = SearchProviderSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    pagination_class = None 

    def list(self, request):

        # check permissions
        if not request.user.has_perm('swirl.view_searchprovider'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        self.queryset = SearchProvider.objects.filter(owner=self.request.user) | SearchProvider.objects.filter(shared=True) 

        serializer = SearchProviderSerializer(self.queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

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
    Add ?rerun=<query_id> to fully re-execute a query, discarding previous results
    Add ?rescore=<query_id> to re-run post-result processing, updating relevancy scores
    """
    queryset = Search.objects.all()
    serializer_class = SearchSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]

    def list(self, request):

        # check permissions
        if not request.user.has_perm('swirl.view_search'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        ########################################

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
            try:
                new_search = Search.objects.create(query_string=query_string,searchprovider_list=providers,owner=self.request.user)
            except Error as err:
                self.error(f'Search.create() failed: {err}')
            new_search.status = 'NEW_SEARCH'
            new_search.save()
            search_task.delay(new_search.id)
            time.sleep(settings.SWIRL_Q_WAIT)
            return redirect(f'/swirl/results?search_id={new_search.id}')

        ########################################

        otf_result_mixer = None
        if 'result_mixer' in request.GET.keys():
            otf_result_mixer = str(request.GET['result_mixer'])

        explain = settings.SWIRL_EXPLAIN
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
            try:
                # security review for 1.7 - OK, created with owner
                new_search = Search.objects.create(query_string=query_string,searchprovider_list=providers,owner=self.request.user)
            except Error as err:
                self.error(f'Search.create() failed: {err}')            
            new_search.status = 'NEW_SEARCH'
            new_search.save()
            res = execute_search(new_search.id)
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
                        results = eval(search.result_mixer)(search.id, search.results_requested, 1, explain, provider).mix()
                except NameError as err:
                    message = f'Error: NameError: {err}'
                    logger.error(f'{module_name}: {message}')
                    return
                except TypeError as err:
                    message = f'Error: TypeError: {err}'
                    logger.error(f'{module_name}: {message}')
                    return
                return Response(results, status=status.HTTP_200_OK)
            else:
                tries = tries + 1
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
            rerun_search = Search.objects.get(id=rerun_id)
            old_results = Result.objects.filter(search_id=rerun_search.id)
            logger.warning(f"{module_name}: deleting Result objects associated with search {rerun_id}")
            for old_result in old_results:
                old_result.delete()
            rerun_search.status = 'NEW_SEARCH'
            # fix for https://github.com/sidprobstein/swirl-search/issues/35
            message = f"[{datetime.now()}] Rerun requested"
            rerun_search.messages = []
            rerun_search.messages.append(message)    
            rerun_search.save()
            search_task.delay(rerun_search.id)
            time.sleep(settings.SWIRL_RERUN_WAIT)
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
            rescore_task.delay(rescore_id)
            time.sleep(settings.SWIRL_RESCORE_WAIT)
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
            search.status = 'UPDATE_SEARCH'
            search.save()
            search_task.delay(update_id)
            time.sleep(settings.SWIRL_SUBSCRIBE_WAIT)
            return redirect(f'/swirl/results?search_id={update_id}')

        ########################################

        # security review for 1.7 - OK, filtered by owner
        self.queryset = Search.objects.filter(owner=self.request.user)
        serializer = SearchSerializer(self.queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    ########################################

    def create(self, request):

        # check permissions
        if not (request.user.has_perm('swirl.add_search') and request.user.has_perm('swirl.change_search') and request.user.has_perm('swirl.add_result') and request.user.has_perm('swirl.change_result')):
            logger.warning(f"User {self.request.user} needs permissions add_search({request.user.has_perm('swirl.add_search')}), change_search({request.user.has_perm('swirl.change_search')}), add_result({request.user.has_perm('swirl.add_result')}), change_result({request.user.has_perm('swirl.change_result')})")
            return Response(status=status.HTTP_403_FORBIDDEN)
            
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
            search_task.delay(serializer.data['id'])

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
            search_task.delay(search.id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    ########################################
        
    def destroy(self, request, pk=None):

        # check permissions
        if not request.user.has_perm('swirl.delete_search'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # security review for 1.7 - OK, filtered by owner
        if not Search.objects.filter(pk=pk, owner=self.request.user).exists():
            return Response('Search Object Not Found', status=status.HTTP_404_NOT_FOUND)

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
    Add &explain=True to display the relevancy explanation for each result
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

        explain = settings.SWIRL_EXPLAIN
        if 'explain' in request.GET.keys():
            explain = str(request.GET['explain'])
            if explain.lower() == 'false':
                explain = False
            elif explain.lower() == 'true':
                explain = True

        provider = None
        if 'provider' in request.GET.keys():
            provider = int(request.GET['provider'])

        if search_id:
            # security review for 1.7 - OK, filtered by owner
            if not Search.objects.filter(id=search_id, owner=self.request.user).exists():
                return Response('Result Object Not Found', status=status.HTTP_404_NOT_FOUND)
            # security review for 1.7 - OK, filtered by owner
            search = Search.objects.get(id=search_id)
            if search.status.endswith('_READY') or search.status == 'RESCORING':
                try:
                    if otf_result_mixer:
                        # call the specifixed mixer on the fly otf
                        results = eval(otf_result_mixer, {"otf_result_mixer": otf_result_mixer, "__builtins__": None}, SWIRL_OBJECT_DICT)(search.id, search.results_requested, page, explain, provider).mix()
                    else:
                        # call the mixer for this search provider
                        results = eval(search.result_mixer, {"otf_result_mixer": otf_result_mixer, "__builtins__": None}, SWIRL_OBJECT_DICT)(search.id, search.results_requested, page, explain, provider).mix()
                except NameError as err:
                    message = f'Error: NameError: {err}'
                    logger.error(f'{module_name}: {message}')
                    return
                except TypeError as err:
                    message = f'Error: TypeError: {err}'
                    logger.error(f'{module_name}: {message}')
                    return
                return Response(results, status=status.HTTP_200_OK)
            else:
                return Response('Result Object Not Ready Yet', status=status.HTTP_503_SERVICE_UNAVAILABLE)
            # end if
        else:
            # security review for 1.7 - OK, filtered by owner
            self.queryset = Result.objects.filter(owner=self.request.user)
            serializer = ResultSerializer(self.queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
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
 