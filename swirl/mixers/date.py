'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ

import django
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

from operator import itemgetter

from django.urls import reverse

from swirl.mixers.mixer import Mixer
from swirl.mixers.utils import * 

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
            dated_results.append(result)

        self.mix_wrapper['messages'].append(f"[{datetime.now()}] DateMixer hid {unknown} results with date_published='unknown'")
        self.found = int(self.found) - int(unknown)
        self.mix_wrapper['info']['results']['retrieved_total'] = self.found

        self.mixed_results = sorted(dated_results, key=itemgetter('date_published'), reverse=True)

