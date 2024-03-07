from sys import path
from os import environ

import django

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.connectors.utils import get_search_obj
from swirl.connectors.utils import get_mappings_dict
from swirl.connectors.requestsget import RequestsGet
from swirl.connectors.requestspost import RequestsPost
from swirl.authenticators.microsoft import Microsoft

########################################
########################################
DEFAULT_DATESORT_X = "createdDateTime desc"

class M365(RequestsGet):

    type = "M365"

    ########################################

    def __init__(self, provider_id, search_id, update, request_id=''):
        super().__init__(provider_id, search_id, update, request_id)
        self.provider.eval_credentials = ""
        self.provider.credentials = "bearer="
        self.authenticator = Microsoft()

    def validate_query(self, session):
        self.auth = self.authenticator.is_authenticated(session)
        return super().validate_query(session)

    def execute_search(self, session):
        self.provider.credentials = f"bearer={session['microsoft_access_token']}"
        return super().execute_search(session)

class M365Post(RequestsPost):

    type = "M365Post"

    ########################################

    def __init__(self, provider_id, search_id, update, request_id=''):
        super().__init__(provider_id, search_id, update, request_id)
        self.provider.eval_credentials = ""
        self.provider.credentials = "bearer="
        self.authenticator = Microsoft()

    def validate_query(self, session):
        self.auth = self.authenticator.is_authenticated(session)
        return super().validate_query(session)

    def execute_search(self, session):
        self.provider.credentials = f"bearer={session['microsoft_access_token']}"
        return super().execute_search(session)


class M365SearchQuery(M365Post):

    type = "M365SearchQuery"

    ########################################

    def __init__(self, provider_id, search_id, update, request_id=''):
        super().__init__(provider_id, search_id, update, request_id)
        self.provider.response_mappings = self.provider.response_mappings or 'FOUND=value[0].hitsContainers[0].total,RESULTS=value[0].hitsContainers[0].hits'
        self.response_mappings = get_mappings_dict(self.provider.response_mappings)
        self.query_mappings_mappings = get_mappings_dict(self.provider.query_mappings)
        self.provider.url = 'https://graph.microsoft.com/beta/search/query'
        self.entity_type = ""
        self.search = get_search_obj(id=search_id) # get the seach object so we can decorate the search request if needed

    def send_request(self, url, params=None, query=None, **kwargs):
        json = dict({
            "requests": [
                {
                    "entityTypes": [
                        self.entity_type
                    ],
                    "query": {
                        "queryString": f'({query}) AND (NOT contenttype:folder)'
                    }
                }
            ]
        })
        # handle date sort express
        if self.search and self.search.sort == 'date':
            json["requests"][0]["orderby"] = self.query_mappings.get("DATE_SORT",
                                                                     DEFAULT_DATESORT_X)
        return super().send_request(url, params=params, query=json, **kwargs)

class M365OutlookMessages(M365SearchQuery):

    type = "M365OutlookMessages"

    ########################################

    def __init__(self, provider_id, search_id, update, request_id=''):
        super().__init__(provider_id, search_id, update, request_id)
        self.provider.result_mappings = self.provider.result_mappings or "title=resource.subject,body=summary,date_published=resource.createdDateTime,author=resource.sender.emailAddress.name,url=resource.webLink,resource.isDraft,resource.importance,resource.hasAttachments,resource.ccRecipients[*].emailAddress[*].name,resource.replyTo[*].emailAddress[*].name,NO_PAYLOAD"
        self.result_mappings = get_mappings_dict(self.provider.result_mappings)
        self.entity_type = "message"

class M365OutlookCalendar(M365SearchQuery):

    type = "M365OutlookCalendar"

    ########################################

    def __init__(self, provider_id, search_id, update, request_id=''):
        super().__init__(provider_id, search_id, update, request_id)
        self.provider.result_mappings = self.provider.result_mappings or "title=resource.subject,body=summary,date_published=resource.start.dateTime,url='https://outlook.office.com/calendar/item/{sw_urlencode(hitId)}',resource.sensitivity,resource.type,resource.hasAttachments,NO_PAYLOAD"
        self.result_mappings = get_mappings_dict(self.provider.result_mappings)
        self.entity_type = "event"

class M365OneDrive(M365SearchQuery):

    type = "M365OneDrive"

    ########################################

    def __init__(self, provider_id, search_id, update, request_id=''):
        super().__init__(provider_id, search_id, update, request_id)
        self.provider.result_mappings = self.provider.result_mappings or "title=resource.name,body='{resource.name} - {summary}',date_published=resource.createdDateTime,url=resource.webUrl,author=resource.createdBy.user.displayName,resource.lastModifiedBy.user.displayName,resource.lastModifiedDateTime,FILE_SYSTEM,NO_PAYLOAD"
        self.result_mappings = get_mappings_dict(self.provider.result_mappings)
        self.entity_type = "driveItem"

    def send_request(self, url, params=None, query=None, **kwargs):
        return super().send_request(url, params=params, query=query, **kwargs)


class M365SharePointSites(M365SearchQuery):

    type = "M365SharePointSites"

    ########################################

    def __init__(self, provider_id, search_id, update, request_id=''):
        super().__init__(provider_id, search_id, update, request_id)
        self.provider.result_mappings = self.provider.result_mappings or "title=resource.displayName,body=summary,date_published=resource.createdDateTime,url=resource.webUrl,resource.lastModifiedDateTime,NO_PAYLOAD"
        self.result_mappings = get_mappings_dict(self.provider.result_mappings)
        self.entity_type = "site"


class MicrosoftTeams(M365SearchQuery):

    type = "MicrosoftTeams"

    ########################################

    def __init__(self, provider_id, search_id, update, request_id=''):
        super().__init__(provider_id, search_id, update, request_id)
        self.provider.result_mappings = self.provider.result_mappings or "title=summary,body=summary,date_published=resource.createdDateTime,author=resource.from.emailAddress.name,url=resource.webLink,resource.importance,resource.channelIdentity.channelId,NO_PAYLOAD"
        self.result_mappings = get_mappings_dict(self.provider.result_mappings)
        self.entity_type = "chatMessage"
