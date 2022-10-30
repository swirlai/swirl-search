'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.3
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

from django.conf import settings

from swirl.models import Search, Result, SearchProvider
from swirl.processors import *

from celery.utils.log import get_task_logger
from logging import DEBUG
logger = get_task_logger(__name__)

from .utils import get_mappings_dict

from swirl.processors import *

########################################

class Connector:

    type = "SWIRL Connector"

    ########################################

    def __init__(self, provider_id, search_id):

        self.provider_id = provider_id
        self.search_id = search_id
        self.status = 'INIT'
        self.provider = None
        self.search = None
        self.status = ""
        self.query_to_provider = ""
        self.query_mappings = {}
        self.response_mappings = {}
        self.result_mappings = {}
        self.response = None
        self.found = -1
        self.retrieved = -1
        self.results = []
        self.processed_results = []
        self.messages = []
        self.start_time = None

        # get the provider and query
        try:
            self.provider = SearchProvider.objects.get(id=self.provider_id)
            self.search = Search.objects.get(id=self.search_id)
        except ObjectDoesNotExist as err:
            self.error(f'ObjectDoesNotExist: {err}')
            return

        self.query_mappings = get_mappings_dict(self.provider.query_mappings)
        self.response_mappings = get_mappings_dict(self.provider.response_mappings)
        self.result_mappings = get_mappings_dict(self.provider.result_mappings)

        self.status = 'READY'

    ########################################

    def __str__(self):
        return f"{self.type}_{self.provider_id}_{self.search_id}"

    ########################################

    def error(self, message):
        self.messages.append(f'{self}: Error: {message}')
        self.status = 'ERROR'
        self.save_results()
        logger.error(f'{self}: Error: {message}')

    def warning(self, message):
        # self.messages.append(f'{self}: Warning: {message}')
        logger.warning(f'{self}: Warning: {message}')
        self.status = 'WARNING'

    ########################################

    def federate(self):

        '''
        Executes the workflow for a given search and provider
        ''' 

        logger.info(f'{self}: federate()')
        self.start_time = time.time()

        if self.status == 'READY':
            self.status = 'FEDERATING'
            try:
                self.process_query()
                self.construct_query()
                v = self.validate_query()
                if v:
                    self.execute_search()
                    self.normalize_response()
                    self.process_results()
                    self.save_results()
                    self.status = 'READY'
                else:
                    self.error(f'query validation failed: {v}')
                    return
                # end if
            except Exception as err:
                self.error(f'{err}')
                return
            # end try
        else:
            self.error(f'unexpected status: {self.status}')
            return
        # end if

    ########################################

    def process_query(self):

        '''
        Invoke the specified query_processor for this provider, store the processed query_string in query_string_processed
        ''' 

        try:
            processed_query = eval(self.provider.query_processor)(self.search.query_string).process()
        except (NameError, TypeError, ValueError) as err:
            self.error(f'{err.args}, {err} in provider.query_processor(search.query_string_processed): {self.provider.query_processor}({self.search.query_string_processed})')
            return
        if processed_query != self.search.query_string_processed:
            self.search.query_string_processed = processed_query
            self.search.save()
            self.messages.append(f"{self.provider.query_processor} rewrote query_string to: {processed_query}")
        return

    ########################################

    def construct_query(self):

        '''
        Turn the query_string_processed into the query_to_provider
        ''' 

        self.query_to_provider = self.search.query_string_processed
        return

    ########################################

    def validate_query(self):
       
        '''
        Validate the query_to_provider, and return True or False
        ''' 

        if self.query_to_provider == "":
            self.error("query_to_provider is blank or missing")
            return False
        return True

    ########################################

    def execute_search(self):
    
        '''
        Connect to, query and save the response from this provider 
        ''' 

        self.found = 1
        self.retrieved = 1
        self.response = [ 
            {
                'title': f'{self.query_to_provider}', 
                'body': f'Did you search for {self.query_to_provider}?', 
                'author': f'{self}'
            }
        ]
        self.messages.append(f"{self} created 1 mock response")
        return

    ########################################

    def normalize_response(self):
        
        '''
        Transform the response from the provider into a json (list) and store as results
        ''' 

        if self.response:
            if len(self.response) == 0:
                # no results, not an error
                self.retrieved = 0
                self.messages.append(f"Retrieved 0 of 0 results from: {self.provider.name}")
                self.status = 'READY'
                return

        self.results = self.response
        return

    ########################################

    def process_results(self):

        '''
        Process the json results through the specified result processor for the provider, updating processed_results
        ''' 

        if self.found > 0:
            # process results
            if self.results:
                retrieved = len(self.results)
            self.messages.append(f"Retrieved {retrieved} of {self.found} results from: {self.provider.name}")
            try:
                processed_results = eval(self.provider.result_processor)(self.results, self.provider, self.search.query_string_processed).process()
            except (NameError, TypeError, ValueError) as err:
                self.error(f'{err.args}, {err} in provider.result_processor(): {self.provider.result_processor}({self.results}, {self.provider}, {self.processed_query})')
                return
            self.processed_results = processed_results
        # end if
        return

    ########################################

    def save_results(self):

        '''
        Store the transformed results as a Result object in the database, linked to the search_id
        ''' 

        # timing
        end_time = time.time()

        try:
            new_result = Result.objects.create(search_id=self.search, searchprovider=self.provider.name, provider_id=self.provider.id, query_to_provider=self.query_to_provider, result_processor=self.provider.result_processor, messages=self.messages, found=self.found, retrieved=self.retrieved, time=f'{(end_time - self.start_time):.1f}', json_results=self.processed_results)
            new_result.save()
        except Error as err:
            self.error(f'save_result() failed: {err}')
        return