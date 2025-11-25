'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ

import django

from swirl.utils import swirl_setdir
path.append(swirl_setdir())  # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

from django.conf import settings  # still available if needed later

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.connectors.connector import Connector

from datetime import datetime

from swirl.openai.openai import AI_QUERY_USE, OpenAIClient

########################################
########################################

MODEL_DEFAULT_SYSTEM_GUIDE = (
    "You are a helpful assistant, keeping your response brief and to the point."
)


class GenAI(Connector):

    type = "GenAIGPT"

    def __init__(self, provider_id, search_id, update, request_id=''):
        self.system_guide = MODEL_DEFAULT_SYSTEM_GUIDE
        super().__init__(provider_id, search_id, update, request_id)

    def execute_search(self, session=None):

        logger.debug(f"{self}: execute_search()")
        client = None
        try:
            # If provider.credentials is set, it overrides the default key
            client = OpenAIClient(usage=AI_QUERY_USE, key=self.provider.credentials)
        except ValueError as valErr:
            logger.error(f"err {valErr} while initializing OpenAI client")
            self.status = "ERR_NO_CREDENTIALS"
            return

        prompted_query = ""
        if self.query_to_provider.endswith('?'):
            prompted_query = self.query_to_provider
        else:
            if 'PROMPT' in self.query_mappings:
                prompted_query = self.query_mappings['PROMPT'].format(
                    query_to_provider=self.query_to_provider
                )
            else:
                prompted_query = self.query_to_provider
                self.warning('PROMPT not found in query_mappings!')

        if 'CHAT_QUERY_REWRITE_GUIDE' in self.query_mappings:
            self.system_guide = self.query_mappings['CHAT_QUERY_REWRITE_GUIDE'].format(
                query_to_provider=self.query_to_provider
            )

        if not prompted_query:
            self.found = 0
            self.retrieved = 0
            self.response = []
            self.status = "ERR_PROMPT_FAILED"
            return

        model_name = client.get_model()
        logger.info(
            "GenAI completion system guide: %s model: %s query_to_provider: %s",
            self.system_guide,
            model_name,
            self.query_to_provider,
        )

        self.query_to_provider = prompted_query
        completions = client.openai_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": self.system_guide},
                {"role": "user", "content": self.query_to_provider},
            ],
        )
        message = completions.choices[0].message.content
        self.found = 1
        self.retrieved = 1
        msg = message.replace("\n\n", "")
        self.response = [
            {
                'title': self.query_string_to_provider,
                'body': f'{msg}',
                'author': 'GenAI',
                'date_published': str(datetime.now()),
                'model': model_name,
            }
        ]

        return
