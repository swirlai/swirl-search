'''
@author:     Sid Probstein
@contact:    sid@swirl.today
@version:    Swirl 1.x
'''

import django
from sys import path
from os import environ

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

from django.conf import settings

#############################################    

SWIRL_BANNER_TEXT = getattr(settings, 'SWIRL_BANNER_TEXT', '__S_W_I_R_L__1_._X_______________________________________________________________')

def create_mix_wrapper(result_sets):

    # accepts: result sets
    # returns: wrapper around the results

    mix_wrapper = {}
    mix_wrapper['messages'] = [ SWIRL_BANNER_TEXT ]
    mix_wrapper['info'] = {}
    for result_set in result_sets:
        for message in result_set.messages:
            mix_wrapper['messages'].append(message)
        mix_wrapper['info'][result_set.searchprovider] = {}
        mix_wrapper['info'][result_set.searchprovider]['found']=result_set.found
        mix_wrapper['info'][result_set.searchprovider]['retrieved']=result_set.retrieved
        mix_wrapper['info'][result_set.searchprovider]['query_to_provider']=result_set.query_to_provider
        mix_wrapper['info'][result_set.searchprovider]['result_processor']=result_set.result_processor
    mix_wrapper['results'] = None
    return mix_wrapper
