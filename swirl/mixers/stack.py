'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

import django
from django.core.exceptions import ObjectDoesNotExist

from sys import path
from os import environ
from .utils import *

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

from swirl.models import Search, Result

import logging as logger
# logger.basicConfig(level=logger.debug)

from operator import itemgetter

#############################################    
#############################################    

def round_robin_mixer(search_id, results_requested, page, explain):
    return stack_mixer_x(search_id, results_requested, page, 1, explain)

def stack_mixer(search_id, results_requested, page, explain):
    return stack_mixer_x(search_id, results_requested, page, 1, explain)

def stack_1_mixer(search_id, results_requested, page, explain):
    return stack_mixer_x(search_id, results_requested, page, 1, explain)

def stack_2_mixer(search_id, results_requested, page, explain):
    return stack_mixer_x(search_id, results_requested, page, 2, explain)

def stack_3_mixer(search_id, results_requested, page, explain):
    return stack_mixer_x(search_id, results_requested, page, 3, explain)

def stack_mixer_x(search_id, results_requested, page, stack, explain=True):

    module_name = 'stack_mixer.py'

    if Search.objects.filter(id=search_id).exists():
        search = Search.objects.get(id=search_id)
        results = Result.objects.filter(search_id=search_id)
    else:
        message = f'Error: Search does not exist: {search_id}'
        logger.error(f'{module_name}: {message}')
        mix_wrapper['messages'].append(message)
        return mix_wrapper
    mix_wrapper = create_mix_wrapper(results)
        
    if stack == 0:
        stack = int(results_requested / len(results))
        
    if search.messages:
        for message in search.messages:
            mix_wrapper['messages'].append(message)
    mix_wrapper['info']['search'] = {}
    mix_wrapper['info']['search']['query_string'] = search.query_string
    mix_wrapper['info']['search']['query_string_processed'] = search.query_string_processed
    mix_wrapper['info']['search']['rescore_url'] = f'http://localhost:8000/swirl/search/?rescore={search.id}'
    mix_wrapper['info']['search']['rerun_url'] = f'http://localhost:8000/swirl/search/?rerun={search.id}'

    # join json_results
    all_results = []
    for result in results:
        all_results = all_results + result.json_results
    found = len(all_results)

    # sort the json_results by score
    ranked_results = sorted(sorted(all_results, key=itemgetter('searchprovider_rank')), key=itemgetter('swirl_score'), reverse=True)
    # organize results by provider
    dict_ranked_by_provider = {}
    for result in ranked_results:
        if 'searchprovider' in result:
            if not result['searchprovider'] in dict_ranked_by_provider:
                dict_ranked_by_provider[result['searchprovider']] = []
            dict_ranked_by_provider[result['searchprovider']].append(result)
    # generate list of ranked providers
    list_top_each_provider = []
    for provider in dict_ranked_by_provider:
        list_top_each_provider.append(dict_ranked_by_provider[provider][0])
    list_ranked_providers = sorted(list_top_each_provider, key=itemgetter('swirl_score'), reverse=True)
    dict_ranked_providers = {}
    for provider in list_ranked_providers:
        dict_ranked_providers[provider['searchprovider']] = provider['swirl_score']

    # mix the results
    results_needed = int(page) * int(results_requested)
    stacked_results = []
    position = 0
    last_len = 0
    while len(stacked_results) < results_needed:
        for searchprovider in dict_ranked_providers:
            for p in range(0,stack):
                if len(dict_ranked_by_provider[searchprovider]) > position + p:
                    stacked_results.append(dict_ranked_by_provider[searchprovider][position + p])
                # done if we now have enough
                # w/o the below, we add one per source until exceeding that might be OK but should be deliberate
                if len(stacked_results) == results_needed:
                    break
            else:
                # out of results for that provider
                # logger.debug(f'{module_name}: out of results for {searchprovider}')
                pass
            # end for
            if len(stacked_results) == results_needed:
                break
        # end for
        if len(stacked_results) == last_len:
            # no more results 
            logger.warning(f'{module_name}: results exhausted for search: {search.id}')
            break
        else:
            last_len = len(stacked_results)
        # end if
        position = position + stack
    # end while
    
    ########################################
    # finalize results
    mix_wrapper['info']['results'] = {}
    mix_wrapper['info']['results']['retrieved_total'] = found
    # set the order in the dict
    mix_wrapper['info']['results']['retrieved'] = 0

    results_available = 0
    for result in results:
        results_available = results_available + len(result.json_results)
    if results_available > len(stacked_results):
        mix_wrapper['info']['results']['next_page'] = f'http://localhost:8000/swirl/results/?search_id={search_id}&result_mixer=stack_{stack}_mixer&page={int(page)+1}'

    if int(page) > 1:
        # chop off all but the last page of results, bc we stopped at results_needed
        stacked_results = stacked_results[-1*(int(results_requested)):]
        mix_wrapper['info']['results']['prev_page'] = f'http://localhost:8000/swirl/results/?search_id={search_id}&result_mixer=stack_{stack}_mixer&page={int(page)-1}'

    # number the results
    numbered_results = []
    result_number = (int(page)-1)*int(results_requested) + 1
    for result in stacked_results:
        result['swirl_rank'] = result_number
        if not explain:
            del result['explain']
        numbered_results.append(result)
        result_number = result_number + 1

    mix_wrapper['results'] = numbered_results

    mix_wrapper['info']['results']['retrieved'] = len(numbered_results)

    # last message 
    if len(mix_wrapper['results']) > 2:
        mix_wrapper['messages'].append(f"Results ordered by: stack_{stack}_mixer")

    return mix_wrapper

#############################################    
#############################################    
