from django.test import RequestFactory, Client, TestCase
import os
from django.http import HttpResponseRedirect
from django.db import Error
import pytest
import logging
import json
from django.contrib.auth.models import User, AnonymousUser
from swirl.models import Search, Result
from swirl.authenticators.microsoft import Microsoft
from swirl.authenticators.authenticator import Authenticator
from swirl.connectors.microsoft_graph import MicrosoftTeams, M365OutlookMessages
from django.conf import settings
from swirl.search import search as search_exec
from swirl.serializers import ResultSerializer, SearchProviderSerializer
import random
import string
import responses
from unittest import mock

@pytest.fixture
def test_suser_pw():
    return 'password'

@pytest.fixture
def test_suser(test_suser_pw):
    return User.objects.create_user(
        username=''.join(random.choices(string.ascii_uppercase + string.digits, k=10)),
        password=test_suser_pw,
        is_staff=True,  # Set to True if your view requires a staff user
        is_superuser=True,  # Set to True if your view requires a superuser
    )

@pytest.fixture
def test_suser_anonymous():
    return AnonymousUser()

@pytest.fixture
def session():
    a = Microsoft()
    return {
        a.access_token_field: 'access_token',
        a.refresh_token_field: 'refresh_token',
        a.expires_in_field: 99999999999999
    }

@pytest.fixture
def _request(test_suser, session):
    r = RequestFactory()
    r.user = test_suser
    r.session = {
        'user': session
    }
    return r

@pytest.fixture
def _anonymous_request(test_suser_anonymous, session):
    r = RequestFactory()
    r.user = test_suser_anonymous
    return r

@pytest.fixture
def app():
    return Microsoft()

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def microsoft_api_url():
    return 'https://graph.microsoft.com/beta/search/query'

logger = logging.getLogger(__name__)


class MicrosoftAuthTestCase(TestCase):

    @pytest.fixture(autouse=True)
    def _init_fixtures(self, client, _request, _anonymous_request, test_suser, test_suser_pw, test_suser_anonymous, app):
        self._client = client
        self._request = _request
        self._anonymous_request = _anonymous_request
        self._test_suser = test_suser
        self._test_suser_pw = test_suser_pw
        self._test_suser_anonymous = test_suser_anonymous
        self._app = app

    def setUp(self):
        settings.CELERY_TASK_ALWAYS_EAGER = True

    def tearDown(self):
        settings.CELERY_TASK_ALWAYS_EAGER = False

    def test_user_can_login_in_microsoft(self):
        is_logged_in = self._client.login(username=self._test_suser.username, password=self._test_suser_pw)

        # Check if the login was successful
        assert is_logged_in, 'Client login failed'

        response = self._app.login(self._request)

        assert isinstance(response, HttpResponseRedirect)
        assert response.status_code == 302
        assert 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize' in response.url


    def test_non_user_can_not_login_in_microsoft(self):

        # Check if the user is anonymous
        assert not self._test_suser_anonymous.is_authenticated, 'Client is authenticated'

        response = self._app.login(self._anonymous_request)

        assert isinstance(response, HttpResponseRedirect)
        assert response.status_code == 302
        assert 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize' not in response.url


class MicrosoftAPITestCase(TestCase):

    @pytest.fixture(autouse=True)
    def _init_fixtures(self, client, _request, _anonymous_request, test_suser, test_suser_pw, test_suser_anonymous, app, microsoft_api_url):
        self._client = client
        self._request = _request
        self._anonymous_request = _anonymous_request
        self._test_suser = test_suser
        self._test_suser_pw = test_suser_pw
        self._test_suser_anonymous = test_suser_anonymous
        self._app = app
        self._microsoft_api_url = microsoft_api_url


    def setUp(self):
        settings.CELERY_TASK_ALWAYS_EAGER = True

    def tearDown(self):
        settings.CELERY_TASK_ALWAYS_EAGER = False


    def _get_connector_name(self):
        return ''

    def _get_provider_data(self):
        return {
            "name": self._get_connector_name(),
            "shared": True,
            "active": True,
            "default": True,
            "connector": self._get_connector_name(),
            "url": "",
            "query_template": "{url}",
            "query_processor": "",
            "query_processors": [
                "AdaptiveQueryProcessor"
            ],
            "query_mappings": "NOT=true,NOT_CHAR=-",
            "result_processor": "",
            "result_processors": [
                "MappingResultProcessor",
                "CosineRelevancyResultProcessor"
            ],
            "response_mappings": "",
            "result_mappings": "",
            "results_per_query": 10,
            "credentials": "",
            "eval_credentials": ""
        }

    def _get_hits(self):
        return []

    def _mock_response(self):
        return {
            'value': [
                {
                    'hitsContainers': [
                        {
                            'hits': self._get_hits()
                        }
                    ]
                }
            ]
        }

    def _create_provider(self):
        provider = self._get_provider_data()
        serializer = SearchProviderSerializer(data=provider)
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=self._test_suser)
        provider_id = serializer.data['id']
        return provider_id

    def _create_search(self):
        provider_id = self._create_provider()
        try:
            new_search = Search.objects.create(query_string='test',searchprovider_list=[provider_id],owner=self._test_suser)
        except Error as err:
            assert f'Search.create() failed: {err}'
        new_search.status = 'NEW_SEARCH'
        new_search.save()
        return new_search.id

    def _run_search(self):
        search_id = self._create_search()
        result = search_exec(search_id, Authenticator().get_session_data(self._request))
        assert result is True
        assert self._check_result(search_id) is True

    def _check_result(self, search_id):
        return True

    @responses.activate
    def test_microsoft_api(self):
        ### CHECKING FOR PARENT CLASS
        if self._get_connector_name() == '':
            return
        responses.add(responses.POST, self._microsoft_api_url, body=json.dumps(self._mock_response()).encode('utf-8'), status=200)
        result = self._run_search()


class MicrosoftOutlookMessagesAPITestCase(MicrosoftAPITestCase):

    def _get_connector_name(self):
        return 'M365OutlookMessages'

    def _get_hits(self):
        return [
            {
                'summary': 'TEST TEST TEST',
                'resource': {
                    'subject': 'TEST',
                    'createdDateTime': '2020-11-17T16:02:27Z',
                    'from': {
                        'emailAddress': {
                            'address': 'test@gmail.com'
                        }
                    }
                }
            }
        ]


class MicrosoftOutlookCalendarAPITestCase(MicrosoftAPITestCase):

    def _get_connector_name(self):
        return 'M365OutlookCalendar'

    def _get_hits(self):
        return [
            {
                'summary': 'TEST TEST TEST',
                'resource': {
                    'subject': 'TEST',
                    'start': {
                        'dateTime': '2020-11-17T16:02:27Z'
                    }
                }
            }
        ]


class MicrosoftOneDriveAPITestCase(MicrosoftAPITestCase):

    def _get_connector_name(self):
        return 'M365OneDrive'

    def _get_hits(self):
        return [
            {
                'summary': 'TEST TEST TEST',
                'resource': {
                    'name': 'TEST',
                    'createdDateTime': '2020-11-17T16:02:27Z',
                }
            }
        ]


class MicrosoftSharePointAPITestCase(MicrosoftAPITestCase):

    def _get_connector_name(self):
        return 'M365SharePointSites'

    def _get_hits(self):
        return [
            {
                'summary': 'TEST TEST TEST',
                'resource': {
                    'name': 'TEST',
                    'description': 'TEST TEST TEST',
                    'createdDateTime': '2020-11-17T16:02:27Z',
                }
            }
        ]


class MicrosoftTeamsAPITestCase(MicrosoftAPITestCase):

    def _get_connector_name(self):
        return 'MicrosoftTeams'

    def _get_hits(self):
        return [
            {
                'summary': 'TEST TEST TEST',
                'resource': {
                    'name': 'TEST',
                    'description': 'TEST TEST TEST',
                    'createdDateTime': '2020-11-17T16:02:27Z',
                    'from': {
                        'emailAddress': {
                            'address': 'test@swirl.today'
                        }
                    }
                }
            }
        ]

class MicrosoftOutlookMessagesGroupConversations(MicrosoftAPITestCase):

    def _get_connector_name(self):
        return 'M365OutlookMessages'

    def _get_provider_data(self):
        return {
            "name": self._get_connector_name(),
            "shared": True,
            "active": True,
            "default": True,
            "connector": self._get_connector_name(),
            "url": "",
            "query_template": "{url}",
            "query_processor": "",
            "query_processors": [
                "AdaptiveQueryProcessor"
            ],
            "query_mappings": "NOT=true,NOT_CHAR=-",
            "result_processor": "",
            "result_grouping_field":"resource.conversationId",
            "result_processors": [
                "MappingResultProcessor",
                "DedupeByFieldResultProcessor",
                "CosineRelevancyResultProcessor"
            ],
            "response_mappings": "",
            "result_mappings": "title=resource.subject,body=summary,date_published=resource.createdDateTime,author=resource.sender.emailAddress.name,url=resource.webLink,resource.conversationId,resource.isDraft,resource.importance,resource.hasAttachments,resource.ccRecipients[*].emailAddress[*].name,resource.replyTo[*].emailAddress[*].name,NO_PAYLOAD",
            "results_per_query": 10,
            "credentials": "",
            "eval_credentials": ""
        }

    def _get_hits(self):
        data_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute file path for the JSON file in the 'data' subdirectory
        json_file_path = os.path.join(data_dir, 'data', 'outlook_message_results.json')

        # Read the JSON file
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        return data

    def _mock_response(self):
        return self._get_hits()

    def _check_result(self, search_id):
        result_count = Result.objects.filter(search_id=search_id).count()
        # assert result_count == 1
        rs = Result.objects.get(search_id=search_id)
        assert rs.retrieved == 1
        jsr = rs.json_results
        assert jsr
        assert len(jsr) == 1
        return True




class MicrosoftOutlookMessagesGroupConversationsSkip(MicrosoftAPITestCase):

    def _get_connector_name(self):
        return 'M365OutlookMessages'

    def _get_provider_data(self):
        return {
            "name": self._get_connector_name(),
            "shared": True,
            "active": True,
            "default": True,
            "connector": self._get_connector_name(),
            "url": "",
            "query_template": "{url}",
            "query_processor": "",
            "query_processors": [
                "AdaptiveQueryProcessor"
            ],
            "query_mappings": "NOT=true,NOT_CHAR=-",
            "result_processor": "",
            "result_grouping_field":"resource.conversationId",
            "result_processors": [
                "MappingResultProcessor",
                "DedupeByFieldResultProcessor",
                "CosineRelevancyResultProcessor"
            ],
            "response_mappings": "",
            "result_mappings": "title=resource.subject,body=summary,date_published=resource.createdDateTime,author=resource.sender.emailAddress.name,url=resource.webLink,resource.conversationId,resource.isDraft,resource.importance,resource.hasAttachments,resource.ccRecipients[*].emailAddress[*].name,resource.replyTo[*].emailAddress[*].name,NO_PAYLOAD",
            "results_per_query": 10,
            "credentials": "",
            "eval_credentials": ""
        }

    def _create_search(self):
        provider_id = self._create_provider()
        try:
            new_search = Search.objects.create(query_string='test',searchprovider_list=[provider_id],owner=self._test_suser, tags = ["SW_RESULT_PROCESSOR_SKIP:DedupeByFieldResultProcessor"])
        except Error as err:
            assert f'Search.create() failed: {err}'
        new_search.status = 'NEW_SEARCH'
        new_search.save()
        return new_search.id

    def _get_hits(self):
        data_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute file path for the JSON file in the 'data' subdirectory
        json_file_path = os.path.join(data_dir, 'data', 'outlook_message_results.json')

        # Read the JSON file
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        return data

    def _check_result(self, search_id):
        result_count = Result.objects.filter(search_id=search_id).count()
        assert result_count == 1
        rs = Result.objects.get(search_id=search_id)
        jsr = rs.json_results
        assert jsr
        assert len(jsr) == 5
        return True

    def _mock_response(self):
        return self._get_hits()

class MicrosoftOutlookMessagesDatesort(MicrosoftAPITestCase):

    def _get_connector_name(self):
        return 'M365OutlookMessages'

    def _get_provider_data(self):
        return {
            "name": self._get_connector_name(),
            "shared": True,
            "active": True,
            "default": True,
            "connector": self._get_connector_name(),
            "url": "",
            "query_template": "{url}",
            "query_processor": "",
            "query_processors": [
                "AdaptiveQueryProcessor"
            ],
            "query_mappings": "NOT=true,NOT_CHAR=-",
            "result_processor": "",
            "result_grouping_field":"resource.conversationId",
            "result_processors": [
                "MappingResultProcessor",
                "DedupeByFieldResultProcessor",
                "CosineRelevancyResultProcessor"
            ],
            "response_mappings": "",
            "result_mappings": "title=resource.subject,body=summary,date_published=resource.createdDateTime,author=resource.sender.emailAddress.name,url=resource.webLink,resource.conversationId,resource.isDraft,resource.importance,resource.hasAttachments,resource.ccRecipients[*].emailAddress[*].name,resource.replyTo[*].emailAddress[*].name,NO_PAYLOAD",
            "results_per_query": 10,
            "credentials": "",
            "eval_credentials": ""
        }

    def _create_search(self):
        provider_id = self._create_provider()
        try:
            new_search = Search.objects.create(query_string='test',searchprovider_list=[provider_id],owner=self._test_suser, sort='date', tags = ["SW_RESULT_PROCESSOR_SKIP:DedupeByFieldResultProcessor"])
        except Error as err:
            assert f'Search.create() failed: {err}'
        new_search.status = 'NEW_SEARCH'
        new_search.save()
        return new_search.id

    def _get_hits(self):
        data_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute file path for the JSON file in the 'data' subdirectory
        json_file_path = os.path.join(data_dir, 'data', 'outlook_message_results.json')

        # Read the JSON file
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        return data

    def _check_result(self, search_id):
        return True

    def _mock_response(self):
        return self._get_hits()

    @mock.patch('swirl.connectors.requestspost.RequestsPost.send_request')
    def test_microsoft_api(self, mock_send_request):
        mock_result = self._get_hits()
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_result
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_send_request.return_value = mock_response
        result = self._run_search()
        mock_send_request.assert_called_with('https://graph.microsoft.com/beta/search/query', params=None,
                                             query={'requests': [{'entityTypes': ['message'], 'query': {'queryString': '(test) AND (NOT contenttype:folder)'}, 'orderby': 'createdDateTime desc'}]},
                                             headers={'Authorization': 'Bearer access_token'}, verify=True)

class MicrosoftOutlookMessagesDatesortWithQueryMapping(MicrosoftAPITestCase):

    def _get_connector_name(self):
        return 'M365OutlookMessages'

    def _get_provider_data(self):
        return {
            "name": self._get_connector_name(),
            "shared": True,
            "active": True,
            "default": True,
            "connector": self._get_connector_name(),
            "url": "",
            "query_template": "{url}",
            "query_processor": "",
            "query_processors": [
                "AdaptiveQueryProcessor"
            ],
            "query_mappings": "NOT=true,NOT_CHAR=-,DATE_SORT=my_custom_datesort desc",
            "result_processor": "",
            "result_grouping_field":"resource.conversationId",
            "result_processors": [
                "MappingResultProcessor",
                "DedupeByFieldResultProcessor",
                "CosineRelevancyResultProcessor"
            ],
            "response_mappings": "",
            "result_mappings": "title=resource.subject,body=summary,date_published=resource.createdDateTime,author=resource.sender.emailAddress.name,url=resource.webLink,resource.conversationId,resource.isDraft,resource.importance,resource.hasAttachments,resource.ccRecipients[*].emailAddress[*].name,resource.replyTo[*].emailAddress[*].name,NO_PAYLOAD",
            "results_per_query": 10,
            "credentials": "",
            "eval_credentials": ""
        }

    def _create_search(self):
        provider_id = self._create_provider()
        try:
            new_search = Search.objects.create(query_string='test',searchprovider_list=[provider_id],owner=self._test_suser, sort='date', tags = ["SW_RESULT_PROCESSOR_SKIP:DedupeByFieldResultProcessor"])
        except Error as err:
            assert f'Search.create() failed: {err}'
        new_search.status = 'NEW_SEARCH'
        new_search.save()
        return new_search.id

    def _get_hits(self):
        data_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute file path for the JSON file in the 'data' subdirectory
        json_file_path = os.path.join(data_dir, 'data', 'outlook_message_results.json')

        # Read the JSON file
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        return data

    def _check_result(self, search_id):
        return True

    def _mock_response(self):
        return self._get_hits()

    @mock.patch('swirl.connectors.requestspost.RequestsPost.send_request')
    def test_microsoft_api(self, mock_send_request):
        mock_result = self._get_hits()
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.json.return_value = mock_result
        mock_send_request.return_value = mock_response
        result = self._run_search()
        mock_send_request.assert_called_with('https://graph.microsoft.com/beta/search/query', params=None,
                                            query={'requests': [{'entityTypes': ['message'], 'query': {'queryString': '(test) AND (NOT contenttype:folder)'}, 'orderby': 'my_custom_datesort desc'}]},
                                            headers={'Authorization': 'Bearer access_token'}, verify=True)
