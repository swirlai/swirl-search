'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL Preview3
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

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

#############################################    
#############################################    

def save_result(search, provider, query_to_provider="", messages=[], found=0, retrieved=0, provider_results=[]):

    new_result = Result.objects.create(search_id=search, searchprovider=provider.name, query_to_provider=query_to_provider, result_processor=provider.result_processor, messages=messages, found=found, retrieved=retrieved, json_results=provider_results)
    new_result.save()
    return new_result

#############################################    

def bind_query_mappings(query_template, query_mappings, credentials=None):

    module_name = 'bind_mappings'

    bound_query_template = query_template
    mappings = []

    if query_mappings:
        mappings = query_mappings.split(',')
    if credentials:
        for add_mapping in credentials.split(','):
            mappings.append(add_mapping)
    if mappings:
        for mapping in mappings:
            stripped_mapping = mapping.strip()
            if '=' in stripped_mapping:
                k = stripped_mapping[:stripped_mapping.find('=')]
                v = stripped_mapping[stripped_mapping.find('=')+1:]
            else:
                logger.warning(f"{module_name}: warning: mapping {stripped_mapping} is missing '='")
                continue
            # end if
            template_key = '{' + k + '}'
            if template_key in query_template:
                bound_query_template = bound_query_template.replace(template_key, v)
            else:
                logger.warning(f"{module_name}: warning: mapping {k} not found in template, does it need braces {{}}?")
                continue
        # end for
    # end if

    return bound_query_template
