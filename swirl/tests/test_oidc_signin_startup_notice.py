"""
DS-5772: the notice that Microsoft sign-in is not limited to one tenant is
logged when SWIRL starts, not only at the first sign-in.

With ``MICROSOFT_CLIENT_ID`` set and ``MICROSOFT_TENANT_ID`` blank, a
multi-tenant app registration lets any Entra tenant sign in (see
swirl/oidc_signin.py). That was logged once, at the first sign-in, where it is
easy to miss. It is now also logged at start-up. Sign-in itself is unchanged.
"""
import logging

import pytest
from django.apps import apps

from swirl import oidc_signin

CLIENT_ID = '00000000-aaaa-bbbb-cccc-000000000001'
TENANT = '11111111-2222-3333-4444-555555555555'
NOTICE = 'MICROSOFT_TENANT_ID is not set'


@pytest.fixture(autouse=True)
def start_clean():
    """The notice is logged once per process; start each test clean."""
    oidc_signin.clear_jwks_cache()
    yield
    oidc_signin.clear_jwks_cache()


def notices(caplog):
    return [r.getMessage() for r in caplog.records if NOTICE in r.getMessage()]


def start_up(caplog, monkeypatch):
    """What the app does when a SWIRL process starts."""
    import swirl.apps
    monkeypatch.setattr(swirl.apps, 'setup_logging', lambda: None)
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger='swirl.oidc_signin'):
        apps.get_app_config('swirl').ready()
    return notices(caplog)


class TestStartUp:

    def test_sign_in_open_to_any_tenant_is_said_at_start_up(self, settings, caplog, monkeypatch):
        settings.MICROSOFT_CLIENT_ID = CLIENT_ID
        settings.MICROSOFT_TENANT_ID = ''

        messages = start_up(caplog, monkeypatch)

        assert len(messages) == 1
        assert 'Set MICROSOFT_TENANT_ID' in messages[0]

    def test_it_is_said_once_per_process(self, settings, caplog, monkeypatch):
        settings.MICROSOFT_CLIENT_ID = CLIENT_ID
        settings.MICROSOFT_TENANT_ID = ''

        assert len(start_up(caplog, monkeypatch)) == 1
        with caplog.at_level(logging.WARNING, logger='swirl.oidc_signin'):
            oidc_signin.warn_if_any_tenant_can_sign_in()
            apps.get_app_config('swirl').ready()

        assert len(notices(caplog)) == 1, 'still only the one from start-up'

    def test_the_notice_holds_no_configuration_value(self, settings, caplog, monkeypatch):
        settings.MICROSOFT_CLIENT_ID = CLIENT_ID
        settings.MICROSOFT_TENANT_ID = ''

        (message,) = start_up(caplog, monkeypatch)

        assert CLIENT_ID not in message

    def test_nothing_is_said_when_a_tenant_is_set(self, settings, caplog, monkeypatch):
        settings.MICROSOFT_CLIENT_ID = CLIENT_ID
        settings.MICROSOFT_TENANT_ID = TENANT

        assert start_up(caplog, monkeypatch) == []

    def test_nothing_is_said_when_microsoft_sign_in_is_not_configured(self, settings, caplog, monkeypatch):
        """Without a client ID every sign-in token is refused."""
        settings.MICROSOFT_CLIENT_ID = ''
        settings.MICROSOFT_TENANT_ID = ''

        assert start_up(caplog, monkeypatch) == []

    def test_a_fault_in_the_check_does_not_stop_start_up(self, settings, monkeypatch):
        import swirl.apps
        monkeypatch.setattr(swirl.apps, 'setup_logging', lambda: None)

        def boom():
            raise RuntimeError('unexpected')
        monkeypatch.setattr(oidc_signin, 'warn_if_any_tenant_can_sign_in', boom)

        apps.get_app_config('swirl').ready()
