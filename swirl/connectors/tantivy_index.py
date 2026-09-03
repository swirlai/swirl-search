'''
@author:     Sid Probstein
@contact:    sid@swirl.today

TantivyIndex connector: read side of the SWIRL for Backstage index
(TECH_DESIGN_swirl_for_backstage.md section 3.4).

Reads only. It opens the live generation of each requested type, per process,
and reloads when the LIVE file changes. Nothing here writes the index; that is
the ingest API in swirl/views_index.py.
'''

from sys import path
from os import environ

import django

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.connectors.connector import Connector
from swirl.tantivy_index.manager import default_manager

########################################
########################################

#: Where the search view parks the Backstage query params (section 3.5).
BACKSTAGE_KEY = 'backstage'


class TantivyIndex(Connector):

    type = "TantivyIndex"

    ########################################

    def __init__(self, provider_id, search_id, update, request_id=''):
        self.backstage_types = []
        self.backstage_filters = {}
        return super().__init__(provider_id, search_id, update, request_id=request_id)

    ########################################

    @property
    def manager(self):
        return default_manager

    def _backstage_block(self, source):
        '''The backstage sub-block of a query_template_json, or an empty dict.'''
        payload = getattr(source, 'query_template_json', None) or {}
        if not isinstance(payload, dict):
            return {}
        block = payload.get(BACKSTAGE_KEY) or {}
        return block if isinstance(block, dict) else {}

    ########################################

    def construct_query(self):
        '''
        Copy the processed query string through, and pick up backstage_types and
        backstage_filters from the Search, falling back to the SearchProvider.
        '''

        logger.debug(f"{self}: construct_query()")
        self.query_to_provider = self.query_string_to_provider

        from_search = self._backstage_block(self.search)
        from_provider = self._backstage_block(self.provider)

        types = from_search.get('types')
        if not types:
            types = from_provider.get('types')
        self.backstage_types = self._clean_types(types)

        filters = from_search.get('filters')
        if not filters:
            filters = from_provider.get('filters')
        self.backstage_filters = self._clean_filters(filters)
        return

    @staticmethod
    def _clean_types(types):
        if not types:
            return []
        if isinstance(types, str):
            types = [part.strip() for part in types.split(',')]
        if not isinstance(types, (list, tuple, set)):
            return []
        return [str(name).strip() for name in types if str(name).strip()]

    @staticmethod
    def _clean_filters(filters):
        '''Keep only scalar or list-of-scalar values, which is what attrs holds.'''
        if not isinstance(filters, dict):
            return {}
        clean = {}
        for key, value in filters.items():
            key = str(key).strip()
            if not key:
                continue
            if isinstance(value, (list, tuple, set)):
                values = [str(item).strip() for item in value
                          if not isinstance(item, (dict, list, tuple, set))
                          and str(item).strip()]
                if values:
                    clean[key] = values
            elif value is None or isinstance(value, dict):
                continue
            elif str(value).strip():
                clean[key] = str(value).strip()
        return clean

    ########################################

    def validate_query(self, session=None):

        logger.debug(f"{self}: validate_query()")
        if not self.query_to_provider:
            self.error("query_to_provider is blank or missing")
            return False
        return True

    ########################################

    def execute_search(self, session=None):

        logger.debug(f"{self}: execute_search()")

        try:
            hits = self.manager.search(
                types=self.backstage_types,
                term=self.query_to_provider,
                filters=self.backstage_filters,
                limit=self.provider.results_per_query,
                offset=0,
            )
        except Exception as err:
            self.error(f"tantivy search failed: {err}")
            return

        self.response = hits
        self.found = len(hits)
        self.retrieved = len(hits)
        if not hits:
            self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
        self.status = 'READY'
        return

    ########################################

    def normalize_response(self):
        '''
        Turn Tantivy hits into SWIRL result dictionaries. The whole Backstage
        document travels in payload.backstage so the plugin can render it.
        '''

        logger.debug(f"{self}: normalize_response()")

        if not self.response:
            self.retrieved = 0
            self.results = []
            self.message(f"Retrieved 0 of 0 results from: {self.provider.name}")
            self.status = 'READY'
            return

        results = []
        for hit in self.response:
            document = hit.get('document') or {}
            snippet = hit.get('snippet') or ''
            body = snippet or (hit.get('body') or document.get('text') or '')
            # searchprovider_score rides inside payload on purpose. Community's
            # MappingResultProcessor collects every result key it does not
            # recognise into a payload of its own and then overwrites
            # swirl_result['payload'] with it, which would drop payload.backstage.
            # Emitting only keys the processor knows, with the score inside the
            # payload, keeps both.
            result = {
                'title': hit.get('title') or document.get('title') or '',
                'body': body,
                'url': hit.get('location') or document.get('location') or '',
                'title_hit_highlights': [],
                'body_hit_highlights': [snippet] if snippet else [],
                'payload': {
                    BACKSTAGE_KEY: {
                        'type': hit.get('type') or '',
                        'document': document,
                    },
                    'doc_id': hit.get('doc_id') or '',
                    'searchprovider_score': hit.get('score', 0.0),
                },
            }
            results.append(result)
        # end for

        self.results = results
        self.retrieved = len(results)
        if self.found < self.retrieved:
            self.found = self.retrieved
        return
