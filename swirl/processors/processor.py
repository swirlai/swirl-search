'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ

import django

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

########################################

class Processor:

    type = "SWIRL Processor"

    ########################################

    def __init__(self, request_id=''):

        self.status = "INIT"
        self.request_id = request_id

    ########################################

    def __str__(self):
        return f"{self.type}"

    ########################################

    def error(self, message):
        logger.error(f'{self}: Error: {message}')
        self.status = "ERROR"

    def warning(self, message):
        logger.warning(f'{self}: Warning: {message}')
        self.status = "WARNING"

    ########################################

    def validate(self):

        '''
        Verify input; TBD by derived classes
        '''

        return True

    ########################################

    def process(self):

        '''
        Executes the workflow for a given processor; tbd by derived classes
        '''

        return None

########################################
########################################

class QueryProcessor(Processor):

    type = "QueryProcessor"

    ########################################

    def __init__(self, query_string, query_mappings, tags):

        self.query_string = query_string
        self.query_mappings = query_mappings
        if type(tags) == str:
            self.tags = [tags]
        else:
            self.tags = tags

    ########################################

    def validate(self):

        '''
        Validate the query
        Returns: boolean
        '''

        if not type(self.query_string) == str:
            self.error("self.query_string was not a str")
            return False

        if len(self.query_string) == 0:
            self.error("self.query_string was blank")
            return False

        self.status = "VALID"
        return True

    ########################################

    def process(self):

        '''
        Executes the workflow for a query processor; TBD by derived classes
        Returns: transformed query_string
        '''

        return self.query_string

########################################
########################################

class ResultProcessor(Processor):

    type = "ResultProcessor"

    ########################################

    def __init__(self, results, provider, query_string, request_id='', **kwargs):

        self.results = results
        self.provider = provider
        self.query_string = query_string
        self.provider_tags = provider.tags
        self.modified = 0
        self.processed_results = None
        self.request_id = request_id
        # process additional keyword arguments
        for key, value in kwargs.items():
            setattr(self, key, value)

    ########################################

    def validate(self):

        '''
        Verify that there are results
        Returns: boolean
        '''

        if not type(self.results) == list:
            self.error("self.results is not list")
            return False

        if not self.results:
            self.error("self.results was empty")
            return False

        return True

    ########################################

    def process(self):

        '''
        Executes the workflow for a result processor; TBD by derived classes
        Returns: # of results modified
        '''

        return self.modified

    ########################################

    def get_results(self):
        return self.processed_results

########################################
########################################

from swirl.models import Search, Result

class PostResultProcessor(Processor):

    type = "PostResultProcessor"

    ########################################

    def __init__(self, search_id, request_id='', should_get_results=False, rag_query_items=False):

        self.search_id = search_id
        self.search = None
        self.results_updated = -1
        self.result_count = -1
        self.request_id = request_id
        self.rag_query_items = rag_query_items

        # security review for 1.7 - OK, filtered by search ID
        if not Search.objects.filter(id=search_id).exists():
            self.error(f"Search not found {search_id}")
            return 0
        self.search = Search.objects.get(id=search_id)
        if self.search.status == 'POST_RESULT_PROCESSING' or self.search.status == 'RESCORING' or should_get_results:
            # security review for 1.7 - OK, filtered by search ID
            self.results = Result.objects.filter(search_id=search_id)
            # count the number retrieved across all result sets
            self.result_count = 0
            for result in self.results:
                self.result_count = self.result_count + result.retrieved
        else:
            logger.warning(f"search.status {self.search.status}, this processor requires: status == 'POST_RESULT_PROCESSING'")
            return 0
        # end if

    ########################################

    def __str__(self):
        return f"{self.type}_{self.search_id}"

    ########################################

    def validate(self):

        '''
        Verify there is at least one result to process
        Returns: boolean
        '''

        if self.results:
            if len(self.results) == 0:
                return False

        return True

    ########################################

    def process(self):

        '''
        Executes the workflow for a result processor; TBD by derived classes
        Returns: number of results updated
        '''

        return self.results_updated
