"""
@author:     Anush008
@contact:    anush.shetty@qdrant.com
"""

from sys import path
from os import environ

import django

from swirl.utils import swirl_setdir

path.append(swirl_setdir())
environ.setdefault("DJANGO_SETTINGS_MODULE", "swirl_server.settings")
django.setup()

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

from swirl.connectors.vdb_connector import VectorDBConnector
from qdrant_client import QdrantClient


class QdrantDB(VectorDBConnector):
    type = "QdrantDB"

    def execute_search(self, session=None):
        logger.debug(f"{self}: execute_search()")

        api_key = self.provider.credentials
        qdrant_url, collection_name = self.provider.url.split("-", maxsplit=1)

        if not self.vector_to_provider:
            self.status = "ERR"
            self.error(f"No vector for query: {self.query_string_to_provider}")
            return

        try:
            client = QdrantClient(url=qdrant_url, api_key=api_key)
            response = client.search(
                collection_name,
                query_vector=self.vector_to_provider,
                limit=self.provider.results_per_query,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as err:
            self.error(f"{err} connecting to {self.type}")
            self.status = "ERR"
            return

        result_list = []
        if response:
            for point in response:
                item = point.payload
                item["id"] = str(point.id)
                item["similarity"] = point.score
                result_list.append(item)

        else:
            self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
            self.status = "READY"
            self.found = 0
            self.retrieved = 0
            return

        self.found = len(response)
        self.retrieved = len(result_list)
        self.response = result_list
        return
