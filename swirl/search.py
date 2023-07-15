
'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from datetime import datetime
import time

from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User, Group
from django.conf import settings

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.models import Search, SearchProvider, Result
from swirl.tasks import federate_task
from swirl.processors import *
from swirl.processors.transform_query_processor_utils import get_pre_query_processor_or_transform
from swirl.utils import select_providers
from swirl.perfomance_logger import SwirlQueryRequestLogger

##################################################
##################################################

module_name = 'search.py'

def search(id, session=None):

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
        logger.info(f"{module_name}_{search.id}: unexpected status {search.status}")
        return False
    if search.status.upper() == 'UPDATE_SEARCH':
        logger.info(f"{module_name}: {search.id}.status == UPDATE_SEARCH")
        update = True
        search.sort = 'date'

    search.status = 'PRE_PROCESSING'
    logger.info(f"{module_name}: {search.status}")
    search.save()
    # check for provider specification

    # check for blank query
    if not search.query_string:
        search.status = 'ERR_NO_QUERY_STRING'
        search.save()
        return False

    # check for starting tag
    start_tag = None
    if ':' in search.query_string.strip().split()[0]:
        start_tag = search.query_string.strip().split()[0].split(':')[0]

    # identify tags in the query
    raw_tags_in_query_list = [tag for tag in search.query_string.strip().split() if ':' in tag]
    tags_in_query_list = []
    for tag in raw_tags_in_query_list:
        if tag.endswith(':'):
            tags_in_query_list.append(tag[:-1])
        else:
            tags_in_query_list.append(tag[:tag.find(':')])

    user = User.objects.get(id=search.owner.id)
    if not user.has_perm('swirl.view_searchprovider'):
        logger.info(f"User {user} needs permission view_searchprovider")
        search.status = 'ERR_NEED_PERMISSION'
        search.save()
        return False

    providers = SearchProvider.objects.filter(active=True, owner=search.owner) | SearchProvider.objects.filter(active=True, shared=True)
    selected_provider_list = []
    if search.searchprovider_list:
        # add providers to list by id, name or tag
        for provider in providers:
            provider_key = None
            if type(search.searchprovider_list[0]) == str:
                provider_key = str(provider.id)
            else:
                provider_key = provider.id
            if provider_key in search.searchprovider_list:
                selected_provider_list.append(provider)
                continue
            if provider.name.lower() in [str(p).lower() for p in search.searchprovider_list]:
                if not provider in selected_provider_list:
                    selected_provider_list.append(provider)
                    continue
            if provider.tags:
                for tag in provider.tags:
                    if tag.lower() in [t.lower() for t in tags_in_query_list]:
                        if not provider in selected_provider_list:
                            selected_provider_list.append(provider)
                            continue
                    if tag.lower() in [p.lower() for p in search.searchprovider_list]:
                        if not provider in selected_provider_list:
                            selected_provider_list.append(provider)
                        # end if
                    # end if
                # end for
            # end if
        # end for
    else:
        # no provider list
        selected_provider_list = select_providers(providers=providers, start_tag=start_tag, tags_in_query_list=tags_in_query_list)

    providers = selected_provider_list

    if len(providers) == 0:
        logger.error(f"{module_name}_{search.id}: no SearchProviders configured")
        search.status = 'ERR_NO_SEARCHPROVIDERS'
        search.save()
        return False

    ########################################
    # pre-query processing, which updates query_string_processed

    swqrx_logger = SwirlQueryRequestLogger(providers, start_time)

    search.status = 'PRE_QUERY_PROCESSING'
    logger.info(f"{module_name}: {search.status}")
    search.save()

    processor_list = []
    processor_list = search.pre_query_processors
    # end if

    if not processor_list:
        search.query_string_processed = search.query_string
    else:
        processed_query = None
        query_temp = search.query_string
        for processor in processor_list:
            logger.info(f"{module_name}: invoking processor: {processor}")
            try:
                pre_query_processor = get_pre_query_processor_or_transform(processor, query_temp, search.tags, user)
                if pre_query_processor.validate():
                    processed_query = pre_query_processor.process()
                else:
                    error_return(f'{module_name}_{search.id}: {processor}.validate() failed', swqrx_logger)
                    return False
                # end if
            except (NameError, TypeError, ValueError) as err:
                error_return(f'{module_name}_{search.id}: {processor}: {err.args}, {err}', swqrx_logger)
                return False
            if processed_query:
                if processed_query != query_temp:
                    search.messages.append(f"[{datetime.now()}] {processor} rewrote query to: {processed_query}")
                    search.save()
                    query_temp = processed_query
            else:
                error_return(f'{module_name}_{search.id}: {processor} returned an empty query, ignoring!', swqrx_logger)
            # end if
        # end for
        search.query_string_processed = query_temp
    # end if

    ########################################
    search.status = 'FEDERATING'
    logger.info(f"{module_name}: {search.status}")
    search.save()

    if not providers:
        msg = f"{module_name}_{search.id}: no active searchprovider specified: {search.searchprovider_list}"
        logger.info(msg)
        search.status = 'ERR_NO_ACTIVE_SEARCHPROVIDERS'
        search.save()
        error_return(msg, swqrx_logger)
        return False
    else:
        for provider in providers:
            federate_task.delay(search.id, provider.id, provider.connector, update, session, swqrx_logger.request_id)

    ########################################
    # asynchronously collect results
    ticks = 0
    error_flag = False
    at_least_one = False
    while 1:
        time.sleep(1)
        ticks = ticks + 1
        # get the list of result objects
        # security review for 1.7 - OK - filtered by search object
        results = Result.objects.filter(search_id=search.id)
        updated = 0
        for result in results:
            if result.status == 'UPDATED':
                updated = updated + 1
            if result.status == 'ERROR':
                error_flag = True
            if result.status == 'READY':
                at_least_one = True
        if len(results) == len(providers):
            # every provider has written a result object - exit
            logger.info(f"{module_name}_{search.id}: all results received!")
            break
        search.status = f'FEDERATING_WAIT_{ticks}'
        logger.info(f"{module_name}: {search.status}")
        SWIRL_TIMEOUT = getattr(settings, 'SWIRL_TIMEOUT', 10)
        if ticks > int(SWIRL_TIMEOUT):
            logger.info(f"{module_name}_{search.id}: timeout!")
            failed_providers = []
            responding_provider_names = []
            for result in results:
                responding_provider_names.append(result.searchprovider)
            for provider in providers:
                if not provider.name in responding_provider_names:
                    failed_providers.append(provider.name)
                    error_flag = True
                    logger.info(f"{module_name}_{search.id}: timeout waiting for: {failed_providers}")
                    search.messages.append(f"[{datetime.now()}] Timeout waiting for: {failed_providers}")
                    search.save()
                # end if
            # end for
            # exit the loop
            swqrx_logger.timeout_execution()
            break
    # end while
    ########################################
    # update query status
    if error_flag:
        if at_least_one:
            search.status = 'PARTIAL_RESULTS'
        else:
            search.status = 'NO_RESULTS_READY'
        # end if
    else:
        search.status = 'FULL_RESULTS'
    logger.info(f"{module_name}: {search.status}")
    ########################################
    # fix the result url
    # to do: figure out a better solution P1
    search.result_url = f"{settings.PROTOCOL}://{settings.HOSTNAME}:8000/swirl/results?search_id={search.id}&result_mixer={search.result_mixer}"
    if {search.result_mixer} == 'DateMixer':
        search.new_result_url = f"{settings.PROTOCOL}://{settings.HOSTNAME}:8000/swirl/results?search_id={search.id}&result_mixer=DateNewItemsMixer"
    else:
        search.new_result_url = f"{settings.PROTOCOL}://{settings.HOSTNAME}:8000/swirl/results?search_id={search.id}&result_mixer=RelevancyNewItemsMixer"
    # note the sort
    if search.sort.lower() == 'date':
        if not update:
            search.messages.append(f"[{datetime.now()}] Requested sort_by_date from all providers")
    search.save()
    # no results ready?
    if search.status == 'NO_RESULTS_READY':
        swqrx_logger.error_execution('NO_RESULTS_READY')
        return True
    ########################################
    # post_result_processing
    if search.post_result_processors:
        last_status = search.status
        search.status = 'POST_RESULT_PROCESSING'
        logger.info(f"{module_name}: {search.status}")
        search.save()

        processor_list = search.post_result_processors

        for processor in processor_list:
            logger.info(f"{module_name}: invoking processor: {processor}")
            try:
                post_result_processor = alloc_processor(processor=processor)(search_id=search.id, request_id=swqrx_logger.request_id)
                if post_result_processor.validate():
                    results_modified = post_result_processor.process()
                else:
                    error_return(f"{module_name}_{search.id}: {processor}.validate() failed", swqrx_logger)
                    return False
                # end if
            except (NameError, TypeError, ValueError) as err:
                error_return(f'{module_name}_{search.id}: {processor}: {err.args}, {err}', swqrx_logger)
                return False
            if not results_modified == 0:
                if results_modified < 0:
                    message = f"[{datetime.now()}] {processor} deleted {-1*results_modified} results"
                else:
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
    swqrx_logger.complete_execution()
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
        logger.info(f"{module_name}_{search.id}: unexpected status {search.status}, rescore may not work")
        last_status = None

    if len(results) == 0:
        logger.error(f"{module_name}_{search.id}: No results to rescore!")
        return False

    if search.post_result_processors:
        search.status = 'RESCORING'
        search.save()
        # setup processor pipeline
        processor_list = search.post_result_processors
        # end if
        for processor in processor_list:
            try:
                logger.info(f"{module_name}: invoking processor: rescoring: {processor}")
                post_result_processor = alloc_processor(processor)
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
        logger.info(f"{module_name}_{search.id}: No post_result_processor or post_result_processors defined")
        return False

def error_return(msg, swqrx_logger):
    logger.error(msg)
    swqrx_logger.error_execution(msg)
