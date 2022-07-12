'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

from django.core.exceptions import ObjectDoesNotExist
import time 
from datetime import datetime

import logging as logger

from swirl.models import Search, SearchProvider, Result
from swirl.tasks import federate_task
from swirl.processors import *

##################################################
##################################################

from django.conf import settings

module_name = 'search.py'

def search(id):
    
    try:
        search = Search.objects.get(id=id)
    except ObjectDoesNotExist as err:
        logger.error(f'{module_name}: Error: ObjectDoesNotExist: {err}')
        return False
    if search.status != 'NEW_SEARCH':
        logger.warning(f"{module_name}: search {search.id} has status {search.status}; set it to NEW_SEARCH to restart it")
        return False
    search.status = 'PRE_PROCESSING'
    # search.date_updated = datetime.now()
    search.save()
    # providers = SearchProvider.objects.all()   
    # providers should always include only active SearchProviders 
    providers = SearchProvider.objects.filter(active=True)
    if len(providers) == 0:
        logger.error(f"{module_name}: error: no SearchProviders configured")
        search.status = 'ERR_NO_SEARCHPROVIDERS'
        search.date_updated = datetime.now()
        search.save()
        return False
    ########################################
    # check for provider specification
    new_provider_list = []
    if search.searchprovider_list:
        for provider in providers:
            if provider.id in search.searchprovider_list:
                new_provider_list.append(provider)
            # end if
        # end for
        providers = new_provider_list
    # end if

    ########################################
    # pre_search_processing
    if search.pre_query_processor:
        search.status = 'PRE_QUERY_PROCESSING'
        search.save()
        try:
            search.query_string_processed = eval(search.pre_query_processor)(search.query_string)
        except NameError as err:
            message = f'Error: NameError: {err}'
            logger.error(f'{module_name}: {message}')
            return False
        except TypeError as err:
            message = f'Error: TypeError: {err}'
            logger.error(f'{module_name}: {message}')
            return False
        if search.query_string_processed != search.query_string:
            message = f"Pre-query processing by {search.pre_query_processor} rewrote query_string to: {search.query_string_processed}"
            messages = search.messages
            messages.append(message)
            search.messages = messages
    else:
        search.query_string_processed = search.query_string
    # end if
    
    # to do: use chord()
    ########################################
    search.status = 'FEDERATING'
    search.save()        
    federation_result = {}
    federation_status = {}
    at_least_one = False
    for provider in providers:
        at_least_one = True
        federation_status[provider.id] = None
        logger.debug(f"{module_name}: federate: {provider.id}, {provider.name}, {provider.connector}, {search.id}")
        federation_result[provider.id] = federate_task.delay(provider.id, provider.name, provider.connector, search.id)
    # end for
    if not at_least_one:
        logger.warning(f"{module_name}: no active searchprovider specified: {search.searchprovider_list}")
        search.status = 'ERR_NO_ACTIVE_SEARCHPROVIDERS'
        search.save()
        return False
    # end if
    ########################################
    # asynchronously collect results
    time.sleep(5)
    ticks = 0
    error_flag = False
    at_least_one = False
    while 1:        
        logger.debug(f"{module_name}: tick!")
        # get the list of result objects
        results = Result.objects.filter(search_id=search.id)
        if len(results) == len(providers):
            # every provider has written a result object - exit
            logger.warning(f"{module_name}: all results received, search {search.id}")
            break
        if len(results) > 0:
            at_least_one = True
        ticks = ticks + 1
        search.status = f'FEDERATING_WAIT_{ticks}'
        search.save()    
        time.sleep(1)
        if ticks > 10:
            logger.warning(f"{module_name}: timeout, search {search.id}")
            failed_providers = []
            responding_provider_names = []
            for result in results:
                responding_provider_names.append(result.searchprovider)
            # fixed: don't report in-active providers as failed (above by filtering providers to active=True)
            for provider in providers:
                if not provider.name in responding_provider_names:
                    failed_providers.append(provider.name)
                    error_flag = True
                    logger.warning(f"{module_name}: timeout waiting for: {failed_providers}")
                    message = f"{module_name}: No response from provider: {failed_providers}"
                    messages = search.messages
                    messages.append(message)
                    search.messages = messages
                    search.save()
                # end if
            # end for
            # exit the loop
            break
    # end while
    ########################################
    # update query status
    logger.debug(f"{module_name}: exiting...")
    if error_flag:
        if at_least_one:
            search.status = 'PARTIAL_RESULTS'
        else:
            search.status = 'NO_RESULTS'
        # end if
    else:
        search.status = 'FULL_RESULTS'
    ########################################
    # fix the result url
    # to do: figure out a better solution P1
    search.result_url = f"http://{settings.ALLOWED_HOSTS[0]}:8000/swirl/results?search_id={search.id}&result_mixer={search.result_mixer}"
    # note the sort
    if search.sort.lower() == 'date':
        message = f"Requested sort_by_date from all providers"
        messages = search.messages
        messages.append(message)
        search.messages = messages        
    search.save()
    logger.debug(f"{module_name}: landed data!")
    ########################################
    # post_result_processing
    if search.post_result_processor:
        last_status = search.status
        search.status = 'POST_RESULT_PROCESSING'
        search.save()
        results_modified = eval(search.post_result_processor)(search.id)
        message = f"Post processing of results by {search.post_result_processor} updated {results_modified} results"
        messages = search.messages
        messages.append(message)
        search.messages = messages        
        search.status = last_status
    if search.status == 'PARTIAL_RESULTS':
        search.status = 'PARTIAL_RESULTS_READY'
    if search.status == 'FULL_RESULTS':
        search.status = 'FULL_RESULTS_READY'
    search.save()
    logger.debug(f"{module_name}: {search.id}, {search.status}")

    ########################################

    return True

##################################################
##################################################

def rescore(id):

    try:
        search = Search.objects.get(id=id)
        results = Result.objects.filter(search_id=search.id)
    except ObjectDoesNotExist as err:
        logger.error(f'{module_name}: Error: ObjectDoesNotExist: {err}')
        return False
        
    last_status = search.status
    if not search.status.endswith('_READY'):
        logger.warning(f"{module_name}: search {search.id} has status {search.status}, rescore may not work")
        last_status = None

    if len(results) == 0:
        logger.error(f"{module_name}: search {search.id} has no results to rescore")
        return False
    search.status = 'RESCORING'
    search.save()
    if search.post_result_processor:
        results_modified = eval(search.post_result_processor)(search.id)
        # message = f"Post processing of results by {search.post_result_processor} updated {results_modified} results"
        # messages = search.messages
        # messages.append(message)
        # search.messages = messages    
        logger.info(f"{module_name}: rescoring {search.id} by {search.post_result_processor} updated {results_modified} results")   
        search.status = last_status
        search.save()
        return True
    else:
        logger.error(f"{module_name}: search {search.id} has no post_result_processor defined")
        return False
