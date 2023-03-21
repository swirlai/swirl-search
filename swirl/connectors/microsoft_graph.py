from sys import path
from os import environ

import django

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.connectors.mappings import *
from swirl.connectors.requestsget import RequestsGet
from swirl.authenticators.microsoft import Microsoft

########################################
########################################

class M365(RequestsGet):

    type = "M365"

    ########################################

    def __init__(self, provider_id, search_id, update):
        super().__init__(provider_id, search_id, update)
        self.provider.eval_credentials = ""
        self.provider.credentials = "bearer="
        self.authenticator = Microsoft()

    def validate_query(self, session):
        is_valid_token = self.authenticator.is_authenticated(session)
        if is_valid_token:
            return super().validate_query(session)
        self.error("M365 access token is not valid or missing")
        return False
    
    def execute_search(self, session):
        self.provider.response_mappings = 'RESULTS=value'
        self.provider.credentials = f"bearer={session['microsoft_access_token']}"
        return super().execute_search(session)


class M365OutlookMessages(M365):

    type = "M365OutlookMessages"

    ########################################

    def __init__(self, provider_id, search_id, update):
        super().__init__(provider_id, search_id, update)
        self.provider.url = 'https://graph.microsoft.com/v1.0'

class M365OutlookCalendar(M365):

    type = "M365OutlookCalendar"

    ########################################

    def __init__(self, provider_id, search_id, update):
        super().__init__(provider_id, search_id, update)
        self.provider.url = 'https://graph.microsoft.com/v1.0/me/events'

class M365OneDrive(M365):

    type = "M365OneDrive"

    ########################################

    def __init__(self, provider_id, search_id, update):
        super().__init__(provider_id, search_id, update)
        self.provider.url = 'https://graph.microsoft.com/v1.0/me/drive/items'


class M365SharePointSites(M365):

    type = "M365SharePointSites"

    ########################################

    def __init__(self, provider_id, search_id, update):
        super().__init__(provider_id, search_id, update)
        self.provider.url = 'https://graph.microsoft.com/v1.0/sites/'
