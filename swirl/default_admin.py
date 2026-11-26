'''
The administrator account that comes with a new installation.

The database a new installation starts from has one administrator, whose
user name and password are in the README so that a first sign-in is possible.
That password is meant to be replaced. This module:

- sets the administrator's password from SWIRL_ADMIN_PASSWORD when that is
  set, whenever migrations run (`swirl.py setup`, `swirl.py migrate`,
  `manage.py migrate`; the Docker image runs setup at every start);
- warns, at the same moment and at every sign-in, while the shipped password
  is still the one in use.

Nothing here stops a start or a sign-in.
'''

import logging
import os

logger = logging.getLogger(__name__)

#: The administrator the shipped database contains. SWIRL_ADMIN_USER names a
#: different account for installations that renamed it.
SHIPPED_ADMIN_USERNAME = 'admin'
#: The password the README gives for that account. It is here only so that
#: its continued use can be recognised.
SHIPPED_ADMIN_PASSWORD = 'password'

WARNING = (
    "The administrator account '%s' still has the password that ships with SWIRL, "
    "which is public. Change it in the admin, or set SWIRL_ADMIN_PASSWORD and run "
    "'python swirl.py setup' (the Docker image does this at every start)."
)


def admin_username():
    return os.environ.get('SWIRL_ADMIN_USER', '') or SHIPPED_ADMIN_USERNAME


def apply_admin_password_from_environment():
    """Set the administrator's password to SWIRL_ADMIN_PASSWORD when that is
    set and differs from the current one. Returns True when it was changed.
    The account is never created here."""
    from django.contrib.auth.models import User

    password = os.environ.get('SWIRL_ADMIN_PASSWORD', '')
    if not password:
        return False
    user = User.objects.filter(username=admin_username()).first()
    if user is None:
        logger.warning("SWIRL_ADMIN_PASSWORD is set but there is no account named '%s'; nothing changed",
                       admin_username())
        return False
    if user.check_password(password):
        return False
    user.set_password(password)
    user.save(update_fields=['password'])
    logger.info("The password of '%s' was set from SWIRL_ADMIN_PASSWORD", user.username)
    return True


def has_shipped_password(user):
    return bool(user and user.is_active and user.has_usable_password()
                and user.check_password(SHIPPED_ADMIN_PASSWORD))


def warn_if_shipped_admin_password():
    """Warn when the administrator account still has the shipped password.
    Returns True when the warning was given."""
    from django.contrib.auth.models import User

    user = User.objects.filter(username=admin_username()).first()
    if not has_shipped_password(user):
        return False
    logger.warning(WARNING, user.username)
    return True


def warn_at_sign_in(user, password):
    """Warn when a privileged account has just signed in with the shipped
    password. Compares the submitted text, so it costs no password hashing."""
    if user is not None and (user.is_superuser or user.is_staff) and password == SHIPPED_ADMIN_PASSWORD:
        logger.warning(WARNING, user.username)
        return True
    return False


def check_admin_account(sender=None, **kwargs):
    """post_migrate handler: apply SWIRL_ADMIN_PASSWORD, then warn if the
    shipped password is still in use. Never stops the migration."""
    try:
        apply_admin_password_from_environment()
        warn_if_shipped_admin_password()
    except Exception as err:
        logger.warning("check_admin_account: skipped: %s", err)
