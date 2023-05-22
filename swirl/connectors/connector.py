'''
@author:     Sid Probstein
@contact:    sid@swirl.today
@version:    SWIRL 1.3
'''

from sys import path
from os import environ
import time

import django
from django.db import Error
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

from django.conf import settings

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.models import Search, Result, SearchProvider
from swirl.connectors.utils import get_mappings_dict
from swirl.processors import *
from swirl.processors.transform_query_processor_utils import get_query_processor_or_transform

SWIRL_OBJECT_LIST = SearchProvider.QUERY_PROCESSOR_CHOICES + SearchProvider.RESULT_PROCESSOR_CHOICES + Search.PRE_QUERY_PROCESSOR_CHOICES + Search.POST_RESULT_PROCESSOR_CHOICES

SWIRL_OBJECT_DICT = {}
for t in SWIRL_OBJECT_LIST:
    SWIRL_OBJECT_DICT[t[0]]=eval(t[0])

########################################
########################################

class Connector:

    type = "SWIRL Connector"

    ########################################

    def __init__(self, provider_id, search_id, update):

        self.provider_id = provider_id
        self.search_id = search_id
        self.update = update
        self.status = 'INIT'
        self.provider = None
        self.search = None
        self.query_string_to_provider = ""
        self.result_processor_json_feedback = {}
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
        self.search_user = None

        # get the provider and query
        try:
            self.provider = SearchProvider.objects.get(id=self.provider_id)
            self.search = Search.objects.get(id=self.search_id)
        except ObjectDoesNotExist as err:
            self.error(f'ObjectDoesNotExist: {err}')
            return

        try:
            self.search_user = User.objects.get(id=self.search_id)
        except ObjectDoesNotExist as err:
            logger.warn("unable to find search user, no auth check")

        self.query_mappings = get_mappings_dict(self.provider.query_mappings)
        self.response_mappings = get_mappings_dict(self.provider.response_mappings)
        self.result_mappings = get_mappings_dict(self.provider.result_mappings)

        self.status = 'READY'

    ########################################

    def __str__(self):
        return f"{self.type}_{self.search_id}_{self.provider_id}"

    ########################################

    def message(self, message):
        self.messages.append(f'[{datetime.now()}] {message}')

    def error(self, message, save_results=True):
        logger.error(f'{self}: {message}')
        self.message(f'Error: {self}: {message}')
        self.status = 'ERROR'
        if save_results:
            self.save_results()

    def warning(self, message):
        logger.warning(f'{self}: {message}')

    ########################################

    def federate(self, session):

        '''
        Executes the workflow for a given search and provider
        '''

        self.start_time = time.time()

        if self.status == 'READY':
            self.status = 'FEDERATING'
            try:
                self.process_query()
                self.construct_query()
                v = self.validate_query(session)
                if v:
                    self.execute_search(session)
                    if self.status not in ['FEDERATING', 'READY']:
                        self.error(f"execute_search() failed, status {self.status}")
                        self.save_results()
                        return False
                    if self.status == 'FEDERATING':
                        self.normalize_response()
                    if self.status not in ['FEDERATING', 'READY']:
                        self.error(f"normalize_response() failed, status {self.status}")
                        self.save_results()
                        return False
                    else:
                        self.process_results()
                    if self.status == 'READY':
                        res = self.save_results()
                        if res:
                            return True
                        else:
                            return False
                    else:
                        self.error(f"process_results() failed, status {self.status}")
                        return False
                else:
                    self.error(f'validate_query() failed: {v}')
                    return False
                # end if
            except Exception as err:
                self.error(f'{err}')
                return False
            # end try
        else:
            self.error(f'unexpected status: {self.status}')
            return False
        # end if

    ########################################

    def process_query(self):

        '''
        Invoke the specified query_processor for this provider on search.query_string_processed, store the result in self.query_string_to_provider
        '''

        logger.info(f"{self}: process_query()")
        processor_list = []
        processor_list = self.provider.query_processors

        if not processor_list:
            self.query_string_to_provider = self.search.query_string_processed
            return

        query_temp = self.search.query_string_processed
        for processor in processor_list:
            logger.info(f"{self}: invoking processor: query processor: {processor}")
            try:
                processed_query = get_query_processor_or_transform(processor, query_temp, SWIRL_OBJECT_DICT, self.provider.query_mappings, self.provider.tags, self.search_user).process()
            except (NameError, TypeError, ValueError) as err:
                self.error(f'{processor}: {err.args}, {err}')
                return
            if processed_query:
                if processed_query != query_temp:
                    self.message(f"{processor} rewrote {self.provider.name}'s query to: {processed_query}")
                    query_temp = processed_query
            else:
                self.error(f'{processor} returned an empty string, ignoring it!')
                # processing will continue with query_temp which is not updated due to the error
        # end for
        # to do: review this? is it correct?
        self.query_string_to_provider = query_temp
        return

    ########################################

    def construct_query(self):

        '''
        Copy query_string_processed to query_to_provider
        '''

        logger.info(f"{self}: construct_query()")
        self.query_to_provider = self.query_string_to_provider
        return

    ########################################

    def validate_query(self, session=None):

        '''
        Validate the query_to_provider, and return True or False
        '''

        logger.info(f"{self}: validate_query()")
        if self.query_to_provider == "":
            self.error("query_to_provider is blank or missing")
            return False
        return True

    ########################################

    def execute_search(self, session=None):

        '''
        Connect to, query and save the response from this provider
        '''

        logger.info(f"{self}: execute_search()")
        self.found = 1
        self.retrieved = 1
        self.response = [
            {
                'title': f'{self.query_string_to_provider}',
                'body': f'Did you search for {self.query_string_to_provider}?',
                'author': f'{self}'
            }
        ]
        self.message(f"Connector.execute_search() created 1 mock response")
        return

    ########################################

    def normalize_response(self):

        '''
        Transform the response from the provider into a json (list) and store as self.results
        '''

        logger.info(f"{self}: normalize_response()")
        if self.response:
            if len(self.response) == 0:
                # no results, not an error
                self.retrieved = 0
                self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
                self.status = 'READY'
                return

        # trim response to requested length
        if len(self.response) > self.provider.results_per_query:
            self.response = self.response[:self.provider.results_per_query]
            self.retrieved = self.provider.results_per_query

        self.results = self.response
        return

    ########################################

    def process_results(self):

        '''
        Process the json results through the specified result processor for the provider, updating processed_results
        '''

        logger.info(f"{self}: process_results()")

        if self.found == 0:
            return

        # process results
        if self.results:
            retrieved = len(self.results)
        if not self.update:
            self.message(f"Retrieved {retrieved} of {self.found} results from: {self.provider.name}")

        processor_list = []
        processor_list = self.provider.result_processors

        if not processor_list:
            self.processed_results = self.results
            self.status = 'READY'
            return

        processed_results = None
        result_temp = self.results
        for processor in processor_list:
            logger.info(f"{self}: invoking processor: process results {processor}")
            try:
                processed_results = eval(processor, {"processor": processor, "__builtins__": None},
                                         SWIRL_OBJECT_DICT)(result_temp, self.provider,
                                                            self.query_string_to_provider).process()
                ## Check if this processor generated feed back and if so, remember it.
                ## TODO: make this additive for multiple processor. For now the mapping processor
                ## is the only one that generates this.
                if processed_results and 'result_processor_feedback' in processed_results[-1]:
                    self.result_processor_json_feedback =  processed_results.pop(-1)
            except (NameError, TypeError, ValueError) as err:
                self.error(f'{processor}: {err.args}, {err}')
                return
            if processed_results:
                # to do: should we log this?
                result_temp = processed_results
            else:
                self.error(f"{processor} returned no results, ignoring!")
            # end if
        # end for
        self.processed_results = result_temp
        self.status = 'READY'

        return

    ########################################

    def save_results(self):

        '''
        Store the transformed results as a Result object in the database, linked to the search_id
        '''

        logger.info(f"{self}: save_results()")
        # timing
        end_time = time.time()

        # gather processor lists
        query_processors = []
        query_processors = query_processors + self.search.pre_query_processors + self.provider.query_processors
        result_processors = self.provider.result_processors
        # end if

        if self.update:
            try:
                result = Result.objects.filter(search_id=self.search, provider_id=self.provider.id)
            except ObjectDoesNotExist as err:
                self.search.status = "ERR_RESULT_NOT_FOUND"
                self.error(f'Update failed: results not found: {err}', save_results=False)
                return False
            if len(result) != 1:
                # to do: document
                self.search.status = "ERR_DUPLICATE_RESULT_OBJECTS"
                self.error(f"Update failed: found {len(result)} result objects, expected 1", save_results=False)
                return False
            # load the single result object now :\
            result = Result.objects.get(id=result[0].id)
            # add new flag
            for r in self.processed_results:
                r['new'] = True
            try:
                result.messages = result.messages + self.messages
                result.found = max(result.found, self.found)
                result.retrieved = result.retrieved + self.retrieved
                result.time = f'{result.time + (end_time - self.start_time):.1f}'
                result.json_results = result.json_results + self.processed_results
                result.query_processors = query_processors
                result.result_processors = result_processors
                result.status = 'UPDATED'
                logger.info(f"{self}: Result.save()")
                result.save()
            except Error as err:
                self.error(f'save_results() update failed: {err.args}, {err}', save_results=False)
                return False
            logger.info(f"{self}: Update: added {len(self.processed_results)} new items to result {result.id}")
            self.message(f"Retrieved {len(self.processed_results)} new results from: {result.searchprovider}")
            return True
        # end if

        try:
            logger.info(f"{self}: Result.create()")
            new_result = Result.objects.create(search_id=self.search, searchprovider=self.provider.name, provider_id=self.provider.id,
                                               query_string_to_provider=self.query_string_to_provider, query_to_provider=self.query_to_provider,
                                               query_processors=query_processors, result_processors=result_processors, messages=self.messages,
                                               status=self.status, found=self.found, retrieved=self.retrieved, time=f'{(end_time - self.start_time):.1f}',
                                               json_results=self.processed_results, owner=self.search.owner,result_processor_json_feedback=self.result_processor_json_feedback)
            new_result.save()
        except Error as err:
            self.error(f'save_results() failed: {err.args}, {err}', save_results=False)
        return True
