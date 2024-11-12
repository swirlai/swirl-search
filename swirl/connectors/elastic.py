'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ
from datetime import datetime

import django

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.connectors.utils import bind_query_mappings
from swirl.connectors.verify_ssl_common import VerifyCertsCommon

from elasticsearch import Elasticsearch
from elasticsearch import *

import re
import ast

########################################
########################################

class Elastic(VerifyCertsCommon):

    type = "Elastic"

    def __init__(self, provider_id, search_id, update, request_id=''):
        super().__init__(provider_id, search_id, update, request_id)


    ########################################

    def construct_query(self):

        logger.debug(f"{self}: construct_query()")

        query_to_provider = bind_query_mappings(self.provider.query_template, self.provider.query_mappings)

        if '{query_string}' in self.provider.query_template:
            query_to_provider = query_to_provider.replace('{query_string}', self.query_string_to_provider)

        sort_field = ""
        if 'sort_by_date' in self.query_mappings:
            sort_field = self.query_mappings['sort_by_date']
        # end if

        elastic_query = ""
        if self.search.sort.lower() == 'date':
            if sort_field:
                # to do: support ascending??? p2
                elastic_query = query_to_provider + f", sort=[{{f'{sort_field}': 'desc'}}], size=" + str(self.provider.results_per_query)
            # endif
        else:
            elastic_query = query_to_provider + ', size=' + str(self.provider.results_per_query)
        # end if

        if elastic_query == "":
            self.error(f"elastic_query unexpectedly blank")

        self.query_to_provider = elastic_query
        logger.debug(f"Constructed query_to_provider: {self.query_to_provider}")
        return

    def execute_search(self, size, session=None):

        logger.debug(f"{self}: execute_search()")

        auth = None
        bearer = None
        (username,password,verify_certs,ca_certs,bearer)=self.get_creds()
        if self.status in ("ERR_INVALID_CREDENTIALS", "ERR_NO_CREDENTIALS"):
            return
        if bearer:
            self.warning(f"bearer token specified but not supported")
        auth = (username, password)

        url = None
        if self.provider.url:
            if self.provider.url.startswith('hosts='):
                url = self.provider.url.split('hosts=')[1][:]
                if url.startswith("'"):
                    url = url[1:-1]
            else:
                url = self.provider.url

        if not url:
            self.status = "ERR_NO_URL"
            return

        try:
            if verify_certs:
                es = Elasticsearch(basic_auth=tuple(auth),hosts=url,verify_certs=verify_certs,ca_certs=ca_certs)
            else:
                if auth:
                    es = Elasticsearch(basic_auth=tuple(auth),hosts=url)
                else:
                    es = Elasticsearch(hosts=url)

        except NameError as err:
            self.error(f'NameError: {err}')
        except TypeError as err:
            self.error(f'TypeError: {err}')
        except Exception as err:
            self.error(f"Exception: {err}")

        # extract index (str)
        index_name_pattern = r"index='([^']+)'"
        match = re.search(index_name_pattern, self.query_to_provider)
        if match:
            index = match.group(1)
        else:
            self.status = "ERR_NO_INDEX_SPECIFIED"
            return

        # extract query (dict)
        query_pattern = r"query=({.*})"
        match = re.search(query_pattern, self.query_to_provider)
        if match:
            query_s = match.group(1)
            query = ast.literal_eval(query_s)
        else:
            self.status = "ERR_NO_QUERY_SPECIFIED"
            return
        
        # Extract size (int) - Optional
        size_pattern = r"size=(\d+)"
        match = re.search(size_pattern, self.query_to_provider)
        if match:
            size = int(match.group(1))
        else:
            size = 10  # Default size if not specified

        response = None
        try:
            response = es.search(index=index, query=query, size=size)
        except ConnectionError as err:
            self.error(f"es.search reports: {err}")
        except NotFoundError:
            self.error(f"es.search reports HTTP/404 (Not Found)")
        except RequestError as err:
            self.error(f"es.search reports Bad Request {err}")
        except AuthenticationException:
            self.error(f"es.search reports HTTP/401 (Forbidden)")
        except AuthorizationException:
            self.error(f"es.search reports HTTP/403 (Access Denied)")
        except ApiError as err:
            self.error(f"es.search reports '{err}'")

        self.response = response

        return

    ########################################

    def normalize_response(self):

        logger.debug(f"{self}: normalize_response()")

        if len(self.response) == 0:
            self.error("search succeeded, but found no json data in response")

        if not 'hits' in self.response.keys():
            self.error("search succeeded, but json data was missing key 'hits'")

        found = self.response['hits']['total']['value']
        self.found = found
        if found == 0:
            # no results, not an error
            self.retrieved = 0
            self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
            self.status = 'READY'
            return

        results = self.response['hits']['hits']
        self.results = results

        retrieved = len(results)
        self.retrieved = retrieved

        return
