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

try:
    import psycopg2
except ImportError as e:
    logger.error(f"postgresql.py: Error: can't load psycopg2: {e}, see https://docs.swirlaiconnect.com/Developer-Reference.html#postgresql")

from swirl.connectors.db_connector import DBConnector

########################################
########################################

class PostgreSQL(DBConnector):

    type = "PostgreSQL"

    ########################################

    def execute_search(self, session=None):

        logger.debug(f"{self}: execute_search()")

        # connect to the db
        config = self.provider.url.split(':')
        if len(config) != 5:
            self.error(f'Invalid configuration: {config}')
            self.status = 'ERR_INVALID_CONFIG'
            return

        connection = None
        try:
            connection = psycopg2.connect(host=config[0], port=config[1], database=config[2], user=config[3], password=config[4])
        except Error as err:
            self.error(f"{err} connecting to {self.type}")
            return

        # issue the count(*) query
        cursor = None
        rows = None
        found = None
        try:
            cursor = connection.cursor()
            cursor.execute(self.count_query)
            found = cursor.fetchone()
        except Error as err:
            self.error(f"{err} connecting to {self.type}")
            self.status = 'ERR'
            return

        if found == None:
            found = 0
        else:
            found = found[0]

        if 'json' in self.count_query.lower():
            self.warning(f"Ignoring 0 return from find, since 'json' appears in the query_string")
        else:
            if found == 0:
                self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
                self.status = 'READY'
                self.found = 0
                self.retrieved = 0
                return
            # end if
        # end if

        # issue the main query
        cursor = None
        rows = None
        try:
            cursor = connection.cursor()
            rows = None
            cursor.execute(self.query_to_provider)
            column_names = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
        except Error as err:
            self.error(f"{err} querying {self.type}")
            return

        # rows is a list of tuple results

        if rows == None:
            logger.warning(f"Received 0 results, but count_query returned {found}")
            self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
            return
            # end if
        # end if

        self.response = rows

        cursor.close()
        connection.close()

        self.column_names = column_names
        self.found = found
        return