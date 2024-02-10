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
logger = get_task_logger(__name__)

from swirl.connectors.vdb_connector import VectorDBConnector
from pinecone import Pinecone

class PineconeDB(VectorDBConnector):

    type = "PineconeDB"

    ########################################

    def execute_search(self, session=None):

        logger.debug(f"{self}: execute_search()")

        credentials = self.provider.credentials
        index_name = self.provider.url
        
        if not self.vector_to_provider:
            self.status = 'ERR'
            self.error(f"No vector for query: {self.query_string_to_provider}")
            return 

        try:
            pc = Pinecone(api_key=credentials)
            index = pc.Index(index_name)
            response = index.query(vector=self.vector_to_provider,top_k=self.provider.results_per_query, include_metadata=True, include_values=False)
        except Exception as err:
            self.error(f"{err} connecting to {self.type}")
            self.status = 'ERR'
            return

        retrieved = 0
        result_list = []
        response = response.to_dict()
        if 'matches' in response:
            if len(response['matches']) > 0:
                for match in response['matches']:
                    item = None
                    if 'metadata' in match:
                        item = match['metadata']
                        id = match['id']
                        item['id'] = str(id)
                        item['similarity'] = match['score']
                    else:
                        self.warning(f"No 'metadata' in result: {match}")
                    if item:    
                        result_list.append(item)
                        retrieved = retrieved + 1
                        if retrieved > self.provider.results_per_query:
                            break

                # end for
            else:
                self.warning("No 'matches'")
                self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
                self.status = 'READY'
                self.found = 0
                self.retrieved = 0
                return
        else:
            self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
            self.status = 'READY'
            self.found = 0
            self.retrieved = 0
            return
        
        self.found = len(response['matches'])
        self.retrieved = len(result_list)        
        self.response = result_list           
        return

