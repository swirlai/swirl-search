'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import os
from sys import path
from os import environ
from datetime import datetime

import django
from django.db import DataError

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

import sqlite3
from sqlite3 import Error

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.connectors.db_connector import DBConnector

########################################
########################################

class Sqlite3(DBConnector):

    type = "Sqlite3"

    ########################################

    def execute_search(self, session=None):

        logger.debug(f"{self}: execute_search()")

        # connect to the db
        db_path = self.provider.url
        if not os.path.exists(db_path):
            self.error(f"db_path does not exist")
            return

        connection = None
        try:
            connection = sqlite3.connect(db_path)
            connection.row_factory = sqlite3.Row
        except Error as err:
            self.error(f"{err} connecting to {self.type}: {db_path}")
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
            self.error(f"execute_count_query: {err}")
            self.status = 'ERR'
            return

        if found == None:
            found = 0
        else:
            found = found[0]

        if 'json' in self.count_query.lower():
            logger.warning(f"{self}: ignoring 0 return from find, since 'json' appears in the query_string")
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
            rows = cursor.fetchall()
        except Error as err:
            self.error(f"execute_count_query: {err}")
            self.status = 'ERR'
            cursor.close()
            connection.close()
            return

        if rows == None:
            self.warning(f"Retrieved 0 results, but count_query returned {found}")
            self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
            return
            # end if
        # end if

        self.response = rows
        self.found = found
        self.status = 'READY'

        cursor.close()
        connection.close()

        return
    