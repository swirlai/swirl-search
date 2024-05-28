'''
@author:     Sid Probstein
@contact:    sid@swirl.today
@version:    Swirl 1.3
'''

from sys import path
from os import environ
import time
import copy

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
from swirl.processors.utils import result_processor_feedback_merge_records
from swirl.processors.transform_query_processor_utils import get_query_processor_or_transform

SWIRL_RP_SKIP_TAG = 'SW_RESULT_PROCESSOR_SKIP'

########################################

class Connector:

    type = "SWIRL Connector"

    ########################################

    def __init__(self, provider_id, search_id, update, request_id=''):

        self.provider_id = provider_id
        self.search_id = search_id
        self.update = update
        self.status = 'INIT'
        self.auth = True
        self.provider = None
        self.search = None
        self.query_string_to_provider = ""
        self.result_processor_json_feedback = {}
        self.query_to_provider = ""
        self.query_mappings = {}
        self.response_mappings = {}
        self.result_mappings = {}
        self.response = []
        self.found = -1
        self.retrieved = -1
        self.results = []
        self.processed_results = []
        self.messages = []
        self.start_time = None
        self.search_user = None
        self.request_id = request_id
        self._swirl_timeout = getattr(settings,'SWIRL_TIMEOUT')

        # get the provider and query
        try:
            self.provider = SearchProvider.objects.get(id=self.provider_id)
            self.search = Search.objects.get(id=self.search_id)
        except ObjectDoesNotExist as err:
            self.error(f'ObjectDoesNotExist: {err}')
            return

        try:
            self.search_user = User.objects.get(id=self.search.owner.id)
        except ObjectDoesNotExist as err:
            logger.warning("unable to find search user, no auth check")

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
                    if not self.auth:
                        self.status = 'NO_AUTH'
                        return False
                    self.execute_search(session)
                    if self.status not in ['FEDERATING', 'READY']:
                        self.error(f"execute_search() failed, status {self.status}")
                        return False
                    if self.status in ['FEDERATING', 'READY']:
                        self.normalize_response()
                    if self.status not in ['FEDERATING', 'READY']:
                        self.error(f"normalize_response() failed, status {self.status}")
                        return False
                    else:
                        self.process_results()
                    if self.status == 'READY':
                        res = self.save_results()
                        if res:
                            return res
                        else:
                            return False
                    else:
                        self.error(f"process_results() failed, status {self.status}")
                        return False
                else:
                    self.status = 'ERR_VALIDATE_QUERY'
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

        logger.debug(f"{self}: process_query()")
        processor_list = []
        processor_list = self.provider.query_processors

        if not processor_list:
            self.query_string_to_provider = self.search.query_string_processed
            return

        query_temp = self.search.query_string_processed
        for processor in processor_list:
            logger.debug(f"{self}: invoking query processor: {processor}")
            try:
                processed_query = get_query_processor_or_transform(processor, query_temp, self.provider.query_mappings, self.provider.tags, self.search_user).process()
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

        logger.debug(f"{self}: construct_query()")
        self.query_to_provider = self.query_string_to_provider
        return

    ########################################

    def validate_query(self, session=None):

        '''
        Validate the query_to_provider, and return True or False
        '''

        logger.debug(f"{self}: validate_query()")
        if self.query_to_provider == "":
            self.error("query_to_provider is blank or missing")
            return False
        return True

    ########################################

    def execute_search(self, session=None):

        '''
        Connect to, query and save the response from this provider
        '''

        logger.debug(f"{self}: execute_search()")
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

        if not self.response:
            # no results, not an error
            self.retrieved = 0
            self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
            self.status = 'READY'
            return
        if len(self.response) == 0:
            # no results, not an error
            self.retrieved = 0
            self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
            self.status = 'READY'
            return
        if isinstance(self.response, str):
            if len(self.response) > self.provider.results_per_query:
                self.response = self.response[:self.provider.results_per_query]
                self.retrieved = self.provider.results_per_query
        elif isinstance(self.response, (list, tuple)):
            if len(self.response) > self.provider.results_per_query:
                self.response = self.response[:self.provider.results_per_query]
                self.retrieved = len(self.response)
        else:
            self.error("self.response is neither a string nor a list/tuple.")
            return

        self.results = self.response
        return

    ########################################
    def _get_skip_processors_from_tags(self):
        """
        Find all of the skip tag and collect the values and return them in a set
        """

        if not (self.search and self.search.tags):
            return []

        skip_set = set()
        for tag in self.search.tags:
            parts = tag.split(':')
            if len(parts) != 2:
                logger.warning(f"{tag} invalid format")
                continue
            tag_key, tag_value = parts
            if tag_key == SWIRL_RP_SKIP_TAG:
                skip_set.add(tag_value.strip())
        return skip_set

    ########################################

    def process_results(self):

        '''
        Process the json results through the specified result processor for the provider, updating processed_results
        Each processor is expected to MODIFY self.results and RETURN the number of records modified
        '''

        logger.debug(f"{self}: process_results()")

        if self.found == 0:
            return

        # process results
        retrieved = 0
        if self.results:
            retrieved = len(self.results)
        self.message(f"Retrieved {retrieved} of {self.found} results from: {self.provider.name}")

        processor_list = []
        processor_list = self.provider.result_processors

        if not processor_list:
            self.processed_results = self.results
            self.status = 'READY'
            return

        processors_to_skip = self._get_skip_processors_from_tags()

        for processor in processor_list:
            if processor in processors_to_skip:
                logger.debug(f"{self}: skipping processor: process results {processor} becasue it was in a skip tag of the search")
                continue
            logger.debug(f"{self}: invoking processor: process results {processor}")
            last_results = copy.deepcopy(self.results)
            try:
                proc = alloc_processor(processor=processor)(self.results, self.provider, self.query_string_to_provider, request_id=self.request_id,
                                                            result_processor_json_feedback=self.result_processor_json_feedback)
                modified = proc.process()
                self.results = proc.get_results()
                logger.debug(f'provider : {self.provider.name} processor: {processor} modified : {modified}')
                ## Check if this processor generated feed back and if so, remember it and merge it in to the exsiting
                if self.results and 'result_processor_feedback' in self.results[-1]:
                    self.result_processor_json_feedback =  self.results.pop(-1)
            except (NameError, TypeError, ValueError) as err:
                self.error(f'{processor}: {err.args}, {err}')
                return
            if modified < 0:
                # if len(last_results) + modified != len(self.results):
                #     self.warning(f"{processor} reported {modified} modified results, but returned {len(self.results)}!!")
                self.message(f"{processor} deleted {-1*modified} results from: {self.provider.name}")
            else:
                # if len(self.results) != len(last_results):
                #     self.warning(f"{processor} updated {modified} results but returned {len(self.results)}!!")
                self.message(f"{processor} updated {modified} results from: {self.provider.name}")
            del last_results
        # end for
        self.processed_results = self.results if self.results else []
        self.status = 'READY'
        self.retrieved = len(self.processed_results) # adjust retrieved in case processing effected the size of the list.

        return

    ########################################

    def save_results(self):

        '''
        Store the transformed results as a Result object in the database, linked to the search_id
        '''

        logger.debug(f"{self}: save_results()")
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
                logger.debug(f"{self}: Result.save()")
                result.save()
            except Error as err:
                self.error(f'save_results() update failed: {err.args}, {err}', save_results=False)
                return False
            logger.debug(f"{self}: Update: added {len(self.processed_results)} new items to result {result.id}")
            self.message(f"Retrieved {len(self.processed_results)} new results from: {result.searchprovider}")
            return result.retrieved
        # end if

        try:
            logger.debug(f"{self}: Result.create()")
            new_result = Result.objects.create(search_id=self.search, searchprovider=self.provider.name, provider_id=self.provider.id,
                                               query_string_to_provider=self.query_string_to_provider, query_to_provider=self.query_to_provider,
                                               query_processors=query_processors, result_processors=result_processors, messages=self.messages,
                                               status=self.status, found=self.found, retrieved=self.retrieved, time=f'{(end_time - self.start_time):.1f}',
                                               json_results=self.processed_results, owner=self.search.owner,result_processor_json_feedback=self.result_processor_json_feedback)
            new_result.save()
        except Error as err:
            self.error(f'save_results() failed: {err.args}, {err}', save_results=False)
            # Log everything except for the json_message
            logger.error( "failed to save "
                f"search_id={self.search}, "
                f"searchprovider={self.provider.name}, "
                f"provider_id={self.provider.id}, "
                f"query_string_to_provider={self.query_string_to_provider}, "
                f"query_to_provider={self.query_to_provider}, "
                f"query_processors={query_processors}, "
                f"result_processors={result_processors}, "
                f"messages={self.messages}, "
                f"status={self.status}, "
                f"found={self.found}, "
                f"retrieved={self.retrieved}, "
                f"time={(end_time - self.start_time):.1f}, "
                f"owner={self.search.owner}, "
                f"result_processor_json_feedback={self.result_processor_json_feedback}"
            )
        return self.retrieved
