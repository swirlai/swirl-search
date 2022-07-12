'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.0-
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
from requests.auth import HTTPBasicAuth, HTTPDigestAuth, HTTPProxyAuth
from requests.exceptions import ConnectionError

import urllib.parse
from urllib3.exceptions import NewConnectionError

from jsonpath_ng import parse
from jsonpath_ng.exceptions import JsonPathParserError

from http import HTTPStatus

# models
from swirl.models import Search, Result, SearchProvider

# processors
from swirl.processors import *

from celery.utils.log import get_task_logger
from logging import DEBUG

logger = get_task_logger(__name__)

from .utils import save_result, bind_query_mappings, get_mappings
from .mappings import *

def search(provider_id, search_id):

    # accepts: provider name to execute, query_data a serialized Search object
    # returns: True or string explaining failure

    module_name = 'requests_get'
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

    module_name = f'requests_get ({provider.name})'

    ########################################
    # query processing for this provider
    try:
        processed_query = eval(provider.query_processor)(search.query_string_processed)
    except (NameError, TypeError, ValueError) as err:
        message = f'{module_name}: Error: {err.args}, {err} in provider.query_processor(search.query_string_processed): {provider.query_processor}({search.query_string_processed})'
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages)
        return message
    if processed_query != search.query_string_processed:
        messages.append(f"{provider.query_processor} rewrote query_string to: {processed_query}")

    ########################################
    # construct the query for this provider
    # TO DO: document below (that if provider starts with...)
    if provider.credentials.startswith('HTTP'):
        query_to_provider = bind_query_mappings(provider.query_template, provider.query_mappings, provider.url)
    else:
        query_to_provider = bind_query_mappings(provider.query_template, provider.query_mappings, provider.url, provider.credentials)
    # this should leave one item, {query_string}
    if '{query_string}' in query_to_provider:
        query_to_provider = query_to_provider.replace('{query_string}', urllib.parse.quote_plus(processed_query))
    else:
        message = f'{module_name}: Warning: {{query_string}} missing from query_to_provider: {query_to_provider}'
        logger.warning(f'{message}')
    # end if

    query_mappings = get_mappings(provider.query_mappings)
    # turn on sort, if specified
    if search.sort.lower() == 'date':
        logger.info(f"{module_name}: date sort specified")
        # insert before the last parameter, which is expected to be the user query
        sort_query = query_to_provider[:query_to_provider.rfind('&')]
        if 'DATE_SORT' in query_mappings:
        # end if
            sort_query = sort_query + '&' + query_mappings['DATE_SORT'] + query_to_provider[query_to_provider.rfind('&'):]
            query_to_provider = sort_query
        else:
            # use default query_to_provider
            message = f'{module_name}: Warning: DATE_SORT missing from query_mappings: {query_mappings}'
            logger.warning(f'{message}')
        # end if
    else:
        sort_query = query_to_provider[:query_to_provider.rfind('&')]
        if 'RELEVANCY_SORT' in query_mappings:
        # end if
            sort_query = sort_query + '&' + query_mappings['RELEVANCY_SORT'] + query_to_provider[query_to_provider.rfind('&'):]
            query_to_provider = sort_query
        else:
            # use default query_to_provider
            message = f'{module_name}: Warning: RELEVANCY_SORT missing from query_mappings: {query_mappings}'
            logger.warning(f'{message}')
        # end if
    # end if
        
    # validate query
    if '{' in query_to_provider or '}' in query_to_provider:
        logger.warning(f"{module_name}: warning: {provider.id} found braces {{ or }} in query after template mapping")
    if query_to_provider == "":
        message = f"{module_name}: Error: query_to_provider is null"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages)
        return message

    ########################################
    # get result mappings
    result_mappings = get_mappings(provider.result_mappings)
    mapped_results = {}

    ########################################
    # determine if paging is required
    pages = 1
    if 'PAGE' in query_mappings:
        if provider.results_per_query > 10:
            # yes, gather multiple pages
            pages = int(int(provider.results_per_query) / 10)
            # handle remainder
            if (int(provider.results_per_query) % 10) > 0:
                pages = pages + 1
            # end if
        # end if
    # end if

    ########################################
    # issue the query
    start = 1
    found = None
    for page in range(0, pages):

        if 'PAGE' in query_mappings:
            page_query = query_to_provider[:query_to_provider.rfind('&')]
            page_spec = None
            if 'RESULT_INDEX' in query_mappings['PAGE']:
                page_spec = query_mappings['PAGE'].replace('RESULT_INDEX',str(start))
            if 'RESULT_ZERO_INDEX' in query_mappings['PAGE']:
                page_spec = query_mappings['PAGE'].replace('RESULT_ZERO_INDEX',str(start-1))
            if 'PAGE_INDEX' in query_mappings['PAGE']:
                page_spec = query_mappings['PAGE'].replace('PAGE_INDEX',page+1)
            if page_spec:
                page_query = page_query + '&' + page_spec + query_to_provider[query_to_provider.rfind('&'):]
            else:
                message = f"{module_name}: Warning: failed to resolve PAGE query mapping: {query_mappings['PAGE']}"
                logger.warning(f'{message}')
                # to do: review below
                page_query = query_to_provider
            # end if
        else:
            page_query = query_to_provider

        ########################################
        # check the query
        if page_query == "":
            message = f"{module_name}: Error: page_query is blank"
            logger.error(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages)
            return message

        ########################################
        # issue the query
        logger.info(f"{module_name}: requesting: {provider.connector} -> {page_query}")
        try:
            if provider.credentials.startswith('HTTP'):
                # handle HTTPBasicAuth('user', 'pass') and other forms
                response = requests.get(page_query, auth=eval(provider.credentials))
            else:
                response = requests.get(page_query)
        except NewConnectionError as err:
            message = f"{module_name}: Error: requests.get reports {err} from: {provider.connector} -> {page_query}"
            logger.error(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message
        except ConnectionError as err:
            message = f"{module_name}: Error: requests.get reports {err} from: {provider.connector} -> {page_query}"
            logger.error(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message
        except requests.exceptions.InvalidURL as err:
            message = f"{module_name}: Error: requests.get reports {err} from: {provider.connector} -> {page_query}"
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
            message = f"{module_name}: Error: request.get succeeded, but no json data returned"
            logger.error(f'{message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message

        ########################################
        # extract results using mappings
        for mapping in RESULT_MAPPING_KEYS:
            if mapping == 'RESULT':
                # skip for now
                continue
            if mapping in result_mappings:
                jxp_key = f"$.{result_mappings[mapping]}"
                try:
                    jxp = parse(jxp_key)
                    matches = [match.value for match in jxp.find(json_data)]
                except JsonPathParserError:
                    message = f'{module_name}: Error: JsonPathParser: {err} in provider.result_mappings: {provider.result_mappings}'
                    logger.error(f'{message}')
                    messages.append(message)
                    save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
                    return message
                except (NameError, TypeError, ValueError) as err:
                    message = f'{module_name}: Error: {err.args}, {err} in provider.result_mappings: {provider.result_mappings}'
                    logger.error(f'{message}')
                    messages.append(message)
                    save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
                    return message
                # end try        
                if len(matches) == 0:
                    # no matches
                    continue      
                if len(matches) == 1:
                    mapped_results[mapping] = matches[0]
                else:
                    message = f"{module_name}: Error: {mapping} is matched {len(matches)} expected 1"
                    logger.error(f'{message}')
                    messages.append(message)
                    save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
                    return message
                # end if
            # end if
        # end for
        # check to see if there are results
        found = retrieved = -1
        if 'RETRIEVED' in mapped_results:        
            retrieved = int(mapped_results['RETRIEVED'])
        if 'FOUND' in mapped_results:
            found = int(mapped_results['FOUND'])
        if found == 0 or retrieved == 0:
            # no results, not an error
            message = f"Retrieved 0 of 0 results from: {provider.name}"
            # logger.info(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message
        # end if        
        # process the results
        if not mapped_results['RESULTS']:
            mapped_results['RESULTS'] = json_data
        if not type(mapped_results['RESULTS']) == list:
            # note: solr zero-results should not get here, it should be identified by found 
            message = f"{module_name}: Error: mapped results was not a list, was {type(mapped_results['RESULTS'])}"
            logger.error(f'{message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message
        # end if
        trimmed_response = []
        if 'RESULT' in result_mappings:
            for result in mapped_results['RESULTS']:                
                try:
                    jxp_key = f"$.{result_mappings['RESULT']}"
                    jxp = parse(jxp_key)
                    matches = [match.value for match in jxp.find(result)]
                except JsonPathParserError:
                    message = f'{module_name}: Error: JsonPathParser: {err} in result_mappings: {provider.result_mappings}'
                    logger.error(f'{message}')
                    messages.append(message)
                    save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
                    return message
                except (NameError, TypeError, ValueError) as err:
                    message = f'{module_name}: Error: {err.args}, {err} in result_mappings: {provider.result_mappings}'
                    logger.error(f'{message}')
                    messages.append(message)
                    save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
                    return message
                # end try
                if len(matches) == 1:
                    for match in matches:
                        trimmed_response.append(match)
                else:
                    message = f"{module_name}: Error: control mapping RESULT matched {len(matches)}, expected {provider.results_per_query}"
                    logger.error(f'{message}')
                    messages.append(message)
                    save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
                    return message
                # end if
        else:
            # no RESULT key specified
            trimmed_response = mapped_results['RESULTS']
        # end if
        # check retrieved 
        if retrieved > -1 and retrieved != len(trimmed_response):
            message = f"{module_name}: Warning: retrieved does not match length of response {len(trimmed_response)}"
            logger.warning(f'{message}')
        # end if
        if retrieved == -1:       
            retrieved = len(trimmed_response)
        # end if
        if found == -1:
            # to do: what should this be???
            found = len(trimmed_response)
        # end if
        if found == 0 or retrieved == 0:
            # no results, not an error
            message = f"Retrieved 0 of 0 results from: {provider.name}"
            # logger.info(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=page_query)
            return message
        # end if        

        ########################################
        # check count
        if retrieved < 10:
            # no more pages, so don't request any
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
        messages.append(f"Retrieved {retrieved} of {found} results from: {provider.name}")
        try:
            provider_results = eval(provider.result_processor)(trimmed_response, provider, processed_query)
        except (NameError, TypeError, ValueError) as err:
            message = f'{module_name}: Error: {err.args}, {err} in provider.result_processor(trimmed_response, provider, processed_query): {provider.result_processor}({trimmed_response}, {provider}, {processed_query})'
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
        message = f"{module_name}: Error creating Result object: {err} during save_result(...)"
        logger.error(f'{module_name}: {message}')
        return message

    ########################################
    ########################################

    return True
    
