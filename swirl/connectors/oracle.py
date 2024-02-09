'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ

import oracledb

import json

import django

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.connectors.db_connector import DBConnector
from swirl.connectors.utils import bind_query_mappings

########################################
########################################

class Oracle(DBConnector):

    type = "Oracle"

    ########################################

    def execute_search(self, session=None):

        logger.debug(f"{self}: execute_search()")

        if self.provider.credentials:
            if ':' in self.provider.credentials:
                credlist = self.provider.credentials.split(':')
                if len(credlist) == 2:
                    username = credlist[0]
                    password = credlist[1]
                else:
                    self.warning("Invalid credentials, should be: username:password")
        else:
            self.warning("No credentials!")
        dsn = self.provider.url

        try:
            # Create a new connection
            conn = oracledb.connect(username, password, dsn)
            cursor = conn.cursor()
            cursor.execute(self.count_query)
            found = cursor.fetchone()[0]
            if found == 0:
                self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
                self.status = 'READY'
                self.found = 0
                self.retrieved = 0
                return
            
            cursor.execute(self.query_to_provider)
            self.column_names = [col[0].lower() for col in cursor.description]
            # this is a problem TO DO
            results = [dict(zip(self.column_names, row)) for row in cursor]
        except oracledb.DatabaseError as e:
            error, = e.args
            self.error(f"Database error: {error.code}, {error.message}")
            self.status = 'ERR'
            cursor.close()
            conn.close()
            return

        try:
            if results:
                self.results = json.dumps(results, default=str)
                # ensure that self.response is not normalized by the base DBConnector class
                self.response = None
        except json.JSONDecodeError as err:
            self.error(f"{err} converting JSON")

        cursor.close()
        conn.close()

        self.found = found
        self.retrieved = self.provider.results_per_query
        return

