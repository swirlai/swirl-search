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
import psycopg2

from celery.utils.log import get_task_logger
from logging import DEBUG
logger = get_task_logger(__name__)
logger.setLevel(DEBUG)

from .utils import save_result, bind_query_mappings

from .connector import Connector

class PostGresql(Connector):

    type = "PostGresql"

    ########################################

    def __init__(self, provider_id, search_id):

        self.count_query = ""
        self.column_names = []
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
