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

from celery.utils.log import get_task_logger
from logging import DEBUG
logger = get_task_logger(__name__)

from swirl.connectors.connector import Connector
from swirl.processors.utils import get_tag

from transformers import AutoModel, AutoTokenizer
import torch

########################################

class VectorDBConnector(Connector):

    type = "SWIRL Vector DB Connector"

    ########################################

    def __init__(self, provider_id, search_id, update, request_id=''):
        self.vector_to_provider = None
        return super().__init__(provider_id, search_id, update, request_id)

    ########################################

    def construct_query(self):
        logger.debug(f"{self}: construct_query()")

        if not self.query_string_to_provider:
            self.warning("No query_string_to_provider!")
            return False

        self.query_to_provider = self.query_string_to_provider

        model_name = get_tag('model', self.provider.tags)
        if not model_name:
            self.error("No model defined in SearchProvider")
            return False

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)

        inputs = tokenizer(self.query_string_to_provider, return_tensors="pt", padding=True, truncation=True)
        with torch.no_grad():
            outputs = model(**inputs)
        # Mean pooling
        embeddings = outputs.last_hidden_state.mean(dim=1)

        self.vector_to_provider = embeddings[0].numpy().tolist()
        
        return True
