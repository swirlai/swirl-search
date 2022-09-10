'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.2
'''

import django
from django.db import Error
from django.core.exceptions import ObjectDoesNotExist
from sys import path
from os import environ

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from .utils import save_result, bind_query_mappings

from .connector import Connector

from elasticsearch import Elasticsearch
import elasticsearch

class Elastic(Connector):

    type = "Elastic"

    ########################################

    def construct_query(self):

        query_to_provider = bind_query_mappings(self.provider.query_template, self.provider.query_mappings)

        if '{query_string}' in self.provider.query_template:
            query_to_provider = query_to_provider.replace('{query_string}', self.search.query_string_processed)

        sort_field = ""
        if 'sort_by_date' in self.query_mappings:
            for field in self.query_mappings.split(','):
                if field.lower().startswith('sort_by_date'):
                    if '=' in field:
                        sort_field = field[field.find('=')+1:]
                    else:
                        self.error(f"sort_by_date mapping is missing '='")
                    # end if
                # end if
            # end for
        # end if

        elastic_query = ""
        if self.search.sort.lower() == 'date':
            if sort_field:
                # to do: support ascending??? p2
                elastic_query = 'es.search(' + query_to_provider + f", sort=[{{'{sort_field}': 'desc'}}], size=" + str(self.provider.results_per_query) + ')'
            # endif
        else:
            elastic_query = 'es.search(' + query_to_provider + ', size=' + str(self.provider.results_per_query) + ')'
        # end if
        logger.info(f"{self}: issuing query: {self.provider.connector} -> {elastic_query}")

        if elastic_query == "":
            self.error(f"elastic_query unexpectedly blank")

        self.query_to_provider = elastic_query
        return

    ########################################

    def execute_search(self):     

        try:
            es = eval(f'Elasticsearch({self.provider.credentials}, {self.provider.url})')
        except NameError as err:
            self.error(f'NameError: {err}')
        except TypeError as err:
            self.error(f'TypeError: {err}')

        response = None
        try:
            response = eval(self.query_to_provider)
        except elasticsearch.ConnectionError as err:
            self.error(f"es.search reports: {err}")
        except elasticsearch.NotFoundError:
            self.error(f"es.search reports HTTP/404 (Not Found)")
        except elasticsearch.RequestError:
            self.error(f"es.search reports Bad Request")
        except elasticsearch.AuthenticationException:
            self.error(f"es.search reports HTTP/401 (Forbidden)")
        except elasticsearch.AuthorizationException:
            self.error(f"es.search reports HTTP/403 (Access Denied)")
        except elasticsearch.ApiError as err:
            self.error(f"es.search reports '{err}'")

        self.response = response
        return

    ########################################

    def normalize_response(self):
        
        if len(self.response) == 0:
            self.error("search succeeded, but found no json data in response")

        if not 'hits' in self.response.keys():
            self.error("search succeeded, but json data was missing key 'hits'")

        found = self.response['hits']['total']['value']
        self.found = found
        if found == 0:
            # no results, not an error
            self.retrieved = 0
            self.messages.append(f"Retrieved 0 of 0 results from: {self.provider.name}")
            self.status = 'READY'
            return

        results = self.response['hits']['hits']
        self.results = results

        retrieved = len(results)
        self.retrieved = retrieved
        self.status = 'READY'
        return

