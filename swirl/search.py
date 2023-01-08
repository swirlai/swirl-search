'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from datetime import datetime
import time

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.models import Search, SearchProvider, Result
from swirl.tasks import federate_task
from swirl.processors import *

SWIRL_OBJECT_LIST = SearchProvider.QUERY_PROCESSOR_CHOICES + SearchProvider.RESULT_PROCESSOR_CHOICES + Search.PRE_QUERY_PROCESSOR_CHOICES + Search.POST_RESULT_PROCESSOR_CHOICES

SWIRL_OBJECT_DICT = {}
for t in SWIRL_OBJECT_LIST:
    SWIRL_OBJECT_DICT[t[0]]=eval(t[0])

##################################################
##################################################

module_name = 'search.py'

def search(id):

    '''
    Execute the search task workflow
    '''
    
    update = False
    start_time = time.time()

    try:
        search = Search.objects.get(id=id)
    except ObjectDoesNotExist as err:
        logger.error(f'{module_name}_{id}: ObjectDoesNotExist: {err}')
        return False
    if not search.status.upper() in ['NEW_SEARCH', 'UPDATE_SEARCH']:
        logger.warning(f"{module_name}_{search.id}: unexpected status {search.status}")
        return False
    if search.status.upper() == 'UPDATE_SEARCH':
        logger.info(f"{module_name}: {search.id}.status == UPDATE_SEARCH")
        update = True
        search.sort = 'date'

    search.status = 'PRE_PROCESSING'
    logger.info(f"{module_name}: {search.status}")
    search.save()
    # check for provider specification
    # to do: add provider if tagged in query, e.g. electric vehicle company:tesla
    # identify tags in the query
    raw_tags_in_query_list = [tag for tag in search.query_string.strip().split() if ':' in tag]
    tags_in_query_list = []
    for tag in raw_tags_in_query_list:
        if tag.endswith(':'):
            tags_in_query_list.append(tag[:-1])
        else:
            tags_in_query_list.append(tag[:tag.find(':')])
    logger.debug(f"{module_name}: tags_in_query_list: {tags_in_query_list}")
    providers = SearchProvider.objects.filter(active=True, owner=search.owner) | SearchProvider.objects.filter(active=True, shared=True)
    new_provider_list = []
    if search.searchprovider_list:            
        # add providers to list by id, name or tag
        for provider in providers:
            provider_key = None
            if type(search.searchprovider_list[0]) == str:
                provider_key = str(provider.id)
            else:
                provider_key = provider.id
            if provider_key in search.searchprovider_list:
                new_provider_list.append(provider)
                continue
            if provider.name.lower() in [str(p).lower() for p in search.searchprovider_list]:
                if not provider in new_provider_list:
                    new_provider_list.append(provider)
                    continue
            if provider.tags:
                for tag in provider.tags:
                    if tag.lower() in [t.lower() for t in tags_in_query_list]:
                        if not provider in new_provider_list:
                            new_provider_list.append(provider)
                            continue
                    if tag.lower() in [p.lower() for p in search.searchprovider_list]:
                        if not provider in new_provider_list:
                            new_provider_list.append(provider)
                # end if
            # end for
        # end for
    else:
        # no provider list
        for provider in providers:
            # active status is determined later on
            if provider.default:
                new_provider_list.append(provider)
            else:
                if provider.tags:
                    for tag in provider.tags:
                        if tag.lower() in [t.lower() for t in tags_in_query_list]: 
                            if not provider in new_provider_list:
                                new_provider_list.append(provider)
        # end for
    # end if
    providers = new_provider_list
    if len(providers) == 0:
        logger.error(f"{module_name}_{search.id}: no SearchProviders configured")
        search.status = 'ERR_NO_SEARCHPROVIDERS'
        search.save()
        return False

    ########################################
    # pre-query processing, which updates query_string_processed
    if search.pre_query_processor or search.pre_query_processors:
        search.status = 'PRE_QUERY_PROCESSING'
        logger.info(f"{module_name}: {search.status}")
        search.save()
        # setup processor pipeline
        processor_list = []
        if search.pre_query_processor:
            processor_list = [search.pre_query_processor]
            if search.pre_query_processors:
                logger.warning(f"{module_name}_{search.id}: Ignoring search.pre_query_processors, since search.pre_query_processor is specified")
        else:
            processor_list = search.pre_query_processors
        # end if
        for processor in processor_list:
            try:
                pre_query_processor = eval(processor, {"processor": processor, "__builtins__": None}, SWIRL_OBJECT_DICT)(search.query_string)
                if pre_query_processor.validate():
                    search.query_string_processed = pre_query_processor.process()
                else:
                    logger.error(f'{module_name}_{search.id}: {processor}.validate() failed')
                    return False
                # end if
            except (NameError, TypeError, ValueError) as err:
                logger.error(f'{module_name}_{search.id}: {processor}: {err.args}, {err}')
                return False
            if search.query_string_processed != search.query_string:
                search.messages.append(f"[{datetime.now()}] {processor} rewrote query to: {search.query_string_processed}")
                search.save()
            # end if
        # end for
    else:
        search.query_string_processed = search.query_string
    # end if
    
    ########################################
    search.status = 'FEDERATING'
    logger.info(f"{module_name}: {search.status}")
    search.save()        
    federation_result = {}
    federation_status = {}
    at_least_one = False
    for provider in providers:
        at_least_one = True
        federation_status[provider.id] = None
        federation_result[provider.id] = federate_task.delay(search.id, provider.id, provider.connector, update)
    # end for
    if not at_least_one:
        logger.warning(f"{module_name}_{search.id}: no active searchprovider specified: {search.searchprovider_list}")
        search.status = 'ERR_NO_ACTIVE_SEARCHPROVIDERS'
        search.save()
        return False
    # end if
    ########################################
    # asynchronously collect results
    time.sleep(2)
    ticks = 0
    error_flag = False
    at_least_one = False
    while 1:        
        updated = 0
        # get the list of result objects
        # security review for 1.7 - OK - filtered by search object
        results = Result.objects.filter(search_id=search.id)
        if len(results) == len(providers):
            if update:
                for result in results:
                    if result.status == 'UPDATED':
                        updated = updated + 1
                if updated == len(providers):
                    # every provider has updated a result object - exit
                    logger.info(f"{module_name}_{search.id}: all results updated!")
                    break
            else:
                # every provider has written a result object - exit
                logger.info(f"{module_name}_{search.id}: all results received!")
                break
        if len(results) > 0:
            if update:
                if updated > 0:
                    at_least_one = True
            else:
                at_least_one = True
        ticks = ticks + 1
        search.status = f'FEDERATING_WAIT_{ticks}'
        logger.info(f"{module_name}: {search.status}")
        search.save()    
        time.sleep(1)
        if (ticks + 2) > int(settings.SWIRL_TIMEOUT):
            logger.info(f"{module_name}_{search.id}: timeout!")
            failed_providers = []
            responding_provider_names = []
            for result in results:
                responding_provider_names.append(result.searchprovider)
            for provider in providers:
                if not provider.name in responding_provider_names:
                    failed_providers.append(provider.name)
                    error_flag = True
                    logger.warning(f"{module_name}_{search.id}: timeout waiting for: {failed_providers}")
                    search.messages.append(f"[{datetime.now()}] Timeout waiting for: {failed_providers}")
                    search.save()
                # end if
            # end for
            # exit the loop
            break
    # end while
    ########################################
    # update query status
    if error_flag:
        if at_least_one:
            search.status = 'PARTIAL_RESULTS'
        else:
            search.status = 'NO_RESULTS'
        # end if
    else:
        search.status = 'FULL_RESULTS'
    logger.info(f"{module_name}: {search.status}")
    ########################################
    # fix the result url
    # to do: figure out a better solution P1
    search.result_url = f"{settings.PROTOCOL}://{settings.HOSTNAME}:8000/swirl/results?search_id={search.id}&result_mixer={search.result_mixer}"
    search.new_result_url = f"{search.result_url}&new=true"
    # note the sort
    if search.sort.lower() == 'date':
        if not update:
            search.messages.append(f"[{datetime.now()}] Requested sort_by_date from all providers")
    search.save()
    ########################################
    # post_result_processing
    if search.post_result_processor or search.post_result_processors:
        last_status = search.status
        search.status = 'POST_RESULT_PROCESSING'
        logger.info(f"{module_name}: {search.status}")
        search.save()
        # setup processor pipeline
        processor_list = []
        if search.post_result_processor:
            processor_list = [search.post_result_processor]
            if search.post_result_processors:
                logger.warning(f"{module_name}_{search.id}: Ignoring search.post_result_processors, since search.post_result_processor is specified")
        else:
            processor_list = search.post_result_processors
        # end if
        for processor in processor_list:
            logger.info(f"{module_name}: invoking processor: {processor}")
            try:
                post_result_processor = eval(processor, {"processor": processor, "__builtins__": None}, SWIRL_OBJECT_DICT)(search.id)
                if post_result_processor.validate():
                    results_modified = post_result_processor.process()
                else:
                    logger.error(f"{module_name}_{search.id}: {processor}.validate() failed")
                    return False
                # end if
            except (NameError, TypeError, ValueError) as err:
                logger.error(f'{module_name}_{search.id}: {processor}: {err.args}, {err}')
                return False
            if results_modified > 0:
                message = f"[{datetime.now()}] {processor} updated {results_modified} results"
                # don't repeat the same message - to do: test
                last_message = search.messages[-1:]
                if last_message:
                    if last_message[0].lower().strip() != message.lower().strip():
                        search.messages.append(message)   
                    # end if
                else:
                    search.messages.append(message)   
                # end if
            # end if
        # end for
        search.status = last_status
    if search.status == 'PARTIAL_RESULTS':
        if update:
            search.status = 'PARTIAL_UPDATE_READY'
        else:
            search.status = 'PARTIAL_RESULTS_READY'
    if search.status == 'FULL_RESULTS':
        if update:
            search.status = 'FULL_UPDATE_READY'
        else:
            search.status = 'FULL_RESULTS_READY'
    logger.info(f"{module_name}: {search.status}")
    end_time = time.time()
    search.time = f"{(end_time - start_time):.1f}"
    logger.info(f"{module_name}: search time: {search.time}")
    search.save()    

    return True

##################################################

def rescore(id):

    '''
    Execute the rescore task workflow
    '''

    try:
        search = Search.objects.get(id=id)
        # security review for 1.7 - OK - filtered by search object
        results = Result.objects.filter(search_id=search.id)
    except ObjectDoesNotExist as err:
        logger.error(f'{module_name}_{search.id}: ObjectDoesNotExist: {err}')
        return False

    last_status = search.status
    if not (search.status.endswith('_READY') or search.status == 'RESCORING'):
        logger.warning(f"{module_name}_{search.id}: unexpected status {search.status}, rescore may not work")
        last_status = None

    if len(results) == 0:
        logger.error(f"{module_name}_{search.id}: No results to rescore!")
        return False

    if search.post_result_processor or search.post_result_processors:
        search.status = 'RESCORING'
        search.save()
        # setup processor pipeline
        processor_list = []
        if search.post_result_processor:
            processor_list = [search.post_result_processor]
            if search.post_result_processors:
                logger.warning(f"{module_name}_{search.id}: Ignoring search.post_result_processors, since search.post_result_processor is specified")
        else:
            processor_list = search.post_result_processors
        # end if
        for processor in processor_list:
            try:
                logger.info(f"{module_name}: invoking processor: {processor}")
                post_result_processor = eval(processor, {"processor": processor, "__builtins__": None}, SWIRL_OBJECT_DICT)(search.id)
                if post_result_processor.validate():
                    results_modified = post_result_processor.process()
                else:
                    logger.error(f"{module_name}_{search.id}: {processor}.validate() failed")
                    return False
                # end if
            except (NameError, TypeError, ValueError) as err:
                logger.error(f'{module_name}_{search.id}: {processor}: {err.args}, {err}')
                return False
            # to do: determine if we need to check for message duplication as above
            if results_modified > 0:
                search.messages.append(f"[{datetime.now()}] {processor} updated {results_modified} results")
        # end for
        if last_status:
            search.status = last_status
        else:
            # to do: document this
            search.status = "RESCORED_RESULTS_READY"
        logger.info(f"{module_name}: {search.status}")
        search.save()
        return True
    else:
        logger.warning(f"{module_name}_{search.id}: No post_result_processor or post_result_processors defined")
        return False
