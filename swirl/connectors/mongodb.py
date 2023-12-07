'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import json

import django

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

from celery.utils.log import get_task_logger
from logging import DEBUG
logger = get_task_logger(__name__)
# logger.setLevel(DEBUG)

from swirl.connectors.db_connector import DBConnector
from swirl.connectors.utils import bind_query_mappings

########################################
########################################

class MongoDB(DBConnector):

    type = "MongoDB"

    ########################################

    def construct_query(self):

        logger.debug(f"{self}: construct_query()")

        self.count_query = None

        query_to_provider = bind_query_mappings(self.provider.query_template, self.provider.query_mappings)
        if '{query_string}' in query_to_provider:
            # add escaped \\" around each word so the search is an "All" instead of "Any" :\
            mongo_query = ''
            for term in self.query_string_to_provider.split():
                if term.startswith('-'):
                    mongo_query = mongo_query + term + ' '
                else:
                    mongo_query = mongo_query + '\\"' + term + '\\"' + ' '
            query_to_provider = query_to_provider.replace('{query_string}', mongo_query.strip())

        try:
            # convert string to json
            query_to_provider = query_to_provider.replace("'",'"')
            self.query_to_provider = json.loads(query_to_provider)
        except Exception as err:
            self.error(f"Error converting query to JSON: {err}")
            self.status = 'ERR'

        return

    ########################################

    def validate_query(self, session=None):

        logger.debug(f"{self}: validate_query()")
        if self.status == 'ERR':
            return False
        
        return True

    ########################################

    def execute_search(self, session=None):

        logger.debug(f"{self}: execute_search()")

        # connect to the db
        config = self.provider.url.split(':')
        if len(config) != 2:
            self.error(f'Invalid configuration: {config}')
            self.status = 'ERR_INVALID_CONFIG'
            return

        mongo_uri = self.provider.credentials
        database_name = config[0]
        collection_name = config[1]

        try:
            client = MongoClient(mongo_uri, server_api=ServerApi('1'))
            db = client[database_name]
            collection = db[collection_name]
            # warning: query to provider is a json object
            found = collection.count_documents(self.query_to_provider)

        except Exception as err:
            self.error(f"{err} connecting to {self.type}")
            return
 
        logger.debug(f"{self}: count {found}")

        if found == 0:
            self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
            self.status = 'READY'
            self.found = 0
            self.retrieved = 0
            return
        # end if
 
        # now run the actual query
        try:
            if self.search.sort.lower() == 'date':
                if 'DATE_SORT' in self.query_mappings:
                    results = collection.find(self.query_to_provider).sort(self.query_mappings['DATE_SORT'], -1).limit(self.provider.results_per_query)
                else:
                    self.warning("Date sort requested, but `DATE_SORT` missing from `query_mappings`, ignoring")
                    results = collection.find(self.query_to_provider).limit(self.provider.results_per_query)
            else:
                results = collection.find(self.query_to_provider).limit(self.provider.results_per_query)
            self.response = list(results)
        except Exception as err:
            self.error(f"{err} connecting to {self.type}")
        finally:
            client.close()

        self.found = found
        self.retrieved = len(self.response)
        return

