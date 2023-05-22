'''
@author:     Sid Probstein
@contact:    sid@swirl.today
@version:    SWIRL 1.3
'''

from sys import path
from os import environ

import django

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

from celery.utils.log import get_task_logger
from logging import DEBUG
logger = get_task_logger(__name__)

from swirl.connectors.utils import bind_query_mappings
from swirl.connectors.connector import Connector

########################################
########################################

class DBConnector(Connector):

    type = "DBConnector"

    ########################################

    def __init__(self, provider_id, search_id, update):

        self.count_query = ""
        self.column_names = []
        return super().__init__(provider_id, search_id, update)

    def construct_query(self):

        logger.info(f"{self}: construct_query()")

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
            count_query = count_query.replace('{query_string}', self.query_string_to_provider)
        else:
            self.error(f"{{query_string}} not found in bound query_template {count_query}")
            return
            
        self.count_query = count_query

        # main query
        query_to_provider = bind_query_mappings(self.provider.query_template, self.provider.query_mappings)
        if '{query_string}' in query_to_provider:
            query_to_provider = query_to_provider.replace('{query_string}', self.query_string_to_provider)

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
                    logger.warning(f"{self}: has no sort_field, ignoring request to sort this provider")
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

    def validate_query(self, session=None):

        logger.info(f"{self}: validate_query()")

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

