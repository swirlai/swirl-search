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

from swirl.ai_provider.ai_provider import AI_QUERY_USE
from swirl.ai_provider.swirl_ai_client_factory import SwirlAIClientFactory


MODEL_3 = "gpt-3.5-turbo"
MODEL_4 = "gpt-4"

MODEL = MODEL_3

########################################
########################################

MODEL_DEFAULT_SYSTEM_GUIDE = "You are a helpful assistant, keeping your response brief and to the point."

class ChatGPT(Connector):

    type = "ChatGPT"

    def __init__(self, provider_id, search_id, update, request_id=''):
        self.system_guide = MODEL_DEFAULT_SYSTEM_GUIDE
        super().__init__(provider_id, search_id, update, request_id)


    def execute_search(self, session=None):

        logger.debug(f"{self}: execute_search()")
        client = None
        if self.provider.credentials:
            client = SwirlAIClientFactory.alloc_ai_client(usage=AI_QUERY_USE)
        else:
            if getattr(settings, 'OPENAI_API_KEY', None):
                client = SwirlAIClientFactory.alloc_ai_client(usage=AI_QUERY_USE)
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

        if 'CHAT_QUERY_REWRITE_GUIDE' in self.query_mappings:
            self.system_guide = self.query_mappings['CHAT_QUERY_REWRITE_GUIDE'].format(query_to_provider=self.query_to_provider)

        if not prompted_query:
            self.found = 0
            self.retrieved = 0
            self.response = []
            self.status = "ERR_PROMPT_FAILED"
            return
        logger.info(f'CGPT completion system guide:{self.system_guide} query to provider : {self.query_to_provider}')
        self.query_to_provider = prompted_query
        message = client.get_completion(
            system_text=self.system_guide,
            prompt=self.query_to_provider,
            temperature=0,
        )
        self.found = 1
        self.retrieved = 1
        self.response = message.replace("\n\n", "")

        return

    ########################################

    def normalize_response(self):

        logger.debug(f"{self}: normalize_response()")

        self.results = [
                {
                'title': self.query_string_to_provider,
                'body': f'{self.response}',
                'author': 'CHATGPT',
                'date_published': str(datetime.now())
            }
        ]

        return
