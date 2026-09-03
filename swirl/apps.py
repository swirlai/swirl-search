from django.apps import AppConfig
from django.db.models.signals import post_migrate

from swirl_server.log_config import setup_logging

class SwirlConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'swirl'

    def ready(self):
        print ("setting up logging...")
        setup_logging()
        print ("setting up logging DONE")
        post_migrate.connect(ensure_backstage_group, sender=self)


def ensure_backstage_group(sender, **kwargs):
    """Create the 'Backstage Users' group with the normal search permissions.

    Runs on post_migrate so the group and its permissions exist on a fresh
    database before the first Backstage token arrives. swirl/backstage_bearer.py
    also creates it on demand, so an older database that has not migrated since
    still works.
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        from swirl.backstage_bearer import get_backstage_group
        get_backstage_group()
    except Exception as err:
        logger.warning(f"ensure_backstage_group: skipped: {err}")
