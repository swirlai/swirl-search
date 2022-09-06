'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

import django
from django.core.exceptions import ObjectDoesNotExist

from sys import path
from os import environ
from .utils import * 

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

from swirl.models import Search, Result

import logging as logger
import datetime

from operator import itemgetter

from django.urls import reverse

from .Mixer import Mixer

#############################################    
#############################################    

class DateMixer(Mixer):

    type = 'DateMixer'

    def order(self):

        # remove and count date_published == unknown
        unknown = 0
        dated_results = []
        for result in self.all_results:
            if result['date_published'] == 'unknown':
                unknown = unknown + 1
                continue
            if not self.explain:
                del result['explain']
            dated_results.append(result)

        self.mix_wrapper['messages'].append(f"DateMixer hid {unknown} results with date_published='unknown'")
        self.found = int(self.found) - int(unknown)
        self.mix_wrapper['info']['results']['retrieved_total'] = self.found

        self.mixed_results = sorted(dated_results, key=itemgetter('date_published'), reverse=True)

