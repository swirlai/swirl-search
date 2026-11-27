"""
Requests to an HTTP source carry a timeout (SWIRL_REQUEST_TIMEOUT), and a
source that does not answer in time is reported as an error for that source.
"""

import time
from unittest import mock

import pytest
import requests
from django.contrib.auth.models import User

from swirl.connectors.requestsget import RequestsGet
from swirl.connectors.requestspost import RequestsPost
from swirl.models import Search, SearchProvider

CASES = [(RequestsGet, 'swirl.connectors.requestsget.requests.get'),
         (RequestsPost, 'swirl.connectors.requestspost.requests.post')]


def connector_for(kind, name):
    owner = User.objects.create_superuser(f'timeout_{name}', f'timeout_{name}@example.com', 'not-a-real-password')
    provider = SearchProvider.objects.create(
        owner=owner, name=f'slow source {name}', shared=True, active=True, connector=kind.__name__,
        url='https://source.example.invalid/search', query_template='{url}?q={query_string}')
    search = Search.objects.create(owner=owner, query_string='term', query_string_processed='term',
                                   searchprovider_list=[provider.id])
    connector = kind(provider.id, search.id, False, '')
    connector.start_time = time.time()
    connector.query_string_to_provider = 'term'
    connector.construct_query()
    return connector


@pytest.mark.django_db
@pytest.mark.parametrize('kind,target', CASES)
def test_the_request_carries_the_configured_timeout(kind, target, settings):
    settings.SWIRL_REQUEST_TIMEOUT = 7
    connector = connector_for(kind, kind.__name__.lower())

    with mock.patch(target, side_effect=requests.exceptions.ConnectionError('stop here')) as sent:
        connector.execute_search()

    assert sent.call_args.kwargs['timeout'] == 7


@pytest.mark.django_db
@pytest.mark.parametrize('kind,target', CASES)
def test_zero_means_no_limit(kind, target, settings):
    settings.SWIRL_REQUEST_TIMEOUT = 0
    connector = connector_for(kind, kind.__name__.lower())

    with mock.patch(target, side_effect=requests.exceptions.ConnectionError('stop here')) as sent:
        connector.execute_search()

    assert sent.call_args.kwargs['timeout'] is None


@pytest.mark.django_db
@pytest.mark.parametrize('kind,target', CASES)
def test_a_source_that_does_not_answer_is_reported_not_raised(kind, target):
    connector = connector_for(kind, kind.__name__.lower())

    with mock.patch(target, side_effect=requests.exceptions.ReadTimeout('too slow')):
        connector.execute_search()

    assert connector.status == 'ERROR'
    assert any('no answer within' in message for message in connector.messages)


def test_the_default_is_sixty_seconds(settings):
    assert settings.SWIRL_REQUEST_TIMEOUT == 60
