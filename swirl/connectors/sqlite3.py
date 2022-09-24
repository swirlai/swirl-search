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

# connectors

########################################
import sqlite3
from sqlite3 import Error

from celery.utils.log import get_task_logger
from logging import DEBUG
logger = get_task_logger(__name__)
logger.setLevel(DEBUG)

from .utils import save_result, bind_query_mappings

from .connector import Connector

class Sqlite3(Connector):

    type = "Sqlite3"

    ########################################

    def __init__(self, provider_id, search_id):

        self.count_query = ""
        return super().__init__(provider_id, search_id)

    def construct_query(self):

        # handle ;
        if not self.provider.query_template.endswith(';'):
            self.provider.query_template = self.provider.query_template + ';'
        # end if

        # count query
        count_query_template = self.provider.query_template
        if '{fields}' in count_query_template:
            count_query_template = self.provider.query_template.replace('{fields}', 'COUNT(*)')
        else:
            self.error(f"{{fields}} not found in bound query_template")
            return
        count_query = bind_query_mappings(count_query_template, self.provider.query_mappings)
    
        if '{query_string}' in count_query:
            count_query = count_query.replace('{query_string}', self.search.query_string_processed)
        else:
            self.error(f"{{query_string}} not found in bound query_template {count_query}")
            return
            
        self.count_query = count_query

        # main query
        query_to_provider = bind_query_mappings(self.provider.query_template, self.provider.query_mappings)
        if '{query_string}' in query_to_provider:
            query_to_provider = query_to_provider.replace('{query_string}', self.search.query_string_processed)

        # sort field
        sort_field = ""
        if 'sort_by_date' in self.provider.query_mappings:
            for field in self.provider.query_mappings.split(','):
                if field.lower().startswith('sort_by_date'):
                    if '=' in field:
                        sort_field = field[field.find('=')+1:]
                    else:
                        self.warning(f"sort_by_date mapping is missing '=', try removing spaces?")
                    # end if
                # end if
            # end for
        # end if

        if self.search.sort.lower() == 'date':
            if query_to_provider.endswith(';'):
                if sort_field:
                    query_to_provider = query_to_provider.replace(';', f' order by {sort_field} desc;')
                else:
                    logger.info(f"{self}: has no sort_field, ignoring request to sort this provider")
                # end if
            else:
                self.warning(f"query_to_provider is missing ';' at end")
            # end if
        # end if

        # results per query
        query_to_provider = query_to_provider.replace(';', ' limit ' + str(self.provider.results_per_query) + ';')
        self.query_to_provider = query_to_provider
        
        return

    ########################################

    def validate_query(self):

        if '{' in self.count_query or '}' in self.count_query:
            self.warning(f"found braces in count_query after template mapping")

        if self.count_query == "":
            self.error(f"count_query is blank")
            return False

        if '{' in self.query_to_provider or '}' in self.query_to_provider:
            self.warning(f"found braces in query_to_provider after template mapping")

        if self.query_to_provider == "":
            self.error(f"query_to_provider is blank")
            return False

        return True

    ########################################

    def execute_search(self):

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
            self.error(f"{err} connecting to sqlite3: {db_path}")
            return
        logger.info(f"{self}: connected to sqlite3: {db_path}")

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
            rows = cursor.fetchall()
        except Error as err:
            self.error(f"execute_count_query: {err}")
            return

        if rows == None:
            message = f"Retrieved 0 of 0 results from: {self.provider.name}"
            logger.warning(f'{self}: {message}, but count_query returned {found}')
            self.messages.append(message)
            return
            # end if
        # end if

        self.response = rows
        self.found = found
        return

    ########################################

    def normalize_response(self):
        
        rows = self.response
        found = self.found

        if found == 0:
            return

        trimmed_rows = []
        field_list = rows[0].keys()
        for row in rows:
            dict_row = {}
            n_field = 0
            for field in field_list:
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
