"""
A provider's key=value credentials are substituted into the request a
connector sends. The provider query and the messages saved with a search, and
the log, show that request without the credential values.
"""

import time
from unittest import mock

import pytest
from django.contrib.auth.models import Permission, User
from rest_framework.test import APIClient

from swirl.connectors.connector import CREDENTIAL_PLACEHOLDER
from swirl.connectors.requestsget import RequestsGet
from swirl.models import Result, Search, SearchProvider

SECRET = 'provider-key-value-0001'


@pytest.fixture
def searcher(db):
    user = User.objects.create_user('cred_searcher', 'cred_searcher@example.com', 'not-a-real-password')
    user.user_permissions.set(Permission.objects.filter(
        content_type__app_label='swirl',
        codename__in=['add_search', 'view_search', 'view_result', 'view_searchprovider']))
    return User.objects.get(pk=user.pk)


@pytest.fixture
def provider(db):
    admin = User.objects.create_superuser('cred_admin', 'cred_admin@example.com', 'not-a-real-password')
    return SearchProvider.objects.create(
        owner=admin, name='keyed source', shared=True, active=True, connector='RequestsGet',
        url='http://source.example.invalid/s', query_template='{url}?key={key}&q={query_string}',
        query_mappings='', credentials=f'key={SECRET}')


def run(provider, searcher, status_code, json_body=None):
    """Run the connector for one search by searcher; return (connector, URL sent)."""
    search = Search.objects.create(owner=searcher, query_string='x', query_string_processed='x',
                                   searchprovider_list=[provider.id])
    connector = RequestsGet(provider.id, search.id, False, '')
    connector.start_time = time.time()
    connector.process_query()
    connector.construct_query()
    response = mock.Mock(status_code=status_code, reason='reason text')
    response.json.return_value = json_body if json_body is not None else {}
    with mock.patch.object(connector, 'send_request', return_value=response) as send:
        connector.execute_search()
    return connector, search, send.call_args.args[0]


def test_the_request_still_carries_the_credential(provider, searcher):
    _, _, sent_url = run(provider, searcher, 500)

    assert f'key={SECRET}' in sent_url


def test_a_failed_request_saves_no_credential_value(provider, searcher):
    _, search, _ = run(provider, searcher, 500)

    result = Result.objects.get(search_id=search)
    assert result.owner == searcher
    saved = result.query_to_provider + str(result.messages)
    assert SECRET not in saved
    assert CREDENTIAL_PLACEHOLDER in result.query_to_provider
    assert 'returned: 500' in str(result.messages)


def test_the_results_api_shows_no_credential_value(provider, searcher):
    run(provider, searcher, 500)
    client = APIClient()
    client.force_authenticate(user=searcher)

    response = client.get('/swirl/results/')

    assert response.status_code == 200
    assert 'keyed source' in response.content.decode()
    assert SECRET not in response.content.decode()


def test_the_log_shows_no_credential_value(provider, searcher, caplog):
    with caplog.at_level('DEBUG'):
        run(provider, searcher, 500)

    assert 'returned: 500' in caplog.text
    assert SECRET not in caplog.text


class TestWithholdCredentials:

    @pytest.fixture
    def connector(self, provider, searcher):
        search = Search.objects.create(owner=searcher, query_string='x', searchprovider_list=[provider.id])
        return RequestsGet(provider.id, search.id, False, '')

    def test_each_value_is_replaced(self, connector):
        connector.provider.credentials = 'key=first-value, token=second-value'

        text = connector.withhold_credentials('a first-value b second-value c')

        assert text == f'a {CREDENTIAL_PLACEHOLDER} b {CREDENTIAL_PLACEHOLDER} c'

    def test_a_url_encoded_value_is_replaced(self, connector):
        connector.provider.credentials = 'key=va lue/with+signs'

        text = connector.withhold_credentials('http://h/s?key=va+lue%2Fwith%2Bsigns&q=x')

        assert text == f'http://h/s?key={CREDENTIAL_PLACEHOLDER}&q=x'

    def test_a_value_too_short_to_tell_apart_is_left_alone(self, connector):
        connector.provider.credentials = 'page=1'

        assert connector.withhold_credentials('page 1 of 10') == 'page 1 of 10'

    @pytest.mark.parametrize('credentials', ['', 'HTTPBasicAuth(user,pass)', 'no-equals-sign'])
    def test_other_credential_forms_change_nothing(self, connector, credentials):
        connector.provider.credentials = credentials

        assert connector.withhold_credentials('some text') == 'some text'

    def test_text_that_is_not_a_string_is_returned_as_is(self, connector):
        assert connector.withhold_credentials(None) is None
