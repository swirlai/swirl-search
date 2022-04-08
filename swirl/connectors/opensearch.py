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
import time

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

# connector
########################################
import requests
from requests.exceptions import ConnectionError
from urllib3.exceptions import NewConnectionError

from http import HTTPStatus
import urllib.parse

# models
from swirl.models import Search, Result, SearchProvider

# processors
from swirl.processors import *

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from .utils import save_result, bind_query_mappings

def search(provider_id, search_id):

    # accepts: provider name to execute, query_data a serialized Search object
    # returns: True or string explaining failure

    module_name = 'opensearch.py'
    message = ""
    messages = []    

    # get the provider and query
    try:
        provider = SearchProvider.objects.get(id=provider_id)
        search = Search.objects.get(id=search_id)
    except ObjectDoesNotExist as err:
        message = f'{module_name}: Error: ObjectDoesNotExist: {err} from: {provider.name}'
        logger.error(f'{module_name}: {message}')
        return message

    ########################################
    # query processing for this provider
    try:
        processed_query = eval(provider.query_processor)(search.query_string_processed)
    except NameError as err:
        message = f'{module_name}: Error: NameError: {err} from: {provider.name}'
        logger.error(f'{module_name}: {message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages)
        return message
    except TypeError as err:
        message = f'{module_name}: Error: TypeError: {err} from: {provider.name}'
        logger.error(f'{module_name}: {message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages)
        return message
    if processed_query != search.query_string_processed:
        messages.append(f"{provider.query_processor} rewrote query_string to: {processed_query}")

    ########################################
    # construct the query for this provider
    query_to_provider = bind_query_mappings(provider.query_template, provider.query_mappings, provider.credentials)
    # process built-ins
    if '{url}' in provider.query_template:
        query_to_provider = query_to_provider.replace('{url}',provider.url)
    if '{query_string}' in provider.query_template:
        query_to_provider = query_to_provider.replace('{query_string}', urllib.parse.quote_plus(processed_query))   
    # check for remaining variables which should not be present in opensearch
    if '{' in query_to_provider or '}' in query_to_provider:
        logger.warning(f"{module_name}: warning: {provider.id} found braces {{ or }} in query after template mapping")

    ########################################
    # sort, if specified
    if search.sort.lower() == 'date':
        sort_query = query_to_provider[:query_to_provider.rfind('&')]
        sort_query = sort_query + f'&sort=date' + query_to_provider[query_to_provider.rfind('&'):]
        logger.info(f"{module_name}: date sort specified")
        query_to_provider = sort_query

    ########################################
    # handle paging i.e. results_requested > 10, which e.g. requires start=11 for page 2
    pages = 1
    if provider.results_per_query > 10:
        # will have to gather multiple pages
        pages = int(int(provider.results_per_query) / 10)
        # handle remainder
        if (int(provider.results_per_query) % 10) > 0:
            pages = pages + 1
        # end if
    # end if
    found = None
    retrieved = 0
    start = 1
    trimmed_response = None
    provider_results = ""

    for page in range(0, pages):

        ########################################
        # prepare the page query
        page_query = query_to_provider[:query_to_provider.rfind('&')]
        page_query = page_query + f'&start={start}' + query_to_provider[query_to_provider.rfind('&'):]

        ########################################
        # check the query
        if page_query == "":
            message = f"{module_name}: Error: page_query is blank, check searchprovider.connector from: {provider.name}"
            logger.error(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages)
            return message

        ########################################
        # issue the query
        logger.debug(f"{module_name}: requesting: {provider.connector} -> {page_query}")
        try:
            response = requests.get(page_query)
        except NewConnectionError as err:
            message = f"{module_name}: Error: requests.get reports {err} from: {provider.name}"
            logger.error(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message
        except ConnectionError as err:
            message = f"{module_name}: Error: requests.get reports {err} from: {provider.name}"
            logger.error(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message
        except requests.exceptions.InvalidURL as err:
            message = f"{module_name}: Error: requests.get reports {err} from: {provider.name}"
            logger.error(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message
        if response.status_code != HTTPStatus.OK:
            message = f"{module_name}: Error: request.get returned: {response.status_code} {response.reason} from: {provider.name}"
            logger.error(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message
    
        ########################################
        # normalize the response
        json_data = response.json()
        if len(json_data) == 0:
            message = f"{module_name}: Error: request.get succeeded, but found no json data in response from: {provider.name}"
            logger.error(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message
        if not 'searchInformation' in json_data:
            message = f"{module_name}: Error: request.get succeeded, but json data was missing key 'searchInformation' from: {provider.name}"
            logger.error(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message

        ########################################
        # check found - once
        if found == None:
            found = int(json_data['searchInformation']['totalResults'])
            formatted_found = json_data['searchInformation']['formattedTotalResults']
        if found == 0:
            # no results, not an error
            message = f"Retrieved 0 of 0 results from: {provider.name}"
            logger.debug(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message
        ########################################
        # check count
        if not 'queries' in json_data:
            message = f"{module_name}: Error: request.get succeeded, found > 0, but json data was missing key 'queries' from: {provider.name}"
            logger.error(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message
        count = int(json_data['queries']['request'][0]['count'])
        # note: this can be 10 when found = 0, which is why we bail when found = 0 :-)
        if count > 0:
            if 'items' in json_data:
                # aggregate the items
                if trimmed_response:
                    trimmed_response = trimmed_response + json_data['items']
                else:
                    trimmed_response = json_data['items']
                # end if
            else:
                # unknown error
                message = f"{module_name}: Error: request.get succeeded, count > 0, but json data was missing key 'items' from: {provider.name}"
                logger.error(f'{module_name}: {message}')
                messages.append(message)
                save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
                return message
            # end if
        # end if
        if count < 10:
            # don't request any more pages
            break
        # end if
        start = start + 10 # get only as many pages as required to satisfy provider results_per_query setting, in increments of 10
        # wait
        time.sleep(1)

    # end for

    if found:

        ########################################
        # process results
        retrieved = len(trimmed_response)
        messages.append(f"Retrieved {retrieved} of {formatted_found} results from: {provider.name}")
        try:
            provider_results = eval(provider.result_processor)(trimmed_response, provider, processed_query)
        except NameError as err:
            message = f'{module_name}: Error: NameError: {err} from: {provider.name}'
            logger.error(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message
        except TypeError as err:
            message = f'{module_name}: Error: TypeError: {err} from: {provider.name}'
            logger.error(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message
        # end try

    # end if

    ########################################
    # store the results as new Result
    try:
        result = save_result(search=search, provider=provider, query_to_provider=page_query, messages=messages, found=found, retrieved=retrieved, provider_results=provider_results) 
    except Error as err:
        message = f"{module_name}: Error creating Result object: {err} from: {provider.name}"
        logger.error(f'{module_name}: {message}')
        return message

    ########################################
    ########################################

    return True
    
