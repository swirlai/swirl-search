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

def stack_mixer(search_id, results_requested, page):
    return stack_mixer_x(search_id, results_requested, page, 0)

def stack_2_mixer(search_id, results_requested, page):
    return stack_mixer_x(search_id, results_requested, page, 2)

def stack_3_mixer(search_id, results_requested, page):
    return stack_mixer_x(search_id, results_requested, page, 3)

def stack_mixer_x(search_id, results_requested, page, stack):

    module_name = 'stack_mixer.py'
    logger.info(f'{module_name}: mixing')

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

    # mix the results
    results_needed = int(page) * int(results_requested)
    stacked_results = []
    position = 0
    last_len = 0
    while len(stacked_results) < results_needed:
        for result in results:
            if len(stacked_results) >= results_needed:
                break
            for p in range(0,stack):
                if len(result.json_results) > position + p:
                    stacked_results.append(result.json_results[position+p])
                # done if we now have enough
                # w/o the below, we add one per source until exceeding that might be OK but should be deliberate
                if len(stacked_results) >= results_needed:
                    break
                # end
            # end if
        # end for
        # did something get added during the last loop? if not we are out of results, so stop
        if len(stacked_results) == last_len:
            break
        else:
            last_len = len(stacked_results)
        # end if
        position = position + stack
    # end while
    
    ########################################
    # finalize results
    mix_wrapper['info']['results'] = {}

    results_available = 0
    for result in results:
        results_available = results_available + len(result.json_results)
    if results_available > len(stacked_results):
        mix_wrapper['info']['results']['next_page'] = f'/swirl/results/?search_id={search_id}&result_mixer=round_robin_mixer&page={int(page)+1}'

    if int(page) > 1:
        # chop off all but the last page of results, bc we stopped at results_needed
        stacked_results = stacked_results[-1*(int(results_requested)):]
        mix_wrapper['info']['results']['prev_page'] = f'/swirl/results/?search_id={search_id}&result_mixer=round_robin_mixer&page={int(page)-1}'

    mix_wrapper['results'] = stacked_results

    mix_wrapper['info']['results']['retrieved'] = len(stacked_results)

    # last message 
    if len(mix_wrapper['results']) > 2:
        mix_wrapper['messages'].append("Results ordered by: stack_mixer")

    return mix_wrapper

#############################################    
#############################################    
