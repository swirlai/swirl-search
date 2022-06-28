'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

import django
from sys import path
from os import environ

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

# models
from swirl.models import Result
from .mappings import *

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

#############################################    
#############################################    

def save_result(search, provider, query_to_provider="", messages=[], found=0, retrieved=0, provider_results=[]):

    # accepts: model data
    # returns: results of saving those items 
    # makes no chnages

    new_result = Result.objects.create(search_id=search, searchprovider=provider.name, query_to_provider=query_to_provider, result_processor=provider.result_processor, messages=messages, found=found, retrieved=retrieved, json_results=provider_results)
    new_result.save()
    return new_result

#############################################    

def bind_query_mappings(query_template, query_mappings, url, credentials=None):

    # accepts: various parameters
    # returns: query template with all mappings (including URL and any credentials in key=value format) bound
    # ignores: QUERY_MAPPING_VARIABLES (e.g. RESULT_INDEX)
    
    module_name = 'bind_query_mappings'

    bound_query_template = query_template
    mappings = []

    if query_mappings:
        mappings = query_mappings.split(',')

    if credentials:
        if not credentials.startswith('HTTP'):
            for add_mapping in credentials.split(','):
                mappings.append(add_mapping)

    if url:
        if '{url}' in bound_query_template:
            bound_query_template = bound_query_template.replace('{url}', url)

    if mappings:
        for mapping in mappings:
            stripped_mapping = mapping.strip()
            if '=' in stripped_mapping:
                # take the right most, in case there are multiple which is permitted
                source_key = stripped_mapping[:stripped_mapping.rfind('=')]
                swirl_key = stripped_mapping[stripped_mapping.rfind('=')+1:]
            else:
                logger.warning(f"{module_name}: warning: mapping {stripped_mapping} is missing '='")
                continue
            # end if
            if swirl_key in QUERY_MAPPING_VARIABLES:
                # ignore it
                continue
            template_key = '{' + source_key + '}'
            if template_key in bound_query_template:
                bound_query_template = bound_query_template.replace(template_key, swirl_key)
                continue
            logger.warning(f"{module_name}: warning: mapping {source_key} not found in template, does it need braces {{}}?")
        # end for
    # end if

    return bound_query_template

#############################################    

def get_mappings(mappings):

    # accepts: any provider mapping
    # returns: dict of the mappings by swirl_key
    # warns if any swirl_key is repeated

    module_name = 'get_mappings'

    dict_mappings = {}
    
    mappings = mappings.split(',')
    if mappings:
        for mapping in mappings:
            stripped_mapping = mapping.strip()
            if '=' in stripped_mapping:
                source_key = stripped_mapping[:stripped_mapping.rfind('=')]
                swirl_key = stripped_mapping[stripped_mapping.rfind('=')+1:]
            else:
                source_key = None
                swirl_key = stripped_mapping
            # end if
            if swirl_key in dict_mappings:
                logger.warning(f"{module_name}: warning: control mapping {swirl_key} found more than once, ignoring")
                continue
            dict_mappings[swirl_key] = source_key
        # end for
    # end if
            
    return dict_mappings

        
