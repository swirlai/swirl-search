'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ
from datetime import datetime

import django
from django.db import Error

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from google.cloud import bigquery

from swirl.connectors.db_connector import DBConnector

########################################
########################################

# https://cloud.google.com/bigquery/docs/quickstarts/quickstart-client-libraries#client-libraries-install-python

class BigQuery(DBConnector):

    type = "BigQuery"

    ########################################

    def execute_search(self, session=None):

        logger.debug(f"{self}: execute_search()")

        if self.provider.credentials:
            environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.provider.credentials
        else:
            self.status = "ERR_NO_CREDENTIALS"
            return

        # connect to the db
        try:
            client = bigquery.Client()
        except Error as err:
            self.error(f"{err} connecting to {self.type}")
            self.status = 'ERR'
            return

        # issue the count(*) query
        found = None
        query_job = client.query(self.count_query)
        results = query_job.result()
        list_results = list(results)
        # fix for https://github.com/swirlai/swirl-search/issues/96
        found = int(list_results[0][0])
        if found == 0:
            self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
            self.status = 'READY'
            self.found = 0
            self.retrieved = 0
            return
        # end if

        # issue the main query
        try:
            query_job = client.query(self.query_to_provider)
            results = query_job.result()
            self.response = list(results)
        except Error as err:
            self.error(f"{err} querying {self.type}")
            self.status = 'ERR'
            client.close()
            return

        client.close()

        self.column_names = dict(self.response[0]).keys()
        self.found = found
        return
