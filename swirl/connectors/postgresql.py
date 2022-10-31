'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.3
'''

import django
from django.db import Error
from django.core.exceptions import ObjectDoesNotExist
import os
from sys import path
from os import environ

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()    

from celery.utils.log import get_task_logger
from logging import DEBUG
logger = get_task_logger(__name__)
logger.setLevel(DEBUG)

########################################
try:
    import psycopg2
except ImportError as e:
    logger.error(f"postgresql.py: Error: can't load psycopg2: {e}, see https://github.com/sidprobstein/swirl-search/wiki/4.-Object-Reference#postgresql")

from .utils import save_result, bind_query_mappings

from .db_connector import DBConnector

class PostgreSQL(DBConnector):

    type = "PostgreSQL"

    ########################################

    def execute_search(self):

        # connect to the db
        config = self.provider.url.split(':')
        if len(config) != 5:
            self.error(f'Invalid configuration: {config}')
            return

        # localhost:5432:sid:sid:sid
        connection = None
        try:
            connection = psycopg2.connect(host=config[0], port=config[1], database=config[2], user=config[3], password=config[4])
        except Error as err:
            self.error(f"{err} connecting to {self.type}")
            return
        logger.info(f"{self}: connected")

        # issue the count(*) query
        logger.debug(f"{self}: requesting: {self.provider.connector} -> {self.count_query}")
        cursor = None
        rows = None
        found = None
        try:
            cursor = connection.cursor()
            cursor.execute(self.count_query)
            found = cursor.fetchone()
        except Error as err:
            self.error(f"execute_count_query: {err}")
            return

        # found = (1460,)
        if found == None:
            found = 0
        else:
            found = found[0]

        if 'json' in self.count_query.lower():
            logger.debug(f"{self}: ignoring 0 return from find, since 'json' appears in the query_string")
        else:
            if found == 0:
                message = f"Retrieved 0 of 0 results from: {self.provider.name}"
                logger.info(f'{self}: {message}')
                self.messages.append(message)
                self.status = 'READY'
                self.found = 0
                self.retrieved = 0
                return
            # end if
        # end if

        # issue the main query
        logger.debug(f"{self}: requesting: {self.provider.connector} -> {self.query_to_provider}")
        cursor = None
        rows = None
        try:
            cursor = connection.cursor()
            rows = None
            cursor.execute(self.query_to_provider)
            column_names = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
        except Error as err:
            self.error(f"execute_count_query: {err}")
            return

        # rows is a list of tuple results

        if rows == None:
            message = f"Retrieved 0 of 0 results from: {self.provider.name}"
            logger.warning(f'{self}: {message}, but count_query returned {found}')
            self.messages.append(message)
            return
            # end if
        # end if
        
        self.response = rows
        self.column_names = column_names
        self.found = found
        return

    ########################################

    def normalize_response(self):
        
        rows = self.response
        found = self.found

        if found == 0:
            return

        # rows = [ (1, 'lifelock', 'LifeLock', '', 'web', 'Tempe', 'AZ', datetime.date(2007, 5, 1), Decimal('6850000'), 'USD', 'b'), etc ]

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
