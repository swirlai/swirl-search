'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL Preview3
'''

import django
from django.db import Error
from django.core.exceptions import ObjectDoesNotExist
from sys import path
from os import environ

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

# connectors

########################################
import requests
from requests.auth import HTTPDigestAuth
from http import HTTPStatus
import urllib.parse

# models
from swirl.models import Search, SearchProvider

# processors
from swirl.processors import *

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from .utils import save_result

def search(provider_id, search_id):

    # accepts: provider name to execute, query_data a serialized Search object
    # returns: normalized json results

    module_name = 'requests_get.py'
    message = ""
    messages = []    

    # get the provider and query
    try:
        provider = SearchProvider.objects.get(id=provider_id)
        search = Search.objects.get(id=search_id)
    except ObjectDoesNotExist as err:
        message = f'{module_name}: Error: ObjectDoesNotExist: {err}'
        logger.error(f'{message}')
        return message

    ########################################
    # query processing for this provider
    try:
        processed_query = eval(provider.query_processor)(search.query_string_processed)
    except NameError as err:
        message = f'{module_name}: Error: NameError: {err} from: {provider.name}'
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages)
        return message
    except TypeError as err:
        message = f'{module_name}: Error: TypeError: {err} from: {provider.name}'
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages)
        return message
    if processed_query != search.query_string_processed:
        messages.append(f"{provider.query_processor} rewrote query_string to: {processed_query}")

    ########################################
    # construct the query for this provider
    query_to_provider = provider.query_template
    # process built-ins
    if '{url}' in provider.query_template:
        query_to_provider = query_to_provider.replace('{url}',provider.url)
    if '{query_string}' in provider.query_template:
        query_to_provider = query_to_provider.replace('{query_string}', urllib.parse.quote_plus(processed_query))   
    # now process mappings
    mappings = []
    if provider.query_mappings:
        mappings = provider.query_mappings.split(',')
    if provider.credentials:
        for add_mapping in provider.credentials.split(','):
            mappings.append(add_mapping)
    if mappings:
        for mapping in mappings:
            stripped_mapping = mapping.strip()
            if '=' in stripped_mapping:
                k = stripped_mapping[:stripped_mapping.find('=')]
                v = stripped_mapping[stripped_mapping.find('=')+1:]
            else:
                logger.warning(f"{module_name}: warning: {provider.id} mapping {stripped_mapping} is missing '='")
                continue
            # end if
            template_key = '{' + k + '}'
            if template_key in provider.query_template:
                query_to_provider = query_to_provider.replace(template_key, v)
            else:
                logger.warning(f"{module_name}: warning: {provider.id} mapping {k} not found in template, does it need braces {{}}?")
                continue
        # end for
    # end if

    if '{' in query_to_provider or '}' in query_to_provider:
        logger.warning(f"{module_name}: warning: {provider.id} found braces {{ or }} in query after template mapping")

    if query_to_provider == "":
        message = f"{module_name}: Error: query_to_provider is blank, check searchprovider.connector from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages)
        return message

    ########################################
    # issue the query
    logger.debug(f"{module_name}: issuing query: {provider.connector} -> {query_to_provider}")
    try:
        if provider.credentials:
            response = requests.get(query_to_provider, auth=eval(provider.credentials))
        else:
            response = requests.get(query_to_provider)
    except ConnectionError as err:
        message = f"{module_name}: Error: requests.get reports {err} from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages)
        return message
    if response.status_code != HTTPStatus.OK:
        message = f"{module_name}: Error: request.get returned: {response.status_code} {response.reason} from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages)
        return message

    ########################################
    # normalize the response
    trimmed_response = None
    found = 0
    retrieved = 0
    json_data = response.json()
    if len(json_data) == 0:
        # to do: test this
        message = f"{module_name}: null response from provider; this may be normal from: {provider.name}"
        logger.debug(f'{module_name}: {message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages)
        return message

    ########################################
    found = len(json_data)
    if found > 0:
        # trim results if longer than expected - to do: make this a mapping special keyword etc P4
        if len(json_data) > provider.results_per_query:
            trimmed_response = json_data[:provider.results_per_query]
        else:
            trimmed_response = json_data
        # end if
        retrieved = len(trimmed_response)
        # prepare messages
        messages.append(f"Retrieved {retrieved} of {found} results from: {provider.name}")
        ########################################
        # result processing
        try:
            provider_results = eval(provider.result_processor)(trimmed_response, provider, processed_query)
        except NameError as err:
            message = f'{module_name}: Error: NameError: {err} from: {provider.name}'
            logger.error(f'{message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages)
            return message
        except TypeError as err:
            message = f'{module_name}: Error: TypeError: {err} from: {provider.name}'
            logger.error(f'{message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages)
            return message
        # end try
    else:
        message = f"Warning: no results from provider: {provider.name}"
        messages.append(message)
        provider_results = []
    # end if

    ########################################
    # store the results as new Result
    try:
        result = save_result(search=search, provider=provider, query_to_provider=query_to_provider, messages=messages, found=found, retrieved=retrieved, provider_results=provider_results) 
    except Error as err:
        message = f"{module_name}: Error creating Result object: {err} from: {provider.name}"
        logger.error(f'{message}')
        return message

    ########################################
    ########################################

    return True
    
