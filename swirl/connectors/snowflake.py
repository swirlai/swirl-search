'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ

import snowflake.connector
from snowflake.connector import ProgrammingError

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

class Snowflake(DBConnector):

    type = "Snowflake"

    ########################################

    def execute_search(self, session=None):

        logger.debug(f"{self}: execute_search()")

        if self.provider.credentials:
            if ':' in self.provider.credentials:
                credlist = self.provider.credentials.split(':')
                if len(credlist) == 4:
                    username = credlist[0]
                    password = credlist[1]
                    database = credlist[2]
                    warehouse = credlist[3]
                else:
                    self.warning("Invalid credentials, should be: username:password:database:warehouse")
        else:
            self.warning("No credentials!")
        account = self.provider.url

        try:
            # Create a new connection
            conn = snowflake.connector.connect(user=username, password=password, account=account)
            cursor = conn.cursor()
            cursor.execute(f"USE WAREHOUSE {warehouse}")
            cursor.execute(f"USE DATABASE {database}")

            cursor.execute(self.count_query)
            count_result = cursor.fetchone()
            found = count_result[0] if count_result else 0
            if found == 0:
                self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
                self.status = 'READY'
                self.found = 0
                self.retrieved = 0
                return
            
            cursor.execute(self.query_to_provider)
            self.column_names = [col[0].lower() for col in cursor.description]
            results = cursor.fetchall()

        except ProgrammingError as err:
            self.error(f"{err} querying {self.type}")
            self.status = 'ERR'
            cursor.close()
            conn.close()
            return

        self.response = list(results)

        cursor.close()
        conn.close()

        self.found = found
        self.retrieved = self.provider.results_per_query
        return

