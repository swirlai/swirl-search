"""
DS-5772: SWIRL does not wait for ever on Microsoft.

When someone connects their Microsoft account, SWIRL redeems an authorization
code, later refreshes the token, and reads the user's profile from Microsoft
Graph. None of those requests had a time limit, so an endpoint that accepted
the connection and then never answered held the worker for as long as it
liked.

Each now gives up after ``SWIRL_IDP_REQUEST_TIMEOUT`` seconds, 30 unless set.
``0`` restores waiting without limit.

No network: ``requests`` and the sign-in library are stand-ins.
"""
from unittest.mock import MagicMock

import pytest
import requests

from swirl.authenticators import microsoft
from swirl.authenticators.microsoft import Microsoft

DEFAULT = 30


@pytest.fixture
def sign_in_library(monkeypatch):
    """Stands in for msal's client: records how it was built."""
    built = []

    def client(**kwargs):
        built.append(kwargs)
        app = MagicMock()
        app.acquire_token_by_refresh_token.return_value = {}
        return app
    monkeypatch.setattr(microsoft.msal, 'ConfidentialClientApplication', client)
    return built


@pytest.fixture
def graph(monkeypatch):
    """Stands in for Microsoft Graph: records how long SWIRL said it would
    wait. Set ``silent`` and it never answers."""
    calls = []
    state = MagicMock(silent=False)

    def get(url, **kwargs):
        calls.append({'url': url, 'timeout': kwargs.get('timeout', 'NOT SET')})
        if state.silent:
            raise requests.exceptions.ReadTimeout(f'no answer from {url}')
        response = MagicMock()
        response.json.return_value = {'mail': 'alice@example.com'}
        return response
    monkeypatch.setattr(microsoft.requests, 'get', get)
    state.calls = calls
    return state


class TestRequestsHaveATimeLimit:

    def test_the_client_that_redeems_codes_and_refreshes_tokens(self, sign_in_library):
        Microsoft()._get_auth_app()

        assert len(sign_in_library) == 1
        assert sign_in_library[0]['timeout'] == DEFAULT

    def test_refreshing_a_token_uses_that_client(self, sign_in_library):
        Microsoft().update_access_from_refresh_token(MagicMock(), 'the-refresh-token')

        assert [built['timeout'] for built in sign_in_library] == [DEFAULT]

    def test_reading_the_user_profile(self, graph):
        Microsoft().get_user('the-access-token')

        assert [call['timeout'] for call in graph.calls] == [DEFAULT]
        assert graph.calls[0]['url'].endswith('/me')

    def test_a_profile_request_that_is_never_answered_is_an_error_not_a_hang(self, graph):
        graph.silent = True

        with pytest.raises(requests.exceptions.RequestException):
            Microsoft().get_user('the-access-token')

    def test_nothing_else_about_the_client_changes(self, sign_in_library, settings):
        settings.MICROSOFT_CLIENT_ID = 'the-client-id'

        Microsoft()._get_auth_app()

        built = dict(sign_in_library[0])
        built.pop('timeout')
        assert set(built) == {'client_id', 'client_credential', 'authority', 'token_cache'}
        assert built['client_id'] == 'the-client-id'


class TestTheSetting:

    def test_the_default_is_thirty_seconds(self, settings):
        assert hasattr(settings, 'SWIRL_IDP_REQUEST_TIMEOUT'), 'the setting is read from the environment'
        assert microsoft.idp_request_timeout() == DEFAULT

    def test_with_the_setting_missing_altogether_the_default_still_applies(self, settings):
        del settings.SWIRL_IDP_REQUEST_TIMEOUT

        assert microsoft.idp_request_timeout() == DEFAULT

    def test_it_can_be_changed(self, settings, sign_in_library, graph):
        settings.SWIRL_IDP_REQUEST_TIMEOUT = 5

        Microsoft()._get_auth_app()
        Microsoft().get_user('the-access-token')

        assert sign_in_library[0]['timeout'] == 5
        assert graph.calls[0]['timeout'] == 5

    @pytest.mark.parametrize('value', [0, '0', -1])
    def test_zero_waits_without_limit_as_before(self, settings, sign_in_library, graph, value):
        settings.SWIRL_IDP_REQUEST_TIMEOUT = value

        Microsoft()._get_auth_app()
        Microsoft().get_user('the-access-token')

        assert sign_in_library[0]['timeout'] is None
        assert graph.calls[0]['timeout'] is None

    @pytest.mark.parametrize('value', ['', 'soon', None])
    def test_a_value_that_is_not_a_number_falls_back_to_the_default(self, settings, value):
        settings.SWIRL_IDP_REQUEST_TIMEOUT = value

        assert microsoft.idp_request_timeout() == DEFAULT

    def test_a_number_given_as_text_is_taken(self, settings):
        settings.SWIRL_IDP_REQUEST_TIMEOUT = '12.5'

        assert microsoft.idp_request_timeout() == 12.5
