"""
DS-5772: what the Microsoft authenticator writes to the log.

The log lines for connecting a Microsoft account and refreshing its token
say what happened (a token was received, or the error Microsoft returned)
and carry no token values. A refresh can still be followed in the log.
"""
import logging
from unittest.mock import MagicMock

import pytest

from swirl.authenticators import microsoft
from swirl.authenticators.microsoft import Microsoft

ACCESS = 'ACCESS-TOKEN-eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.payload.signature'
REFRESH = 'REFRESH-TOKEN-0.AXoA1234567890abcdefghijklmnopqrstuvwxyz'
OLD_ACCESS = 'OLD-ACCESS-TOKEN-previous-value'
OLD_REFRESH = 'OLD-REFRESH-TOKEN-previous-value'
ID_TOKEN = 'ID-TOKEN-eyJhbGciOiJSUzI1NiJ9.identity.signature'
SECRETS = (ACCESS, REFRESH, OLD_ACCESS, OLD_REFRESH, ID_TOKEN)


@pytest.fixture
def client(monkeypatch):
    """Stands in for the sign-in library's client. Set ``client.result`` to
    what Microsoft answers."""
    app = MagicMock()
    app.result = {'access_token': ACCESS, 'refresh_token': REFRESH, 'expires_in': 3600}
    app.acquire_token_by_refresh_token.side_effect = lambda *a, **k: app.result
    app.acquire_token_by_auth_code_flow.side_effect = lambda *a, **k: app.result
    monkeypatch.setattr(microsoft.msal, 'ConfidentialClientApplication', lambda **kwargs: app)
    monkeypatch.setattr(Microsoft, 'update_oauth_token_in_db', lambda self, *a, **k: None)
    return app


def request_with_session(tokens=True):
    request = MagicMock()
    session = {}
    if tokens:
        session['user'] = {'microsoft_access_token': OLD_ACCESS, 'microsoft_refresh_token': OLD_REFRESH,
                           'microsoft_access_token_expiration_time': 1,
                           'owner_id': request.user.id}

    class Session(dict):
        def save(self):
            pass
    request.session = Session(session)
    request.GET = {}
    return request


def everything_logged(caplog):
    return '\n'.join(record.getMessage() for record in caplog.records)


def assert_no_token_in(text):
    for secret in SECRETS:
        assert secret not in text


@pytest.fixture
def log(caplog):
    caplog.set_level(logging.DEBUG)
    return caplog


class TestRefreshingAToken:

    def test_the_background_refresh_logs_no_token(self, client, log):
        Microsoft().update_access_from_refresh_token(MagicMock(), OLD_REFRESH)

        assert_no_token_in(everything_logged(log))

    def test_the_background_refresh_still_says_it_happened(self, client, log):
        Microsoft().update_access_from_refresh_token(MagicMock(), OLD_REFRESH)

        assert 'refresh' in everything_logged(log).lower()

    def test_a_refresh_during_a_request_logs_no_token_and_no_session_data(self, client, log):
        result = Microsoft().update_token(request_with_session())

        assert result is True
        assert_no_token_in(everything_logged(log))

    def test_a_refresh_that_microsoft_refuses_logs_the_reason_not_the_response(self, client, log):
        client.result = {'error': 'invalid_grant', 'error_description': 'AADSTS70008: The refresh token has expired.',
                         'id_token': ID_TOKEN, 'refresh_token': REFRESH}

        Microsoft().update_access_from_refresh_token(MagicMock(), OLD_REFRESH)

        logged = everything_logged(log)
        assert 'invalid_grant' in logged
        assert_no_token_in(logged)


class TestAConnectionThatComesBackWithoutAnAccessToken:

    def failed_callback(self, client):
        client.result = {'error': 'invalid_client', 'error_description': 'AADSTS7000215: Invalid client secret provided.',
                         'id_token': ID_TOKEN, 'refresh_token': REFRESH, 'correlation_id': 'c0ffee'}
        with pytest.raises(ValueError) as raised:
            Microsoft().callback(request_with_session(tokens=False))
        return raised.value

    def test_the_log_names_the_error_microsoft_gave(self, client, log):
        self.failed_callback(client)

        logged = everything_logged(log)
        assert 'invalid_client' in logged
        assert 'AADSTS7000215' in logged

    def test_the_log_does_not_hold_the_whole_response(self, client, log):
        self.failed_callback(client)

        assert_no_token_in(everything_logged(log))

    def test_the_error_that_is_raised_does_not_hold_it_either(self, client, log):
        """An unhandled error is written to the log with its message."""
        error = self.failed_callback(client)

        assert_no_token_in(str(error))
        assert_no_token_in(repr(error))
        assert 'invalid_client' in str(error)

    def test_a_response_with_no_error_fields_is_still_reported(self, client, log):
        client.result = {'refresh_token': REFRESH}

        with pytest.raises(ValueError) as raised:
            Microsoft().callback(request_with_session(tokens=False))

        assert_no_token_in(str(raised.value))
        assert_no_token_in(everything_logged(log))
        assert 'access token' in everything_logged(log).lower()

    def test_a_very_long_description_is_cut_short(self, client, log):
        client.result = {'error': 'server_error', 'error_description': 'x' * 5000}

        with pytest.raises(ValueError) as raised:
            Microsoft().callback(request_with_session(tokens=False))

        assert len(str(raised.value)) < 600


class TestASuccessfulConnection:

    def test_it_logs_no_token(self, client, log, monkeypatch):
        monkeypatch.setattr(Microsoft, 'get_user', lambda self, token: {'mail': 'alice@example.com'})

        response = Microsoft().callback(request_with_session(tokens=False))

        assert response.status_code == 302
        assert_no_token_in(everything_logged(log))
