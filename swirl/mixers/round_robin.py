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

#############################################    
#############################################    

def round_robin_mixer(search_id, results_requested, page):

    module_name = 'round_robin_mixer.py'

    if Search.objects.filter(id=search_id).exists():
        search = Search.objects.get(id=search_id)
        results = Result.objects.filter(search_id=search_id)
    else:
        message = f'Error: Search does not exist: {search_id}'
        logger.error(f'{module_name}: {message}')
        mix_wrapper['messages'].append(message)
        return mix_wrapper
    mix_wrapper = create_mix_wrapper(results)
 
    if search.messages:
        for message in search.messages:
            mix_wrapper['messages'].append(message)
    mix_wrapper['info']['search'] = {}
    mix_wrapper['info']['search']['query_string'] = search.query_string
    mix_wrapper['info']['search']['query_string_processed'] = search.query_string_processed

    # mix the results
    results_needed = int(page) * int(results_requested)
    mixed_results = []
    position = 1
    last_len = 0
    while len(mixed_results) < results_needed:
        for result in results:
            if len(result.json_results) >= position:
                mixed_results.append(result.json_results[position-1]) # 0 indexed
                # done if we now have enough
                # w/o the below, we add one per source until exceeding that might be OK but should be deliberate
                if len(mixed_results) == results_needed:
                    break
            else:
                # out of results for that provider
                pass # logger.debug(f'{module_name}: result {result.id} exhausted, need more results for page {page}')
        # end for
        if len(mixed_results) == last_len:
            # not getting any more results
            # logger.debug(f'{module_name}: all result objects exhausted for {search.id}')
            break
        else:
            last_len = len(mixed_results)
        # end if
        position = position + 1
    # end while

    ########################################
    # finalize results
    mix_wrapper['info']['results'] = {}

    results_available = 0
    for result in results:
        results_available = results_available + len(result.json_results)
    if results_available > len(mixed_results):
        mix_wrapper['info']['results']['next_page'] = f'/swirl/results/?search_id={search_id}&result_mixer=round_robin_mixer&page={int(page)+1}'

    if int(page) > 1:
        # chop off all last page bc we stopped at results_requested
        mixed_results = mixed_results[-1*(int(results_requested)):]
        mix_wrapper['info']['results']['prev_page'] = f'/swirl/results/?search_id={search_id}&result_mixer=round_robin_mixer&page={int(page)-1}'

    mix_wrapper['results'] = mixed_results

    mix_wrapper['info']['results']['retrieved'] = len(mixed_results)

    # last message 
    if len(mix_wrapper['results']) > 2:
        mix_wrapper['messages'].append("Results ordered by: round_robin_mixer")

    return mix_wrapper 

#############################################    
#############################################    
