'''
@author:     Sid Probstein
@contact:    sid@swirl.today
@version:    SWIRL 1.3
'''

from sys import path
from os import environ

import django
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

from celery.utils.log import get_task_logger
from logging import DEBUG
logger = get_task_logger(__name__)

from natsort import natsorted

from swirl.models import Search, Result
from swirl.banner import SWIRL_BANNER_TEXT

########################################
########################################

class Mixer:

    type = "SWIRL Mixer"

    ########################################

    def __init__(self, search_id, results_requested, page, explain=False, provider=None):

        self.search_id = search_id
        self.results_requested = results_requested
        self.page = page
        self.results_needed = int(self.page) * int(self.results_requested)
        self.explain = explain
        self.provider = provider
        self.results = None
        self.search = None
        self.mix_wrapper = {}
        self.all_results = []
        self.mixed_results = None
        self.found = 0
        self.result_mixer = None
        self.status = "INIT"
        
        try:
            if self.provider:
                if type(self.provider) == str:
                    self.provider = int(self.provider)
                if type(self.provider) == int:
                    # security review for 1.7 - OK, filtered by search ID
                    self.results = Result.objects.filter(search_id=search_id,provider_id=self.provider)
                else:
                    self.warning(f"Unknown provider_list: {self.provider}")
                # end if
            else:
                # security review for 1.7 - OK, filtered by search ID
                self.results = Result.objects.filter(search_id=search_id)
            self.search = Search.objects.get(id=self.search_id)
        except ObjectDoesNotExist as err:
            self.error(f'Search does not exist: {search_id}')
            return

        self.result_mixer = self.type

        self.mix_wrapper = {}
        self.mix_wrapper['messages'] = [ SWIRL_BANNER_TEXT ]
        self.mix_wrapper['info'] = {}
        self.mix_wrapper['results'] = None

        result_messages = []
        rewrote_messages = []
        for result in self.results:
            for message in result.messages:
                if 'rewrote' in message:
                    rewrote_messages.append(message)
                else:
                    result_messages.append(message)
            self.mix_wrapper['info'][result.searchprovider] = {}
            self.mix_wrapper['info'][result.searchprovider]['found'] = result.found
            self.mix_wrapper['info'][result.searchprovider]['retrieved'] = result.retrieved
            self.mix_wrapper['info'][result.searchprovider]['filter_url'] = f'{settings.PROTOCOL}://{settings.HOSTNAME}:8000/swirl/results/?search_id={self.search.id}&provider={result.provider_id}'
            self.mix_wrapper['info'][result.searchprovider]['query_string_to_provider'] = result.query_string_to_provider
            self.mix_wrapper['info'][result.searchprovider]['query_to_provider'] = result.query_to_provider
            self.mix_wrapper['info'][result.searchprovider]['result_processor'] = result.result_processor
            self.mix_wrapper['info'][result.searchprovider]['search_time'] = result.time
        result_messages = natsorted(result_messages, reverse=True)
        rewrote_messages = natsorted(rewrote_messages)
        self.mix_wrapper['messages'] = self.mix_wrapper['messages'] + result_messages + rewrote_messages
        
        if self.search.messages:
            for message in self.search.messages:
                self.mix_wrapper['messages'].append(message)
        self.mix_wrapper['info']['search'] = {}
        if self.search.tags:
            self.mix_wrapper['info']['search']['tags'] = self.search.tags
        if self.search.searchprovider_list:
            self.mix_wrapper['info']['search']['searchprovider_list'] = self.search.searchprovider_list
        self.mix_wrapper['info']['search']['query_string'] = self.search.query_string
        self.mix_wrapper['info']['search']['query_string_processed'] = self.search.query_string_processed
        self.mix_wrapper['info']['search']['rescore_url'] = f'{settings.PROTOCOL}://{settings.HOSTNAME}:8000/swirl/search/?rescore={self.search.id}'
        self.mix_wrapper['info']['search']['rerun_url'] = f'{settings.PROTOCOL}://{settings.HOSTNAME}:8000/swirl/search/?rerun={self.search.id}'

        # join json_results
        for result in self.results:
            if type(result.json_results) == list:
                self.all_results = self.all_results + result.json_results

        self.found = len(self.all_results)

        self.mix_wrapper['info']['results'] = {}
        self.mix_wrapper['info']['results']['retrieved_total'] = self.found
        # set the order in the dict
        self.mix_wrapper['info']['results']['retrieved'] = 0
        self.mix_wrapper['info']['results']['federation_time'] = self.search.time

        self.status = 'READY'

    ########################################

    def __str__(self):
        return f"{self.type}_{self.search_id}"

    ########################################

    def error(self, message):
        logger.error(f'{self}: Error: {message}')
        self.status = "ERROR"

    def warning(self, message):
        logger.warning(f'{self}: Warning: {message}')
        self.status = "WARNING"

    ########################################

    def mix(self):

        '''
        Executes the workflow for a given mixer
        '''

        self.order()
        self.finalize()
        return self.mix_wrapper

    ########################################

    def order(self):

        '''
        Orders all_results into mixed_results
        Base class, intended to be overriden!
        '''

        self.mixed_results = self.all_results[(self.page-1)*self.results_requested:(self.page)*self.results_requested]

    ########################################

    def finalize(self):
        
        '''
        Trims mixed_results if needed, updates mix_wrapper with counts
        ''' 

        # check for overrun
        if (int(self.page)-1)*int(self.results_requested) > len(self.mixed_results):
            self.error("Page not found, results exhausted")
            self.mix_wrapper['results'] = []
            self.mix_wrapper['messages'].append(f"Results exhausted for {self.search_id}")
            return

        # number all mixed results
        result_number = 1
        for result in self.mixed_results:
            result['swirl_rank'] = result_number
            if not self.explain:
                if 'explain' in result:
                    del result['explain']
                if 'swirl_score' in result:
                    del result['swirl_score']
            result_number = result_number + 1
  
        # extract the page of mixed results
        self.mix_wrapper['results'] = self.mixed_results[(int(self.page)-1)*int(self.results_requested):int(self.results_needed)]
        self.mix_wrapper['info']['results']['retrieved'] = len(self.mix_wrapper['results'])

        # next page
        if self.found > int(self.results_needed):
            if self.result_mixer == self.search.result_mixer:
                self.mix_wrapper['info']['results']['next_page'] = f'{settings.PROTOCOL}://{settings.HOSTNAME}:8000/swirl/results/?search_id={self.search_id}&page={int(self.page)+1}'
            else:
                self.mix_wrapper['info']['results']['next_page'] = f'{settings.PROTOCOL}://{settings.HOSTNAME}:8000/swirl/results/?search_id={self.search_id}&result_mixer={self.result_mixer}&page={int(self.page)+1}'
            # end if
        if int(self.page) > 1:
            if self.result_mixer == self.search.result_mixer:
                self.mix_wrapper['info']['results']['prev_page'] = f'{settings.PROTOCOL}://{settings.HOSTNAME}:8000/swirl/results/?search_id={self.search_id}&page={int(self.page)-1}'
            else:
                self.mix_wrapper['info']['results']['prev_page'] = f'{settings.PROTOCOL}://{settings.HOSTNAME}:8000/swirl/results/?search_id={self.search_id}&result_mixer={self.result_mixer}&page={int(self.page)-1}'
            # end if

        # last message 
        if len(self.mix_wrapper['results']) > 2:
            if self.result_mixer:
                self.mix_wrapper['messages'].append(f"Results ordered by: {self.result_mixer}")
            else:
                self.mix_wrapper['messages'].append(f"Results ordered by: {self.type}")     



