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

from django.conf import settings

from celery.utils.log import get_task_logger
from logging import DEBUG, INFO, WARNING
logger = get_task_logger(__name__)

from swirl.connectors.mappings import *
from swirl.connectors.connector import Connector

from datetime import datetime

import openai

########################################
########################################

class ChatGPT(Connector):

    type = "ChatGPT"

    def execute_search(self):

        logger.info(f"{self}: execute_search()")
        
        # to do: move to base class
        if self.provider.credentials:
            openai.api_key = self.provider.credentials
        else:
            if settings.OPENAI_API_KEY:
                openai.api_key = settings.OPENAI_API_KEY

        completions = openai.Completion.create(
            engine="text-davinci-002",
            prompt=self.query_to_provider,
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=0.5,
        )

        message = completions.choices[0].text     
        logger.info(f"{self}: {message}")

        # to do: review this
        self.found = 1
        self.retrieved = 1
        self.response = message

    ########################################

    def normalize_response(self):
        
        logger.info(f"{self}: normalize_response()")

        self.results = [
                {
                'title': f'{self.query_to_provider}',
                'body': f'{self.response}',
                'author': 'CHATGPT',
                'date_published': str(datetime.now())
            }
        ]


