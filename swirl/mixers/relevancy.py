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

from operator import itemgetter

#############################################    
#############################################    

def relevancy_mixer(search_id, results_requested, page):

    module_name = 'relevancy_mixer'

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

    # join json_results
    all_results = []
    for result in results:
        all_results = all_results + result.json_results
    # sort the json_results by score
    sorted_results = sorted(sorted(all_results, key=itemgetter('rank')), key=itemgetter('score'), reverse=True)

    ########################################
    # finalize results
    mix_wrapper['info']['results'] = {}

    results_needed = int(page) * int(results_requested)

    if len(sorted_results) > results_needed:
        mix_wrapper['info']['results']['next_page'] = f'/swirl/results/?search_id={search_id}&result_mixer=round_robin_mixer&page={int(page)+1}'

    sorted_results = sorted_results[(int(page)-1)*int(results_requested):int(page)*int(results_requested)]

    if page > 1:
        mix_wrapper['info']['results']['prev_page'] = f'/swirl/results/?search_id={search_id}&result_mixer=round_robin_mixer&page={int(page)-1}'

    mix_wrapper['results'] = sorted_results

    mix_wrapper['info']['results']['retrieved'] = len(sorted_results)

    # last message 
    if len(sorted_results) > 2:
        mix_wrapper['messages'].append("Results ordered by: relevancy_mixer")

    return mix_wrapper 

