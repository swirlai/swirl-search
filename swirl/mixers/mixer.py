'''
@author:     Sid Probstein
@contact:    sid@swirl.today
@version:    Swirl 1.3
'''
import json
from urllib.parse import urlparse

from sys import path
from os import environ
from datetime import datetime

import django
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.contrib.auth.models import User

from swirl.utils import get_url_details, swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()
from django.conf import settings

import logging
logger = logging.getLogger(__name__)

from natsort import natsorted

from swirl.models import Search, Result
from swirl.banner import SWIRL_BANNER_TEXT

########################################
########################################

class Mixer:

    type = "SWIRL Mixer"

    ########################################

    def __init__(self, search_id, results_requested, page, explain=False, provider=None, mark_all_read=False, request=None):

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
        self.stack = 0
        self.result_mixer = None
        self.mark_all_read = mark_all_read
        self.status = "INIT"
        self.request = request

        try:
            if self.provider:
                if type(self.provider) == str:
                    self.provider = int(self.provider)
                if type(self.provider) == int:
                    # security review for 1.7 - OK, filtered by search ID
                    self.results = Result.objects.filter(search_id=search_id,provider_id=self.provider)
                if type(self.provider) == list:
                    self.results = Result.objects.filter(search_id=search_id,provider_id__in=self.provider)
                if type(self.provider) not in [str, int, list]:
                    self.warning(f"Unknown provider specification: {self.provider}")
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
        self.mix_wrapper['info']['results'] = {}
        self.mix_wrapper['results'] = None

        scheme, hostname, port = get_url_details(self.request)
        messages = []
        self.mix_wrapper['info']['results']['found_total'] = 0
        for result in self.results:
            for message in result.messages:
                messages.append(message)
            self.mix_wrapper['info'][result.searchprovider] = {}
            self.mix_wrapper['info'][result.searchprovider]['found'] = result.found
            self.mix_wrapper['info']['results']['found_total'] += result.found
            self.mix_wrapper['info'][result.searchprovider]['retrieved'] = result.retrieved
            self.mix_wrapper['info'][result.searchprovider]['filter_url'] = f'{scheme}://{hostname}:{port}/swirl/results/?search_id={self.search.id}&provider={result.provider_id}'
            self.mix_wrapper['info'][result.searchprovider]['query_string_to_provider'] = result.query_string_to_provider
            # TODO: Make optional include self.mix_wrapper['info'][result.searchprovider]['result_processor_json_feedback'] = result.result_processor_json_feedback
            self.mix_wrapper['info'][result.searchprovider]['query_to_provider'] = result.query_to_provider
            self.mix_wrapper['info'][result.searchprovider]['query_processors'] = result.query_processors
            self.mix_wrapper['info'][result.searchprovider]['result_processors'] = result.result_processors
            # if result.json_results:
            #     if 'result_block' in result.json_results[0]:
            #         self.mix_wrapper['info'][result.searchprovider]['result_block'] = result.json_results[0]['result_block']
            self.mix_wrapper['info'][result.searchprovider]['search_time'] = result.time

        if self.search.messages:
            for message in self.search.messages:
                messages.append(message)

        self.mix_wrapper['messages'] = self.mix_wrapper['messages'] + natsorted(messages) #, reverse=True)

        self.mix_wrapper['info']['search'] = {}
        self.mix_wrapper['info']['search']['id'] = self.search_id

        if self.search.tags:
            self.mix_wrapper['info']['search']['tags'] = self.search.tags
        if self.search.searchprovider_list:
            self.mix_wrapper['info']['search']['searchprovider_list'] = self.search.searchprovider_list
        self.mix_wrapper['info']['search']['query_string'] = self.search.query_string
        self.mix_wrapper['info']['search']['query_string_processed'] = self.search.query_string_processed
        self.mix_wrapper['info']['search']['rerun_url'] = f'{scheme}://{hostname}:{port}/swirl/search/?rerun={self.search.id}'

        # join json_results
        for result in self.results:
            if type(result.json_results) == list:
                self.all_results = self.all_results + result.json_results

        self.found = len(self.all_results)

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
            self.mix_wrapper['messages'].append(f"[{datetime.now()}] Results exhausted for {self.search_id}")
            return

        # number all result blocks
        mixed_result_number = 1
        mixed_results = []
        block_dict = {}
        for result in self.mixed_results:
            if not self.explain:
                if 'explain' in result:
                    del result['explain']
                if 'swirl_score' in result:
                    del result['swirl_score']
            # end if
            if 'result_block' in result:
                block_name = result['result_block']
                del result['result_block']
                if block_name in block_dict:
                    block_count = block_count + 1
                    result['swirl_rank'] = block_count
                    block_dict[block_name].append(result)
                else:
                    block_count = 1
                    result['swirl_rank'] = block_count
                    block_dict[block_name] = [result]
                # end if
                peek_search_provider = result.get('searchprovider', None)
                if peek_search_provider and self.mix_wrapper['info'].get(peek_search_provider, None):
                    del self.mix_wrapper['info'][result['searchprovider']]
                # end if
            else:
                result['swirl_rank'] = mixed_result_number
                mixed_results.append(result)
                mixed_result_number = mixed_result_number + 1
            # end if
        # end for

        # block results
        self.mix_wrapper['info']['results']['result_blocks'] = []

        # default block, if specified in settings
        if settings.SWIRL_DEFAULT_RESULT_BLOCK:
            self.mix_wrapper['info']['results']['result_blocks'].append(settings.SWIRL_DEFAULT_RESULT_BLOCK)
            self.mix_wrapper[settings.SWIRL_DEFAULT_RESULT_BLOCK] = []

        # blocks specified by provider(s)
        moved_to_block = 0
        for block in block_dict:
            self.mix_wrapper[block] = block_dict[block]
            moved_to_block = moved_to_block + len(block_dict[block])
            if not block in self.mix_wrapper['info']['results']['result_blocks']:
                self.mix_wrapper['info']['results']['result_blocks'].append(block)
        if moved_to_block > 0:
            self.mix_wrapper['info']['results']['retrieved_total'] = self.found - moved_to_block
            if self.mix_wrapper['info']['results']['retrieved_total'] < 0:
                self.warning("Block count exceeds result count")

        # extract the page of mixed results
        self.mixed_results = mixed_results
        self.mix_wrapper['results'] = self.mixed_results[(int(self.page)-1)*int(self.results_requested):int(self.results_needed)]
        self.mix_wrapper['info']['results']['retrieved'] = len(self.mix_wrapper['results'])

        scheme, hostname, port = get_url_details(self.request)

        # next page
        if self.found > int(self.results_needed):
            if self.result_mixer == self.search.result_mixer:
                self.mix_wrapper['info']['results']['next_page'] = f'{scheme}://{hostname}:{port}/swirl/results/?search_id={self.search_id}&page={int(self.page)+1}'
            else:
                self.mix_wrapper['info']['results']['next_page'] = f'{scheme}://{hostname}:{port}/swirl/results/?search_id={self.search_id}&result_mixer={self.result_mixer}&page={int(self.page)+1}'
            # end if
        if int(self.page) > 1:
            if self.result_mixer == self.search.result_mixer:
                self.mix_wrapper['info']['results']['prev_page'] = f'{scheme}://{hostname}:{port}/swirl/results/?search_id={self.search_id}&page={int(self.page)-1}'
            else:
                self.mix_wrapper['info']['results']['prev_page'] = f'{scheme}://{hostname}:{port}/swirl/results/?search_id={self.search_id}&result_mixer={self.result_mixer}&page={int(self.page)-1}'
            # end if

        # last message
        if len(self.mix_wrapper['results']) > 2:
            if self.result_mixer:
                self.mix_wrapper['messages'].append(f"[{datetime.now()}] Results ordered by: {self.result_mixer}")
            else:
                self.mix_wrapper['messages'].append(f"[{datetime.now()}] Results ordered by: {self.type}")

        # log info
        user = User.objects.get(id=self.search.owner.id)
        logger.info(f"{user} results {self.search_id} {self.type} {self.mix_wrapper['info']['results']['retrieved_total']}")