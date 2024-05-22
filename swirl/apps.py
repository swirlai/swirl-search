from django.apps import AppConfig

from swirl_server.log_config import setup_logging

class SwirlConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'swirl'

    def ready(self):
        print ("setting up logging...")
        setup_logging()
        print ("setting up logging DONE")
