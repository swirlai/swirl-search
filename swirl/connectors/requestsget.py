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

import requests

from swirl.connectors.mappings import *
from swirl.connectors.utils import bind_query_mappings

from swirl.connectors.requests import Requests

########################################
########################################

class RequestsGet(Requests):

    type = "RequestsGet"

    def __init__(self, provider_id, search_id, update, request_id=''):
        super().__init__(provider_id, search_id, update, request_id)

    ########################################

    def get_method(self):
        return 'get'

    def send_request(self, url, params=None, query=None, **kwargs):
        return requests.get(url, params=params, **kwargs)
