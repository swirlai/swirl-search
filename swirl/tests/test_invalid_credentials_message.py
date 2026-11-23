"""
The "invalid credentials" error for a SearchProvider.

Connectors built on ``VerifyCertsCommon`` read the SearchProvider's
credentials string. When an entry in it is not in a recognised form, the
error says which entry is wrong and what forms are accepted. It does not
repeat the credentials.
"""
import logging
from types import SimpleNamespace

import pytest

from swirl.connectors.verify_ssl_common import VerifyCertsCommon

PASSWORD = 'S3cr3t-Pa55word-example'
BEARER = 'eyJhbGciOiJSUzI1NiJ9.example-access-token.signature'
API_KEY = 'example-key-0123456789abcdef'
VALUES = (PASSWORD, BEARER, API_KEY)


def connector(credentials):
    """A connector with the given credentials that touches no database."""
    c = object.__new__(VerifyCertsCommon)
    c.type = 'Elastic'
    c.search_id = 7
    c.provider_id = 3
    c.provider = SimpleNamespace(credentials=credentials)
    c.messages = []
    c.status = ''
    c.save_results = lambda: None
    return c


def reported(c, caplog):
    """All the text the error produced: the log and the search's messages."""
    return '\n'.join([record.getMessage() for record in caplog.records] + list(c.messages))


MALFORMED = {
    'a bearer token with something unrecognised after it': f'bearer={BEARER},not-a-setting',
    'an empty bearer token after a password': f'elastic:{PASSWORD},bearer=',
    'a password with no user name': f':{PASSWORD}',
    'a key under a name the connector does not know': f'X-Api-Key={API_KEY}',
    'a single word': PASSWORD,
    'an unknown setting after valid credentials': f'elastic:{PASSWORD},verify=true',
}


class TestTheErrorDoesNotRepeatTheCredentials:

    @pytest.mark.parametrize('case', sorted(MALFORMED))
    def test_no_part_of_the_credentials_is_reported(self, case, caplog):
        c = connector(MALFORMED[case])

        with caplog.at_level(logging.DEBUG):
            c.get_creds()

        assert c.status == 'ERR_INVALID_CREDENTIALS'
        text = reported(c, caplog)
        assert 'invalid credentials' in text.lower(), 'the error is still reported'
        for value in VALUES:
            assert value not in text
        assert MALFORMED[case] not in text

    def test_it_reaches_the_log_and_the_search_messages(self, caplog):
        c = connector(f'elastic:{PASSWORD},verify=true')

        with caplog.at_level(logging.ERROR):
            c.get_creds()

        assert any('invalid credentials' in r.getMessage().lower() for r in caplog.records)
        assert any('invalid credentials' in m.lower() for m in c.messages)


class TestTheErrorIsUseful:

    def test_it_says_which_entry_is_wrong(self, caplog):
        c = connector(f'elastic:{PASSWORD},verify_certs=true,oops')

        with caplog.at_level(logging.ERROR):
            c.get_creds()

        assert 'entry 3 of 3' in reported(c, caplog)

    def test_it_says_what_forms_are_accepted(self, caplog):
        c = connector('oops')

        with caplog.at_level(logging.ERROR):
            c.get_creds()

        text = reported(c, caplog)
        for form in ('username:password', 'bearer=', 'verify_certs=', 'ca_certs='):
            assert form in text


class TestValidCredentialsAreReadAsBefore:

    def test_user_name_and_password(self):
        c = connector(f'elastic:{PASSWORD}')

        assert c.get_creds() == ('elastic', PASSWORD, False, '', '')
        assert c.messages == []

    def test_bearer_token(self):
        c = connector(f'bearer={BEARER}')

        assert c.get_creds(def_verify_certs=True) == ('', '', True, '', BEARER)

    def test_password_with_certificate_settings(self):
        c = connector(f'elastic:{PASSWORD},verify_certs=false,ca_certs=/etc/ca.pem')

        assert c.get_creds(def_verify_certs=True) == ('elastic', PASSWORD, False, '/etc/ca.pem', '')

    def test_no_credentials(self):
        c = connector('')

        assert c.get_creds() == ('', '', False, '', '')
        assert c.status == ''
