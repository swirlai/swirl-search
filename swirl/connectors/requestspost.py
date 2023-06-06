'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ

import django

import json

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

class RequestsPost(Requests):

    type = "RequestsPost"

    ########################################

    def validate_query(self, session=None):
        logger.info(f"{self}: https post request validate_query() returning true")
        try:
            json_object = json.loads(self.query_string_to_provider)
        except ValueError as e:
            logger.warning(f"{self}: https post request validate_query() failed JSON validation, passing anyways")
            return True
        return True

    def get_method(self):
        return 'post'

    def send_request(self, url, params=None, query=None, **kwargs):
        headers = dict({
            "Content-Type": "application/json"
        })
        headers.update(kwargs.get("headers", {}))
        kwargs['headers'] = headers
        ret = requests.post(url, params=params, json=query, **kwargs)
        return ret
