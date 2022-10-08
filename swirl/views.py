'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

import time
import logging as logger
from datetime import datetime
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.models import User, Group
from django.http import Http404, HttpResponse
from django.conf import settings

from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework import viewsets, status
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import *
from .serializers import *
from swirl.models import SearchProvider, Search, Result
from swirl.serializers import UserSerializer, GroupSerializer, SearchProviderSerializer, SearchSerializer, ResultSerializer
from swirl.mixers import *

module_name = 'views.py'

from .tasks import search_task, rescore_task

########################################
########################################

def index(request):
    context = {'index': []}
    return render(request, 'index.html', context)

########################################
########################################

class SearchProviderViewSet(viewsets.ModelViewSet):
    """
    ##S#W#I#R#L##1#.#3##############################################################
    API endpoint for managing SearchProviders. 
    Use GET to list all, POST to create a new one. 
    Add /<id>/ to DELETE, PUT or PATCH.
    """
    queryset = SearchProvider.objects.all()
    serializer_class = SearchProviderSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    # TO DO: figure out if we keep this or not P1
    pagination_class = None 

########################################
########################################

class SearchViewSet(viewsets.ModelViewSet):
    """
    ##S#W#I#R#L##1#.#3##############################################################
    API endpoint for managing Search objects. 
    Use GET to list all, POST to create a new one. 
    Add /<id>/ to DELETE, PUT or PATCH.
    Add ?q=<query_string> to the URL to create a Search with default settings
    Add ?rerun=<query_id> to fully re-execute a query, discarding previous results
    Add ?rescore=<query_id> to re-run post-result processing, updating relevancy scores
    """
    queryset = Search.objects.all()
    serializer_class = SearchSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    ########################################
    def list(self, request):
        ########################################
        # handle ?q=
        query_string = ""
        if 'q' in request.GET.keys():
            query_string = request.GET['q']
        if query_string:
            new_search = Search.objects.create(query_string=query_string)
            new_search.status = 'NEW_SEARCH'
            new_search.save()
            search_task.delay(new_search.id)
            time.sleep(settings.SWIRL_Q_WAIT)
            return redirect(f'/swirl/results?search_id={new_search.id}')
        # end if
        ########################################
        # handle ?rerun=
        rerun_id = 0
        if 'rerun' in request.GET.keys():
            rerun_id = int(request.GET['rerun'])
        if rerun_id:
            rerun_search = Search.objects.get(id=rerun_id)
            old_results = Result.objects.filter(search_id=rerun_search.id)
            # to do: instead of deleting, copy the search copy to a new search? 
            logger.warning(f"{module_name}: deleting Result objects associated with search {rerun_id}")
            for old_result in old_results:
                old_result.delete()
            rerun_search.status = 'NEW_SEARCH'
            rerun_search.save()
            search_task.delay(rerun_search.id)
            time.sleep(settings.SWIRL_RERUN_WAIT)
            return redirect(f'/swirl/results?search_id={rerun_search.id}')
        # end if        
        ########################################
        # handle ?rescore=
        rescore_id = 0
        if 'rescore' in request.GET.keys():
            rescore_id = request.GET['rescore']
        if rescore_id:
            # to do to do
            rescore_task.delay(rescore_id)
            time.sleep(settings.SWIRL_RESCORE_WAIT)
            return redirect(f'/swirl/results?search_id={rescore_id}')
        # end if
        self.queryset = Search.objects.all()
        serializer = SearchSerializer(self.queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    ########################################
    def create(self, request):
        serializer = SearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        search_task.delay(serializer.data['id'])
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    ########################################
    def retrieve(self, request, pk=None):
        if Search.objects.filter(pk=pk).exists():
            search = Search.objects.get(pk=pk)
            serializer = SearchSerializer(search)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response('Search Object Not Found', status=status.HTTP_404_NOT_FOUND)
        # end if

    ########################################
    def update(self, request, pk=None):
        if Search.objects.filter(pk=pk).exists():
            search = Search.objects.get(pk=pk)
            search.date_updated = datetime.now()
            serializer = SearchSerializer(instance=search, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            # re-start queries if status appropriate
            if search.status == 'NEW_SEARCH':
                search_task.delay(search.id)
                # publish('search_create', serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response('Search Object Not Found', status=status.HTTP_404_NOT_FOUND)

    ########################################
    def destroy(self, request, pk=None):
        if Search.objects.filter(pk=pk).exists():
            search = Search.objects.get(pk=pk)
            search.delete()
            return Response('Search Object Deleted', status=status.HTTP_410_GONE)
        else:
            return Response('Search Object Not Found', status=status.HTTP_404_NOT_FOUND)

########################################
########################################

class ResultViewSet(viewsets.ModelViewSet):
    """
    ##S#W#I#R#L##1#.#3##############################################################
    API endpoint for managing Result objects, including Mixed Results
    Use GET to list all, POST to create a new one. 
    Add /<id>/ to DELETE, PUT or PATCH.
    Add ?search_id=<search_id> to the base URL to view mixed results with the default mixer
    Add &result_mixer=<MixerName> to the above URL specify the result mixer to use
    Add &explain=True to display the relevancy explanation for each result
    Add &provider=<provider_id> to filter results to one SearchProvider
    """
    queryset = Result.objects.all()
    serializer_class = ResultSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    ########################################
    def list(self, request):

        # handle search_id, page, and optionally result_mixer
        search_id = 0
        if 'search_id' in request.GET.keys():
            search_id = int(request.GET['search_id'])
        # end if
        page = 1
        if 'page' in request.GET.keys():
            page = int(request.GET['page'])
        # end if
        otf_result_mixer = None
        if 'result_mixer' in request.GET.keys():
            otf_result_mixer = str(request.GET['result_mixer'])
        # end if        
        explain = settings.SWIRL_EXPLAIN
        if 'explain' in request.GET.keys():
            explain = str(request.GET['explain'])
            if explain.lower() == 'false':
                explain = False
            elif explain.lower() == 'true':
                explain = True
        # end if
        provider = None
        if 'provider' in request.GET.keys():
            provider = int(request.GET['provider'])
        # end if
        if search_id:
            # check if the query has ready status
            if Search.objects.filter(id=search_id).exists():
                search = Search.objects.get(id=search_id)
                if search.status.endswith('_READY'):
                    try:
                        if otf_result_mixer:
                            # call the specifixed mixer on the fly otf
                            results = eval(otf_result_mixer)(search.id, search.results_requested, page, explain, provider).mix()
                        else:
                            # call the mixer for this search provider
                            results = eval(search.result_mixer)(search.id, search.results_requested, page, explain, provider).mix()
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
                # invalid search_id
                return Response('Result Object Not Found', status=status.HTTP_404_NOT_FOUND)
            # end if
        ########################################
        else:
            # results = reversed(Result.objects.all())
            serializer = ResultSerializer(self.queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        # end if

    ########################################
    def retrieve(self, request, pk=None):
        if Result.objects.filter(pk=pk).exists():
            result = Result.objects.get(pk=pk)
            serializer = ResultSerializer(result)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response('Result Object Not Found', status=status.HTTP_404_NOT_FOUND)
        # end if

    ########################################
    def destroy(self, request, pk=None):
        if Result.objects.filter(pk=pk).exists():
            result = Result.objects.get(pk=pk)
            result.delete()
            return Response('Result Object Deleted!', status=status.HTTP_410_GONE)
        else:
            return Response('Result Object Not Found', status=status.HTTP_404_NOT_FOUND)

########################################
########################################

class UserViewSet(viewsets.ModelViewSet):
    """
    ##S#W#I#R#L##1#.#3##############################################################
    API endpoint that allows management of Users objects.
    Use GET to list all objects, POST to create a new one. 
    Add /<id>/ to DELETE, PUT or PATCH objects.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

########################################
########################################

class GroupViewSet(viewsets.ModelViewSet):
    """
    ##S#W#I#R#L##1#.#3##############################################################
    API endpoint that allows management of Group objects.
    Use GET to list all objects, POST to create a new one. 
    Add /<id>/ to DELETE, PUT or PATCH objects.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]
