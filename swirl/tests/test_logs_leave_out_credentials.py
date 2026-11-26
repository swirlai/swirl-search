"""
Log lines name what failed without the credentials involved: page-fetch
header values and AI Provider keys stay out of the log.
"""

from types import SimpleNamespace
from unittest import mock

import pytest
import responses

from swirl import ai_provider as ai_provider_module
from swirl import web_page as web_page_module
from swirl.ai_provider import LLMWrapper
from swirl.web_page import PageFetcherFactory

URL = 'https://fetch.example.com/page'
HEADER_VALUE = 'Bearer header-value-for-test'
KEY_VALUE = 'key-value-for-test'


def logged(logger):
    return ' '.join(str(call.args[0]) for method in ('debug', 'info', 'warning', 'error')
                    for call in getattr(logger, method).call_args_list)


@pytest.fixture
def page_log():
    with mock.patch.object(web_page_module, 'logger') as logger:
        yield logger


@responses.activate
def test_failed_page_fetch_logs_header_names_only(page_log):
    responses.add(responses.GET, URL, status=500)
    fetcher = PageFetcherFactory.alloc_page_fetcher(
        url=URL, options={'cache': 'false', 'headers': {'Authorization': HEADER_VALUE}})

    assert fetcher.get_page() is None

    text = logged(page_log)
    assert '500' in text and URL in text
    assert 'Authorization' in text
    assert HEADER_VALUE not in text


def test_options_that_are_not_enabled_log_their_names_only(page_log):
    options = {'headers': {'Authorization': HEADER_VALUE}}

    assert PageFetcherFactory.alloc_page_fetcher(url=URL, options=options) is None

    text = logged(page_log)
    assert 'headers' in text
    assert HEADER_VALUE not in text


def test_rejected_ai_provider_key_is_not_logged():
    provider = SimpleNamespace(name='Test Provider', model='test-model', api_key=KEY_VALUE, config={})
    llm = mock.Mock()
    llm.completion.side_effect = RuntimeError('rejected')

    with mock.patch.object(ai_provider_module, 'logger') as logger:
        logger.getEffectiveLevel.return_value = 20
        LLMWrapper(llm, provider)

    text = logged(logger)
    assert 'Test Provider' in text and 'not valid' in text
    assert KEY_VALUE not in text
