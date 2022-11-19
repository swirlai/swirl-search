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

from operator import itemgetter

from swirl.mixers.mixer import Mixer
from swirl.mixers.utils import * 

#############################################    

class RelevancyMixer(Mixer):

    type = 'RelevancyMixer'

    def order(self):

        # sort by score
        self.mixed_results = sorted(sorted(sorted(self.all_results, key=itemgetter('searchprovider_rank')), key=itemgetter('date_published'), reverse=True), key=itemgetter('swirl_score'), reverse=True)


