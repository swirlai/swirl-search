from django.test import TestCase

from swirl.connectors.requests import Requests

QUERY_TO_PROVIDER = 'https://example.com/api?cx=abc&q=test'


class RequestsBuildPageQueryTestCase(TestCase):
    """
    URL paging rewrites the PAGE query mapping into the query sent to the source.
    build_page_query() takes the 0-based page number and the 1-based index of the
    first result wanted.
    """

    def _connector(self, page_mapping=None):
        # the mappings and the query are all build_page_query() needs, so skip the
        # database round trip a real SearchProvider would require
        connector = object.__new__(Requests)
        connector.query_mappings = {} if page_mapping is None else {'PAGE': page_mapping}
        connector.query_to_provider = QUERY_TO_PROVIDER
        connector.warnings = []
        connector.warning = lambda message: connector.warnings.append(message)
        return connector

    def test_result_index_is_one_based(self):
        connector = self._connector('start=RESULT_INDEX')
        assert connector.build_page_query(0, 1) == 'https://example.com/api?cx=abc&start=1&q=test'
        assert connector.build_page_query(2, 21) == 'https://example.com/api?cx=abc&start=21&q=test'

    def test_result_zero_index_is_zero_based(self):
        connector = self._connector('offset=RESULT_ZERO_INDEX')
        assert connector.build_page_query(0, 1) == 'https://example.com/api?cx=abc&offset=0&q=test'
        assert connector.build_page_query(2, 21) == 'https://example.com/api?cx=abc&offset=20&q=test'

    def test_page_index_counts_pages_from_one(self):
        connector = self._connector('page=PAGE_INDEX')
        assert connector.build_page_query(0, 1) == 'https://example.com/api?cx=abc&page=1&q=test'
        assert connector.build_page_query(2, 21) == 'https://example.com/api?cx=abc&page=3&q=test'

    def test_unresolvable_page_mapping_warns_and_falls_back(self):
        connector = self._connector('start=BOGUS')
        assert connector.build_page_query(1, 11) == QUERY_TO_PROVIDER
        assert len(connector.warnings) == 1

    def test_no_page_mapping_returns_the_query_unchanged(self):
        connector = self._connector()
        assert connector.build_page_query(0, 1) == QUERY_TO_PROVIDER

    def test_paging_defaults(self):
        assert self._connector().supports_paging() is False
        assert self._connector('start=RESULT_INDEX').supports_paging() is True
        assert self._connector().get_page_size() == Requests.DEFAULT_PAGE_SIZE
        assert self._connector().continue_paging({}) is True
