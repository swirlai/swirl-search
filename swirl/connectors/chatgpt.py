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

    def execute_search(self, session=None):

        logger.info(f"{self}: execute_search()")
        
        if self.provider.credentials:
            openai.api_key = self.provider.credentials
        else:
            if getattr(settings, 'OPENAI_API_KEY', None):
                openai.api_key = settings.OPENAI_API_KEY
            else:
                self.status = "ERR_NO_CREDENTIALS"
                return 

        prompted_query = ""
        if self.query_to_provider.endswith('?'):
            prompted_query = self.query_to_provider
        else:
            if 'PROMPT' in self.query_mappings:
                prompted_query = self.query_mappings['PROMPT'].format(query_to_provider=self.query_to_provider)
            else:
                prompted_query = self.query_to_provider
                self.warning(f'PROMPT not found in query_mappings!')

        if not prompted_query:
            self.found = 0
            self.retrieved = 0
            self.response = []
            self.status = "ERR_PROMPT_FAILED"
            return 

        self.query_to_provider = prompted_query

        completions = openai.Completion.create(
            engine="text-davinci-002",
            prompt=self.query_to_provider,
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=0.5,
        )

        message = completions.choices[0].text

        self.found = 1
        self.retrieved = 1
        self.response = message.replace("\n\n", "")

        return

    ########################################

    def normalize_response(self):
        
        logger.info(f"{self}: normalize_response()")

        self.results = [
                {
                'title': self.query_string_to_provider,
                'body': f'{self.response}',
                'author': 'CHATGPT',
                'date_published': str(datetime.now())
            }
        ]

        return

