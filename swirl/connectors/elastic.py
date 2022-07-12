'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
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

# connector
########################################
from elasticsearch import Elasticsearch
import elasticsearch

# models
from swirl.models import Search, SearchProvider

# processors
from swirl.processors import *

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from .utils import save_result, bind_query_mappings

def search(provider_id, search_id):

    # accepts: provider name to execute, query_data a serialized Search object
    # returns: True or string explaining failure

    module_name = 'elastic.py'
    message = ""
    messages = []    

    # get the query
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
        logger.info(f'{module_name}: processed query: {processed_query}')
        messages.append(f"{provider.query_processor} rewrote query_string to: {processed_query}")

    ########################################
    # connect to elasticsearch

    logger.info("elastic: connecting")

    try:
        es = eval(f'Elasticsearch({provider.credentials}, {provider.url})')
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

    logger.info("elastic: connected")

    ########################################
    # construct the query
    if provider.credentials.startswith('HTTP'):
        query_to_provider = bind_query_mappings(provider.query_template, provider.query_mappings, provider.url)
    else:
        query_to_provider = bind_query_mappings(provider.query_template, provider.query_mappings, provider.url, provider.credentials)

    # now should only have {query_string}
    if '{query_string}' in provider.query_template:
        query_to_provider = query_to_provider.replace('{query_string}', processed_query)
    # elastic queries always have braces, do not check/reject!

    if query_to_provider == "":
        message = f"{module_name}: Error: query_to_provider is blank, check searchprovider.connector"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages)
        return message

    # to do: all mappings need overhaul per requests_get
    sort_field = ""
    if 'sort_by_date' in provider.query_mappings:
        for field in provider.query_mappings.split(','):
            if field.lower().startswith('sort_by_date'):
                if '=' in field:
                    sort_field = field[field.find('=')+1:]
                else:
                    message = f"{provider.id} sort_by_date mapping is missing '=', try removing spaces?"
                    logger.warning(f'{module_name}: {message}')
                    messages.append(message)
                    save_result(search=search, provider=provider, messages=messages)
                    return message
                # end if
            # end if
        # end for
    # end if

    ########################################
    # issue the query
    issue_search = ""
    if search.sort.lower() == 'date':
        # to do: support ascending??? p2
        issue_search = 'es.search(' + query_to_provider + f", sort=[{{'{sort_field}': 'desc'}}], size=" + str(provider.results_per_query) + ')'
    else:
        issue_search = 'es.search(' + query_to_provider + ', size=' + str(provider.results_per_query) + ')'
    # end if
    logger.info(f"{module_name}: issuing query: {provider.connector} -> {query_to_provider}")
    try:
        response = eval(issue_search)
    except elasticsearch.ConnectionError as err:
        message = f"{module_name}: Error: es.search reports: {err} from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
        return message
    except elasticsearch.NotFoundError:
        message = f"{module_name}: Error: es.search reports HTTP/404 (Not Found) from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
        return message
    except elasticsearch.RequestError:
        message = f"{module_name}: Error: es.search reports Bad Request"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
        return message
    except elasticsearch.AuthenticationException:
        message = f"{module_name}: Error: es.search reports HTTP/401 (Forbidden) from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
        return message
    except elasticsearch.AuthorizationException:
        message = f"{module_name}: Error: es.search reports HTTP/403 (Access Denied) from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
        return message
    except elasticsearch.ApiError as err:
        message = f"{module_name}: Error: es.search reports '{err}' from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
        return message

    ########################################
    # normalize the response
    if len(response) == 0:
        message = f"{module_name}: Error: search succeeded, but found no json data in response from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
        return message
    if not 'hits' in response.keys():
        message = f"{module_name}: Error: search succeeded, but json data was missing key 'hits' from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
        return message

    ########################################
    # check found
    found = response['hits']['total']['value']
    if found == 0:
        # no results, not an error
        message = f"Retrieved 0 of 0 results from: {provider.name}"
        logger.debug(f'{module_name}: {message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
        return message

    ########################################
    # normalize response
    trimmed_response = response['hits']['hits']
    retrieved = len(trimmed_response)
    # prepare messages
    message = f"Retrieved {retrieved} of {found} results from: {provider.name}"
    logger.info(f'{module_name}: {message}')
    messages.append(message)

    ########################################
    # process results
    try:
        provider_results = eval(provider.result_processor)(trimmed_response, provider, processed_query)
    except NameError as err:
        message = f'{module_name}: Error: NameError: {err} from: {provider.name}'
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
        return message
    except TypeError as err:
        message = f'{module_name}: Error: TypeError: {err} from: {provider.name}'
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
        return message
    # end try
        
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
