'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

import django
from django.db import Error
from django.core.exceptions import ObjectDoesNotExist
import os
from sys import path
from os import environ

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

# connectors

########################################
import sqlite3
from sqlite3 import Error

# models
from swirl.models import Search, Result, SearchProvider

# processors
from swirl.processors.generic import *
from swirl.processors.swirl_result_matches import *

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from .utils import save_result, bind_query_mappings

########################################
# sqlite3

def create_connection(path):
    connection = None
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection

def execute_read_query(connection, query):
    cursor = connection.cursor()
    rows = None
    cursor.execute(query)
    rows = cursor.fetchall()
    return rows

def execute_count_query(connection, query):
    cursor = connection.cursor()
    rows = None
    cursor.execute(query)
    row = cursor.fetchone()
    if row == None:
        return 0
    else:
        return row[0]

########################################
########################################

def search(provider_id, search_id):

    # accepts: provider name to execute, query_data a serialized Search object
    # returns: True or string explaining failure

    module_name = 'sqlite3.py'
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
    # connect to the db
    db_path = provider.url
    if not os.path.exists(db_path):
        message = f"{module_name}: Error: db_path does not exist from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages)
        # returning a message is preferred, although False is OK :\
        return message
    try:
        connection = create_connection(db_path)
    except Error as err:
        message = f"{module_name}: Error: {err} connecting to database: {db_path} from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages)
        return message
    logger.info(f"{module_name}: connected to sqlite db: {db_path}")

    ########################################
    # handle ;
    # to do: test this
    if not provider.query_template.endswith(';'):
        provider.query_template = provider.query_template + ';'
    # end if
    
    ########################################
    # construct the query for this provider to check the count
    count_query = bind_query_mappings(provider.query_template, provider.query_mappings)
    if '{fields}' in count_query:
        count_query = count_query.replace('{fields}', 'COUNT(*)')
    # no error if missing assume they may have hand-written the SQL
    if '{query_string}' in count_query:
        count_query = count_query.replace('{query_string}', processed_query)
        
    if '{' in count_query or '}' in count_query:
        logger.warning(f"{module_name}: warning: {provider.id} found braces {{ or }} in count_query after template mapping")

    if count_query == "":
        message = f"{module_name}: Error: count_query is blank, check searchprovider.connector from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages)
        return message

    ########################################
    # issue the count(*) query
    logger.debug(f"{module_name}: requesting: {provider.connector} -> {count_query}")
    try:
        found = execute_count_query(connection, count_query)
    except Error as err:
        message = f"{module_name}: Error: execute_count_query: {err} from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages, query_to_provider=count_query)
        return message

    if 'json' in count_query.lower():
        logger.debug(f"{module_name}: ignoring 0 return from find, since 'json' appears in the query_string")
    else:
        if found == 0:
            message = f"Retrieved 0 of 0 results from: {provider.name}"
            logger.info(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=count_query)
            return message
        # end if
    # end if

    ########################################
    # construct the query for the provider
    query_to_provider = bind_query_mappings(provider.query_template, provider.query_mappings)
    if '{query_string}' in query_to_provider:
        query_to_provider = query_to_provider.replace('{query_string}', processed_query)

    # check the query
    if '{' in query_to_provider or '}' in query_to_provider:
        logger.warning(f"{module_name}: warning: {provider.id} found braces {{ or }} in count_query after template mapping")

    if query_to_provider == "":
        message = f"{module_name}: Error: query_to_provider is blank, check searchprovider.connector from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
        return message

    # sort field

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
                    save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
                    return message
                # end if
            # end if
        # end for
    # end if

    if search.sort.lower() == 'date':
        if query_to_provider.endswith(';'):
            if sort_field:
                query_to_provider = query_to_provider.replace(';', f' order by {sort_field} desc;')
            else:
                logger.info(f"{module_name}: {provider.id} has no sort_field, ignoring request to sort this provider")
            # end if
        else:
            message = f"{provider.id} query_to_provider is missing ';' at end"
            logger.warning(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
            return message
        # end if
    # end if

    # results per query
    query_to_provider = query_to_provider.replace(';', ' limit ' + str(provider.results_per_query) + ';')

    ########################################
    # issue the main query
    logger.debug(f"{module_name}: requesting: {provider.connector} -> {query_to_provider}")
    try:
        rows = execute_read_query(connection, query_to_provider)
    except Error as err:
        message = f"{module_name}: Error: execute_count_query: {err} from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
        return message

    if found == 0:
        found=len(rows)
        # is this an error???
        if found == 0:
            message = f"{module_name}: Retrieved 0 of 0 results from: {provider.name}"
            logger.info(f'{module_name}: {message}')
            messages.append(message)
            save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
            return message
    # end if

    ########################################
    # normalize the response
    trimmed_rows = []
    field_list = rows[0].keys()
    for row in rows:
        dict_row = {}
        n_field = 0
        for field in field_list:
            dict_row[field] = row[n_field]
            n_field = n_field + 1
        # end for
        trimmed_rows.append(dict_row)
    # end for
    retrieved = len(trimmed_rows)
    if retrieved == 0:
        message = f"{module_name}: Error: rows were returned but couldn't serialize them from: {provider.name}"
        logger.error(f'{message}')
        messages.append(message)
        save_result(search=search, provider=provider, messages=messages, query_to_provider=query_to_provider)
        return message
    if retrieved > found:
        found = retrieved
    # prepare messages
    messages.append(f"Retrieved {retrieved} of {found} results from: {provider.name}")

    ########################################
    # result processing
    try:
        provider_results = eval(provider.result_processor)(trimmed_rows, provider, processed_query)
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

    ########################################
    # store the results as new Result
    try:
        result = save_result(search=search, provider=provider, query_to_provider=query_to_provider, messages=messages, found=found, retrieved=retrieved, provider_results=provider_results) 
        # Result.objects.create(search_id=search, searchprovider=provider.name, query_to_provider=query_to_provider, result_processor=provider.result_processor, messages=messages, found=found, retrieved=retrieved, json_results=provider_results)
    except Error as err:
        message = f"{module_name}: Error creating Result object: {err} from: {provider.name}"
        logger.error(f'{message}')
        return message

    ########################################
    ########################################

    return True
    
