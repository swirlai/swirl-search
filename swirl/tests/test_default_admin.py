"""
The administrator account that ships with a new installation has a public
password. SWIRL_ADMIN_PASSWORD replaces it when migrations run, and SWIRL
warns while the shipped password is still in use.
"""

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from rest_framework.test import APIClient

from swirl import default_admin
from swirl.default_admin import SHIPPED_ADMIN_PASSWORD

NEW_PASSWORD = 'a-replacement-value-for-tests'
LOGGER = 'swirl.default_admin'


@pytest.fixture
def admin(db):
    return User.objects.create_superuser('admin', 'admin@example.com', SHIPPED_ADMIN_PASSWORD)


def warnings(caplog):
    return [r.getMessage() for r in caplog.records if r.name == LOGGER and r.levelname == 'WARNING']


class TestPasswordFromTheEnvironment:

    def test_it_replaces_the_shipped_password(self, admin, monkeypatch):
        monkeypatch.setenv('SWIRL_ADMIN_PASSWORD', NEW_PASSWORD)

        assert default_admin.apply_admin_password_from_environment() is True

        admin.refresh_from_db()
        assert admin.check_password(NEW_PASSWORD)
        assert not admin.check_password(SHIPPED_ADMIN_PASSWORD)

    def test_a_second_run_changes_nothing(self, admin, monkeypatch):
        monkeypatch.setenv('SWIRL_ADMIN_PASSWORD', NEW_PASSWORD)
        default_admin.apply_admin_password_from_environment()
        stored = User.objects.get(pk=admin.pk).password

        assert default_admin.apply_admin_password_from_environment() is False
        assert User.objects.get(pk=admin.pk).password == stored

    def test_without_the_variable_nothing_changes(self, admin, monkeypatch):
        monkeypatch.delenv('SWIRL_ADMIN_PASSWORD', raising=False)

        assert default_admin.apply_admin_password_from_environment() is False
        assert User.objects.get(pk=admin.pk).check_password(SHIPPED_ADMIN_PASSWORD)

    def test_no_account_is_created(self, db, monkeypatch, caplog):
        monkeypatch.setenv('SWIRL_ADMIN_PASSWORD', NEW_PASSWORD)

        with caplog.at_level('WARNING', logger=LOGGER):
            assert default_admin.apply_admin_password_from_environment() is False

        assert User.objects.count() == 0
        assert len(warnings(caplog)) == 1

    def test_a_renamed_administrator_is_found_through_swirl_admin_user(self, db, monkeypatch):
        chief = User.objects.create_superuser('chief', 'chief@example.com', SHIPPED_ADMIN_PASSWORD)
        monkeypatch.setenv('SWIRL_ADMIN_USER', 'chief')
        monkeypatch.setenv('SWIRL_ADMIN_PASSWORD', NEW_PASSWORD)

        assert default_admin.apply_admin_password_from_environment() is True
        assert User.objects.get(pk=chief.pk).check_password(NEW_PASSWORD)

    def test_the_value_is_never_logged(self, admin, monkeypatch, caplog):
        monkeypatch.setenv('SWIRL_ADMIN_PASSWORD', NEW_PASSWORD)

        with caplog.at_level('DEBUG'):
            default_admin.apply_admin_password_from_environment()

        assert NEW_PASSWORD not in caplog.text


class TestWarningWhileTheShippedPasswordIsInUse:

    def test_it_warns_and_names_the_account(self, admin, caplog):
        with caplog.at_level('WARNING', logger=LOGGER):
            assert default_admin.warn_if_shipped_admin_password() is True

        assert len(warnings(caplog)) == 1
        assert "'admin'" in warnings(caplog)[0] and 'SWIRL_ADMIN_PASSWORD' in warnings(caplog)[0]

    def test_no_warning_once_the_password_was_changed(self, admin, caplog):
        admin.set_password(NEW_PASSWORD)
        admin.save()

        with caplog.at_level('WARNING', logger=LOGGER):
            assert default_admin.warn_if_shipped_admin_password() is False

        assert warnings(caplog) == []

    def test_no_warning_for_an_inactive_account(self, admin):
        admin.is_active = False
        admin.save()

        assert default_admin.warn_if_shipped_admin_password() is False

    def test_no_warning_when_there_is_no_such_account(self, db):
        assert default_admin.warn_if_shipped_admin_password() is False


class TestWhenMigrationsRun:

    def test_migrate_applies_the_variable_and_then_has_nothing_to_warn_about(self, admin, monkeypatch, caplog):
        monkeypatch.setenv('SWIRL_ADMIN_PASSWORD', NEW_PASSWORD)

        with caplog.at_level('WARNING', logger=LOGGER):
            call_command('migrate', verbosity=0)

        assert User.objects.get(pk=admin.pk).check_password(NEW_PASSWORD)
        assert warnings(caplog) == []

    def test_migrate_warns_when_the_shipped_password_is_left_in_place(self, admin, monkeypatch, caplog):
        monkeypatch.delenv('SWIRL_ADMIN_PASSWORD', raising=False)

        with caplog.at_level('WARNING', logger=LOGGER):
            call_command('migrate', verbosity=0)

        assert len(warnings(caplog)) == 1

    def test_a_failure_in_the_check_does_not_stop_the_migration(self, admin, monkeypatch):
        monkeypatch.setattr(default_admin, 'apply_admin_password_from_environment',
                            lambda: (_ for _ in ()).throw(RuntimeError('boom')))

        call_command('migrate', verbosity=0)


class TestSignIn:

    def post(self, username, password):
        return APIClient().post('/swirl/login/', {'username': username, 'password': password}, format='json')

    def test_sign_in_with_the_shipped_password_still_works_and_warns(self, admin, caplog):
        with caplog.at_level('WARNING', logger=LOGGER):
            response = self.post('admin', SHIPPED_ADMIN_PASSWORD)

        assert response.status_code == 200 and response.json()['is_superuser'] is True
        assert len(warnings(caplog)) == 1

    def test_sign_in_with_a_replaced_password_does_not_warn(self, admin, caplog):
        admin.set_password(NEW_PASSWORD)
        admin.save()

        with caplog.at_level('WARNING', logger=LOGGER):
            response = self.post('admin', NEW_PASSWORD)

        assert 'token' in response.json()
        assert warnings(caplog) == []

    def test_an_ordinary_user_with_that_password_is_not_the_subject_of_the_warning(self, db, caplog):
        User.objects.create_user('someone', 'someone@example.com', SHIPPED_ADMIN_PASSWORD)

        with caplog.at_level('WARNING', logger=LOGGER):
            response = self.post('someone', SHIPPED_ADMIN_PASSWORD)

        assert 'token' in response.json()
        assert warnings(caplog) == []

    def test_a_failed_sign_in_does_not_warn(self, admin, caplog):
        with caplog.at_level('WARNING', logger=LOGGER):
            response = self.post('admin', 'wrong')

        assert 'token' not in response.json()
        assert warnings(caplog) == []
