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

import math
import time

from jsonpath_ng import parse
from jsonpath_ng.exceptions import JsonPathParserError

from swirl.connectors.mappings import RESPONSE_MAPPING_KEYS

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
        self.search = get_search_obj(id=search_id) # get the search object so we can decorate the search request if needed

    def send_request(self, url, params=None, query=None, **kwargs):
        if isinstance(query, dict):
            # query is pre-built JSON body with pagination params
            # called from our paginated execute_search()
            built_json = query
        else:
            # query is raw search string (original behavior from parent's execute_search)
            built_json = {
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
            }
            # handle date sort express
            if self.search and self.search.sort == 'date':
                built_json["requests"][0]["orderby"] = self.query_mappings.get("DATE_SORT",
                                                                                DEFAULT_DATESORT_X)
        return super().send_request(url, params=params, query=built_json, **kwargs)

    ########################################

    def execute_search(self, session):
        """
        Override to implement proper POST-based pagination for the Microsoft Graph Search API.
        The parent's Requests.execute_search() uses URL-based pagination (PAGE in query_mappings),
        which doesn't work for the POST-based Graph Search API beta/search/query endpoint.
        This method uses Graph's offset-based paging (from, size) to fetch multiple result pages.
        """

        # ---- Auth setup ----
        self.provider.credentials = f"bearer={session['microsoft_access_token']}"
        (username, password, verify_certs, ca_certs, bearer) = self.get_creds(def_verify_certs=True)
        if not bearer:
            self.error("M365SearchQuery failed: no bearer token")
            return
        headers = self._put_configured_headers({"Authorization": f"Bearer {bearer}"})
        verify_param = ca_certs if ca_certs else verify_certs

        # ---- Pagination setup ----
        # Graph API limits: message/event/chatMessage max 25, driveItem/site max 1000
        if self.entity_type in ('message', 'event', 'chatMessage'):
            max_page_size = 25
        else:
            max_page_size = 200  # driveItem, site — 200 is a good balance for latency

        results_needed = max(self.provider.results_per_query, 1)
        page_size = min(results_needed, max_page_size)
        max_pages = math.ceil(results_needed / page_size)

        self.found = 0
        all_results = []
        from_offset = 0
        more_available = True

        for page_num in range(max_pages):
            if not more_available:
                break

            # Build POST body with pagination
            json_body = {
                "requests": [
                    {
                        "entityTypes": [self.entity_type],
                        "query": {
                            "queryString": f'({self.query_string_to_provider}) AND (NOT contenttype:folder)'
                        },
                        "from": from_offset,
                        "size": page_size
                    }
                ]
            }
            if self.search and self.search.sort == 'date':
                json_body["requests"][0]["orderby"] = self.query_mappings.get(
                    "DATE_SORT", DEFAULT_DATESORT_X
                )

            # ---- Send request ----
            try:
                response = self.send_request(
                    self.provider.url,
                    query=json_body,
                    headers=headers,
                    verify=verify_param
                )
            except Exception as err:
                self.error(f"M365 search page {page_num + 1} request failed: {err}")
                break

            if not response or response.status_code != 200:
                self.error(
                    f"M365 search page {page_num + 1} returned "
                    f"HTTP {response.status_code if response else 'none'}"
                )
                break

            try:
                json_data = response.json()
            except ValueError as err:
                self.error(f"M365 search page {page_num + 1} response not valid JSON: {err}")
                break

            # ---- Response processing (adapted from Requests.execute_search) ----
            mapped_response = {}
            for mapping_key in RESPONSE_MAPPING_KEYS:
                if mapping_key == 'RESULT':
                    continue
                if mapping_key not in self.response_mappings:
                    continue
                try:
                    jxp_key = f"$.{self.response_mappings[mapping_key]}"
                    jxp = parse(jxp_key)
                    matches = [match.value for match in jxp.find(json_data)]
                except (JsonPathParserError, Exception) as err:
                    self.error(f'JsonPathParser: {err}')
                    continue
                if matches:
                    if len(matches) == 1:
                        mapped_response[mapping_key] = matches[0]
                    else:
                        self.error(f'{mapping_key} matched {len(matches)}, expected 1')
                        break

            # Total found (from FOUND mapping → value[0].hitsContainers[0].total)
            if 'FOUND' in mapped_response:
                try:
                    self.found = int(mapped_response['FOUND'])
                except (ValueError, TypeError):
                    pass

            # Page results (from RESULTS mapping → value[0].hitsContainers[0].hits)
            page_results = mapped_response.get('RESULTS', [])
            if isinstance(page_results, dict):
                page_results = [page_results]
            elif not isinstance(page_results, list):
                page_results = []

            if not page_results:
                break  # no more results

            # Apply RESULT mapping if configured (M365 connectors don't use it)
            if 'RESULT' in self.response_mappings:
                try:
                    jxp = parse(f"$.{self.response_mappings['RESULT']}")
                    for item in page_results:
                        it_matches = [match.value for match in jxp.find(item)]
                        if it_matches and len(it_matches) == 1:
                            all_results.append(it_matches[0])
                except (JsonPathParserError, Exception) as err:
                    self.error(f'RESULT mapping: {err}')
                    break
            else:
                all_results.extend(page_results)

            # Check moreResultsAvailable to avoid unnecessary requests
            try:
                jxp = parse("$.value[0].hitsContainers[0].moreResultsAvailable")
                more_matches = [match.value for match in jxp.find(json_data)]
                if more_matches:
                    more_available = bool(more_matches[0])
                else:
                    more_available = False
            except Exception:
                more_available = False

            # Advance offset by actual results received
            from_offset += len(page_results)

            if len(all_results) >= results_needed:
                break

            # Rate limit courtesy: 10K requests / 10 min per tenant
            time.sleep(0.5)

        # ---- Finalize results ----
        self.response = all_results[:results_needed]
        self.retrieved = len(self.response)
        if self.found == 0 and self.retrieved > 0:
            self.found = self.retrieved
        self.status = 'READY'

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
