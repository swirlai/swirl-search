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
from logging import DEBUG
logger = get_task_logger(__name__)
# logger.setLevel(DEBUG)

from google.cloud import bigquery

from swirl.connectors.db_connector import DBConnector

########################################
########################################

# https://cloud.google.com/bigquery/docs/quickstarts/quickstart-client-libraries#client-libraries-install-python

class BigQuery(DBConnector):

    type = "BigQuery"

    ########################################

    def execute_search(self, session=None):

        logger.info(f"{self}: execute_search()")

        if self.provider.credentials:
            environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.provider.credentials
        else:
            self.status = "ERR_NO_CREDENTIALS"
            return

        # connect to the db
        try:
            client = bigquery.Client()
            # to do: review/test the below
        except Error as err:
            self.error(f"{err} connecting to {self.type}")
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
        query_job = client.query(self.query_to_provider)
        results = query_job.result()
        self.response = list(results)
        logger.debug(f"{self}: response: {self.response}")

        self.column_names = dict(self.response[0]).keys()
        self.found = found

        return

    ########################################

    def normalize_response(self):

        logger.info(f"{self}: normalize_response()")

        rows = self.response
        found = self.found

        if found == 0:
            return

        trimmed_rows = []
        column_names = self.column_names
        for row in rows:
            dict_row = {}
            n_field = 0
            for field in column_names:
                dict_row[field] = row[n_field]
                n_field = n_field + 1
            # end for
            trimmed_rows.append(dict_row)
        # end for
        retrieved = len(trimmed_rows)
        if retrieved == 0:
            self.error(f"rows were returned, but couldn't serialize them")
            return

        if retrieved > found:
            found = retrieved

        self.found = found
        self.retrieved = retrieved
        # self.messages.append(f"Retrieved1 {retrieved} of {found} results from: {self.provider.name}")
        self.results = trimmed_rows
        return
