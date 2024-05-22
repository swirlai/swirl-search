'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ

import django
from django.core.exceptions import ObjectDoesNotExist

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

import logging
logger = logging.getLogger(__name__)

from operator import itemgetter

from swirl.mixers.utils import *
from swirl.mixers.mixer import Mixer

#############################################
#############################################

class StackNMixer(Mixer):

    type = "StackNMixer"

    def order(self):

        # sort the json_results by score
        ranked_results = sorted(sorted(self.all_results, key=itemgetter('searchprovider_rank')), key=itemgetter('swirl_score'), reverse=True)
        # organize results by provider
        dict_ranked_by_provider = {}
        for result in ranked_results:
            if 'searchprovider' in result:
                if not result['searchprovider'] in dict_ranked_by_provider:
                    dict_ranked_by_provider[result['searchprovider']] = []
                dict_ranked_by_provider[result['searchprovider']].append(result)
        # generate list of ranked providers
        list_top_each_provider = []
        for provider in dict_ranked_by_provider:
            list_top_each_provider.append(dict_ranked_by_provider[provider][0])
        list_ranked_providers = sorted(list_top_each_provider, key=itemgetter('swirl_score'), reverse=True)
        dict_ranked_providers = {}
        for provider in list_ranked_providers:
            dict_ranked_providers[provider['searchprovider']] = provider['swirl_score']

        if self.stack == 0:
            self.stack = int(int(self.results_requested)/len(dict_ranked_providers))

        # mix the results
        stacked_results = []
        position = 0
        last_len = 0
        while len(stacked_results) < self.results_needed:
            for searchprovider in dict_ranked_providers:
                for p in range(0,self.stack):
                    if len(dict_ranked_by_provider[searchprovider]) > position + p:
                        stacked_results.append(dict_ranked_by_provider[searchprovider][position + p])
                    # done if we now have enough
                    # w/o the below, we add one per source until exceeding that might be OK but should be deliberate
                    if len(stacked_results) == self.results_needed:
                        break
                else:
                    # out of results for that provider
                    pass
                # end for
                if len(stacked_results) == self.results_needed:
                    break
            # end for
            if len(stacked_results) == last_len:
                # no more results
                self.warning(f'results exhausted')
                break
            else:
                last_len = len(stacked_results)
            # end if
            position = position + self.stack
        # end while

        self.mixed_results = stacked_results

#############################################

class RoundRobinMixer(StackNMixer):
    type = "RoundRobinMixer"
    def order(self):
        self.stack = 1
        super().order()

class Stack1Mixer(StackNMixer):
    type = "Stack1Mixer"
    def order(self):
        self.stack = 1
        super().order()

class Stack2Mixer(StackNMixer):
    type = "Stack2Mixer"
    def order(self):
        self.stack = 2
        super().order()

class Stack3Mixer(StackNMixer):
    type = "Stack3Mixer"
    def order(self):
        self.stack = 3
        super().order()
