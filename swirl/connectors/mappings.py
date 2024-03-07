'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ

import django
from swirl.swirl_common import RESULT_MAPPING_COMMANDS
from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

#############################################
#############################################

# types for use with mappings

QUERY_MAPPING_KEYS = [ 'DATE_SORT', 'RELEVANCY_SORT', 'PAGE' ]
RESPONSE_MAPPING_KEYS = [ 'FOUND', 'RETRIEVED', 'RESULTS', 'RESULT' ]
# RESULT_MAPPING_KEYS = [ 'BLOCK' ]
MAPPING_KEYS = QUERY_MAPPING_KEYS + RESPONSE_MAPPING_KEYS #+ RESULT_MAPPING_KEYS

QUERY_MAPPING_VARIABLES = [ 'RESULT_INDEX', 'RESULT_ZERO_INDEX', 'PAGE_INDEX' ]
RESULT_MAPPING_VARIABLES = []
MAPPING_VARIABLES = QUERY_MAPPING_VARIABLES + RESULT_MAPPING_VARIABLES

QUERY_MAPPING_COMMANDS = []
MAPPING_COMMANDS = RESULT_MAPPING_COMMANDS + QUERY_MAPPING_COMMANDS
