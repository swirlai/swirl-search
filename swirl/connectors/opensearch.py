'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ
from datetime import datetime
from urllib.parse import urlparse

import django

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.connectors.utils import bind_query_mappings
from swirl.connectors.verify_ssl_common import VerifyCertsCommon
import json

from opensearchpy import OpenSearch as opensearch
from opensearchpy.exceptions import AuthenticationException, AuthorizationException, ConnectionError, NotFoundError, RequestError, SSLError, TransportError

########################################
########################################

class OpenSearch(VerifyCertsCommon):

    type = "OpenSearch"

    def __init__(self, provider_id, search_id, update, request_id=''):
        super().__init__(provider_id, search_id, update, request_id)


    ########################################

    def construct_query(self):

        logger.debug(f"{self}: construct_query()")

        base_query = bind_query_mappings(self.provider.query_template, self.provider.query_mappings)
        logger.debug(f"base_query: {base_query}")

        if '{query_string}' in self.provider.query_template:
            base_query = base_query.replace('{query_string}', self.query_string_to_provider)

        query_to_provider = json.loads(base_query)
        if type(query_to_provider) != dict:
            self.error(f"error converting to dict: {base_query}")
            # to do stop?

        sort_field = ""
        if 'sort_by_date' in self.query_mappings:
            sort_field = self.query_mappings['sort_by_date']
        # end if

        if self.search.sort.lower() == 'date':
            if sort_field:
                # to do: support ascending??? p2
                query_to_provider['sort'] = [
                    {
                        f'{sort_field}': 'desc'
                    }
                ]
        self.query_to_provider = query_to_provider
        return

    ########################################

    def execute_search(self, session=None):

        logger.debug(f"{self}: execute_search()")

        parsed_url = urlparse(self.provider.url)
        host = parsed_url.hostname
        port = parsed_url.port

        logger.debug(f"{self}: host: {host}, port: {port}")

        client = None
        if self.provider.credentials:
            bearer = None
            (username,password,verify_certs,ca_certs,bearer)=self.get_creds()
            if self.status in ("ERR_INVALID_CREDENTIALS", "ERR_NO_CREDENTIALS"):
                return
            if bearer:
                self.warning(f"Warning: bearer token specified but not supported")

            auth = (username, password)
            # ca_certs_path = '/full/path/to/root-ca.pem' # Provide a CA bundle if you use intermediate CAs with your root CA.
            # Optional client certificates if you don't want to use HTTP basic authentication.
            # client_cert_path = '/full/path/to/client.pem'
            # client_key_path = '/full/path/to/client-key.pem'
            try:
                client = opensearch(
                    hosts = [{'host': host, 'port': port}],
                    http_compress = True, # enables gzip compression for request bodies
                    http_auth = auth,
                    # client_cert = client_cert_path,
                    # client_key = client_key_path,
                    use_ssl = True,
                    verify_certs = verify_certs,
                    ssl_assert_hostname = False,
                    ssl_show_warn = False,
                    ca_certs = ca_certs
                )
            except SSLError:
                self.error(f"client.search reports SSL Error")
            except ConnectionError as err:
                self.error(f"client.search reports: {err}")
            except NameError as err:
                self.error(f'NameError: {err}')
            except TypeError as err:
                self.error(f'TypeError: {err}')
        else:
            # no credentials!
            logger.debug("no credentials!")
            try:
                client = opensearch(
                    hosts = [{'host': host, 'port': port}],
                    http_compress = True, # enables gzip compression for request bodies
                    use_ssl = False,
                    verify_certs = False,
                    ssl_assert_hostname = False,
                    ssl_show_warn = False
                )
            except SSLError as err:
                self.error(f"client.search reports SSL Error: {err}")
            except ConnectionError as err:
                self.error(f"client.search reports: {err}")
            except NameError as err:
                self.error(f'NameError: {err}')
            except TypeError as err:
                self.error(f'TypeError: {err}')
        # end if

        if not client:
            self.error("client failed to initialize")
            self.status = "ERR_CLIENT_INIT_FAILED"
            return

        response = None
        try:
            # security review 1.7 - OK - limited to Elasticsearch
            response = client.search(size=self.provider.results_per_query, index=self.query_mappings['index_name'], body=self.query_to_provider)
        # to do: not sure we need this error
        except SSLError as err:
            self.error(f"client.search reports SSL Error: {err}")
        except NotFoundError:
            self.error(f"client.search reports HTTP/404 (Not Found)")
        except RequestError as err:
            self.error(f"client.search reports Bad Request {err}")
        except AuthenticationException:
            self.error(f"client.search reports HTTP/401 (Forbidden)")
        except AuthorizationException:
            self.error(f"client.search reports HTTP/403 (Access Denied)")
        except ConnectionError as err:
            self.error(f"client.search reports: {err}")
        except TransportError as err:
            self.error(f"client.search reports Transport Error: {err}")

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
