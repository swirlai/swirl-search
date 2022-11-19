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
from logging import DEBUG
logger = get_task_logger(__name__)

########################################

class Processor:

    type = "SWIRL Processor"

    ########################################

    def __init__(self):
        
        self.status = "INIT"

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
        Verify input; tbd by derived classes
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

    def __init__(self, query_string, query_mappings):

        self.query_string = query_string
        self.query_mappings = query_mappings

    ########################################

    def validate(self):

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
        Executes the workflow for a query processor; tbd by derived classes
        '''

        return self.query_string

########################################
########################################

class ResultProcessor(Processor):

    type = "ResultProcessor"

    ########################################

    def __init__(self, results, provider, query_string):

        self.results = results
        self.provider = provider
        self.query_string = query_string
        self.processed_results = None

    ########################################

    def validate(self):

        '''
        Verify that there are results
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
        Executes the workflow for a result processor; tbd by derived classes
        '''

        return self.processed_results
        
########################################
########################################

from swirl.models import Search, Result

class PostResultProcessor(Processor):

    type = "PostResultProcessor"

    ########################################

    def __init__(self, search_id):

        self.search_id = search_id
        self.search = None
        self.results_updated = -1

        if Search.objects.filter(id=search_id).exists():
            self.search = Search.objects.get(id=search_id)
            if self.search.status == 'POST_RESULT_PROCESSING' or self.search.status == 'RESCORING':
                self.results = Result.objects.filter(search_id=search_id)
            else:
                logger.warning(f"search.status {self.search.status}, this processor requires: status == 'POST_RESULT_PROCESSING'")
                return 0
            # end if
        else:
            self.error(f"search not found")
            return 0
        # end if

    ########################################

    def __str__(self):
        return f"{self.type}_{self.search_id}"

    ########################################

    def validate(self):

        '''
        Verify there is at least one result to process
        '''

        if self.results:
            if len(self.results) == 0:
                return False

        return True

    ########################################

    def process(self):

        '''
        Executes the workflow for a result processor; tbd by derived classes
        '''

        return self.results_updated
        