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
import re

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


logger = logging.getLogger(__name__)


class GeneralRequestAPITestCase(TestCase):

    @pytest.fixture(autouse=True)
    def _init_fixtures(self, client, _request, _anonymous_request, test_suser, test_suser_pw, test_suser_anonymous, app):
        self._client = client
        self._request = _request
        self._anonymous_request = _anonymous_request
        self._test_suser = test_suser
        self._test_suser_pw = test_suser_pw
        self._test_suser_anonymous = test_suser_anonymous
        self._app = app
        self._request_api_url = self._get_request_api_url()

    def setUp(self):
        settings.CELERY_TASK_ALWAYS_EAGER = True

    def tearDown(self):
        settings.CELERY_TASK_ALWAYS_EAGER = False

    def _get_request_api_url(self):
        return ''

    def _get_connector_name(self):
        return ''

    def _get_provider_data(self):
        return {}

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
    def test_request_api(self):
        ### CHECKING FOR PARENT CLASS
        if self._get_connector_name() == '':
            return
        responses.add(responses.GET, self._request_api_url, body=json.dumps(self._mock_response()).encode('utf-8'), status=200)
        result = self._run_search()


class LibraryDatasourceTest(GeneralRequestAPITestCase):

    def _get_connector_name(self):
        return 'M365OutlookMessages'

    def _get_provider_data(self):

        return {
                    "name": "Library Mock (web/Library)",
                    "shared": True,
                    "active": True,
                    "default": True,
                    "connector": "RequestsGet",
                    "url": "https://xxx.mockable.io/rest/v2/plus/search/dc/",
                    "query_template": "{url}?q={query_string}",
                    "post_query_template": "{}",
                    "query_processors": [
                    "AdaptiveQueryProcessor"
                    ],
                    "query_mappings": "",
                    "result_grouping_field": "",
                    "result_processors": [
                        "MappingResultProcessor",
                        "CosineRelevancyResultProcessor"
                    ],
                    "response_mappings": "FOUND=info.total,RESULTS=docs",
                    "result_mappings": "date_published_display=pnx.display.creationdate[0],title=pnx.display.title[0],body=pnx.display.description[0],date_published=pnx.sort.creationdate[0],author=pnx.sort.author[0],url='https://xxx.place.edu/primo-explore/fulldisplay?docid={pnx.control.recordid[0]}&context=L&vid=XXX2',pnx.facets.creatorcontrib[*],pnx.display.publisher[*],pnx.display.edition[*],pnx.display.format[*],pnx.display.language[*],pnx.enrichment.classificationlcc[*],NO_PAYLOAD",
                    "results_per_query": 10,
                    "credentials": "",
                    "eval_credentials": "",
                    "tags": []
            }

    def _get_request_api_url(self):
        return 'https://xxx.mockable.io/rest/v2/plus/search/dc/?q=facebook'

    def _create_search(self):
        provider_id = self._create_provider()
        try:
            new_search = Search.objects.create(query_string='facebook',searchprovider_list=[provider_id],owner=self._test_suser)
        except Error as err:
            assert f'Search.create() failed: {err}'
        new_search.status = 'NEW_SEARCH'
        new_search.save()
        return new_search.id

    def _get_hits(self):
        data_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute file path for the JSON file in the 'data' subdirectory
        json_file_path = os.path.join(data_dir, 'data', 'libsystem_message_results.json')

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
        assert len(jsr) == 1
        hits = self._get_hits()
        assert jsr[0].get('title') == '<em>Facebook</em> :The Missing Manual'
        assert jsr[0].get('body') == "<em>Facebook</em> is the wildly popular, free social networking site that combines the best of blogs, online forums and groups, photosharing, clever applications, and interaction among friends. The one thing it doesn't have is a users guide to help you truly take advantage of it. Until now. <em>Facebook</em>: The Missing Manual gives you a very objective and entertaining look at everything this fascinating <em>Facebook</em> phenomenon has to offer. Teeming with high-quality color graphics, each page in this guide is uniquely designed to help you with specific <em>Facebook</em> tasks, such as signing up,"
        assert jsr[0].get('url') == "https://xxx.place.edu/primo-explore/fulldisplay?docid=[]&context=L&vid=XXX2"
        assert jsr[0].get('date_published_display') == '2008'
        assert jsr[0].get('date_published') == '2008-01-01 00:00:00'

        return True

    def _mock_response(self):
        return self._get_hits()


class DS254Test(GeneralRequestAPITestCase):

    def _get_connector_name(self):
        return 'M365OutlookMessages'

    def _get_provider_data(self):

        return     {
            "name": "Mergers & Acquisitions (web/Google PSE)",
            "active": True,
            "default": True,
            "connector": "RequestsGet",
            "url": "https://www.googleapis.com/customsearch/v1",
            "query_template": "{url}?cx={cx}&key={key}&q={query_string}",
            "query_processors": [
                "AdaptiveQueryProcessor"
            ],
            "query_mappings": "cx=b384c4e79a5394479,DATE_SORT=sort=date,PAGE=start=RESULT_INDEX,NOT_CHAR=-",
            "result_processors": [
                "MappingResultProcessor",
                "CosineRelevancyResultProcessor"
            ],
            "response_mappings": "FOUND=searchInformation.totalResults,RETRIEVED=queries.request[0].count,RESULTS=items",
            "result_mappings": "url=link,body=snippet,author=pagemap.metatags[*].['article:publisher'],cacheId,pagemap.metatags[*].['og:type'],pagemap.metatags[*].['article:tag'],pagemap.metatags[*].['og:site_name'],pagemap.metatags[*].['og:description'],NO_PAYLOAD",
            "results_per_query": 10,
            "credentials": "key=AIzaSyDvVeE-L6nCC9u-TTGuhggvSmzhtiTHJsA",
            "tags": [
                "News",
                "MergersAcquisitions"
            ]
        }

    def _get_request_api_url(self):
        return 'https://www.googleapis.com/customsearch/v1'

    def _create_search(self):
        provider_id = self._create_provider()
        try:
            new_search = Search.objects.create(query_string='technology consulting',searchprovider_list=[provider_id],owner=self._test_suser)
        except Error as err:
            assert f'Search.create() failed: {err}'
        new_search.status = 'NEW_SEARCH'
        new_search.save()
        return new_search.id

    def _get_hits(self):
        data_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute file path for the JSON file in the 'data' subdirectory
        json_file_path = os.path.join(data_dir, 'data', 'ds-254-test-result.json')

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
        assert len(jsr) == 1
        assert jsr[0].get('body', None)
        return True

    def _mock_response(self):
        return self._get_hits()

    @responses.activate
    def test_request_api(self):
        if self._get_connector_name() == '':
            return
        url_pattern = re.compile(r'https://www\.googleapis\.com/customsearch/.*')
        responses.add(responses.GET, url_pattern, body=json.dumps(self._mock_response()).encode('utf-8'), status=200)
        result = self._run_search()


class DS403Test(GeneralRequestAPITestCase):

    def _get_connector_name(self):
        return 'M365OutlookMessages'

    def _get_provider_data(self):

        return     {
            "name": "Mergers & Acquisitions (web/Google PSE)",
            "active": True,
            "default": True,
            "connector": "RequestsGet",
            "url": "https://www.googleapis.com/customsearch/v1",
            "query_template": "{url}?cx={cx}&key={key}&q={query_string}",
            "query_processors": [
                "AdaptiveQueryProcessor"
            ],
            "query_mappings": "cx=b384c4e79a5394479,DATE_SORT=sort=date,PAGE=start=RESULT_INDEX,NOT_CHAR=-",
            "result_processors": [
                "MappingResultProcessor",
                "CosineRelevancyResultProcessor"
            ],
            "response_mappings": "FOUND=searchInformation.totalResults,RETRIEVED=queries.request[0].count,RESULTS=items",
            "result_mappings": "url=link,body=snippet,author=pagemap.metatags[*].['article:publisher'],cacheId,pagemap.metatags[*].['og:type'],pagemap.metatags[*].['article:tag'],pagemap.metatags[*].['og:site_name'],pagemap.metatags[*].['og:description'],NO_PAYLOAD",
            "results_per_query": 10,
            "credentials": "key=AIzaSyDvVeE-L6nCC9u-TTGuhggvSmzhtiTHJsA",
            "tags": [
                "News",
                "MergersAcquisitions"
            ]
        }

    def _get_request_api_url(self):
        return 'https://www.googleapis.com/customsearch/v1'

    def _create_search(self):
        provider_id = self._create_provider()
        try:
            new_search = Search.objects.create(query_string='MergersAcquisitions:Microsoft blizzrd activision',searchprovider_list=[provider_id],owner=self._test_suser)
        except Error as err:
            assert f'Search.create() failed: {err}'
        new_search.status = 'NEW_SEARCH'
        new_search.save()
        return new_search.id

    def _get_hits(self):
        data_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute file path for the JSON file in the 'data' subdirectory
        json_file_path = os.path.join(data_dir, 'data', 'ds-403-test-result.json')

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
        assert len(jsr) == 1
        assert jsr[0].get('body', None)
        jsr[0]['body'].startswith("U.K. Blocks <em>Microsoft's</em> $69 Billion")
        return True

    def _mock_response(self):
        return self._get_hits()

    @responses.activate
    def test_request_api(self):
        if self._get_connector_name() == '':
            return
        url_pattern = re.compile(r'https://www\.googleapis\.com/customsearch/.*')
        responses.add(responses.GET, url_pattern, body=json.dumps(self._mock_response()).encode('utf-8'), status=200)
        result = self._run_search()

class DS254TestLocationBug1(GeneralRequestAPITestCase):

    def _get_connector_name(self):
        return 'M365OutlookMessages'

    def _get_provider_data(self):

        return     {
            "name": "Mergers & Acquisitions (web/Google PSE)",
            "active": True,
            "default": True,
            "connector": "RequestsGet",
            "url": "https://www.googleapis.com/customsearch/v1",
            "query_template": "{url}?cx={cx}&key={key}&q={query_string}",
            "query_processors": [
                "AdaptiveQueryProcessor"
            ],
            "query_mappings": "cx=b384c4e79a5394479,DATE_SORT=sort=date,PAGE=start=RESULT_INDEX,NOT_CHAR=-",
            "result_processors": [
                "MappingResultProcessor",
                "CosineRelevancyResultProcessor"
            ],
            "response_mappings": "FOUND=searchInformation.totalResults,RETRIEVED=queries.request[0].count,RESULTS=items",
            "result_mappings": "url=link,body=snippet,author=pagemap.metatags[*].['article:publisher'],cacheId,pagemap.metatags[*].['og:type'],pagemap.metatags[*].['article:tag'],pagemap.metatags[*].['og:site_name'],pagemap.metatags[*].['og:description'],NO_PAYLOAD",
            "results_per_query": 10,
            "credentials": "key=AIzaSyDvVeE-L6nCC9u-TTGuhggvSmzhtiTHJsA",
            "tags": [
                "News",
                "MergersAcquisitions"
            ]
        }

    def _get_request_api_url(self):
        return 'https://www.googleapis.com/customsearch/v1'

    def _create_search(self):
        provider_id = self._create_provider()
        try:
            new_search = Search.objects.create(query_string='Microsoft Blizzard Activision Inc',searchprovider_list=[provider_id],owner=self._test_suser)
        except Error as err:
            assert f'Search.create() failed: {err}'
        new_search.status = 'NEW_SEARCH'
        new_search.save()
        return new_search.id

    def _get_hits(self):
        data_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute file path for the JSON file in the 'data' subdirectory
        json_file_path = os.path.join(data_dir, 'data', 'ds-254-test-result-location-bug-1.json')

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
        assert len(jsr) == 1
        explain = jsr[0].get('explain', None)
        assert explain
        hits = explain.get('hits', None)
        assert hits
        title_hits = hits.get('title', None)
        assert title_hits
        assert title_hits.get('activision')[0] == 0
        assert title_hits.get('blizzard')[0] == 1
        assert title_hits.get('inc')[0] == 2
        return True

    def _mock_response(self):
        return self._get_hits()

    @responses.activate
    def test_request_api(self):
        if self._get_connector_name() == '':
            return
        url_pattern = re.compile(r'https://www\.googleapis\.com/customsearch/.*')
        responses.add(responses.GET, url_pattern, body=json.dumps(self._mock_response()).encode('utf-8'), status=200)
        result = self._run_search()


class DS254TestLocationBug2(GeneralRequestAPITestCase):

    def _get_connector_name(self):
        return 'M365OutlookMessages'

    def _get_provider_data(self):

        return     {
            "name": "Mergers & Acquisitions (web/Google PSE)",
            "active": True,
            "default": True,
            "connector": "RequestsGet",
            "url": "https://www.googleapis.com/customsearch/v1",
            "query_template": "{url}?cx={cx}&key={key}&q={query_string}",
            "query_processors": [
                "AdaptiveQueryProcessor"
            ],
            "query_mappings": "cx=b384c4e79a5394479,DATE_SORT=sort=date,PAGE=start=RESULT_INDEX,NOT_CHAR=-",
            "result_processors": [
                "MappingResultProcessor",
                "CosineRelevancyResultProcessor"
            ],
            "response_mappings": "FOUND=searchInformation.totalResults,RETRIEVED=queries.request[0].count,RESULTS=items",
            "result_mappings": "url=link,body=snippet,author=pagemap.metatags[*].['article:publisher'],cacheId,pagemap.metatags[*].['og:type'],pagemap.metatags[*].['article:tag'],pagemap.metatags[*].['og:site_name'],pagemap.metatags[*].['og:description'],NO_PAYLOAD",
            "results_per_query": 10,
            "credentials": "key=AIzaSyDvVeE-L6nCC9u-TTGuhggvSmzhtiTHJsA",
            "tags": [
                "News",
                "MergersAcquisitions"
            ]
        }

    def _get_request_api_url(self):
        return 'https://www.googleapis.com/customsearch/v1'

    def _create_search(self):
        provider_id = self._create_provider()
        try:
            new_search = Search.objects.create(query_string='Microsoft Blizzard Activision executives',searchprovider_list=[provider_id],owner=self._test_suser)
        except Error as err:
            assert f'Search.create() failed: {err}'
        new_search.status = 'NEW_SEARCH'
        new_search.save()
        return new_search.id

    def _get_hits(self):
        data_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute file path for the JSON file in the 'data' subdirectory
        json_file_path = os.path.join(data_dir, 'data', 'ds-254-test-result-location-bug-2.json')

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
        assert len(jsr) == 1
        explain = jsr[0].get('explain', None)
        assert explain
        hits = explain.get('hits', None)
        assert hits
        body_hits = hits.get('body', None)
        assert body_hits
        assert body_hits.get('microsoft')[0] == 1
        assert body_hits.get('microsoft')[1] == 12
        assert body_hits.get('executives')[0] == 2

        return True

    def _mock_response(self):
        return self._get_hits()

    @responses.activate
    def test_request_api(self):
        if self._get_connector_name() == '':
            return
        url_pattern = re.compile(r'https://www\.googleapis\.com/customsearch/.*')
        responses.add(responses.GET, url_pattern, body=json.dumps(self._mock_response()).encode('utf-8'), status=200)
        result = self._run_search()


class DS403Test(GeneralRequestAPITestCase):

    def _get_connector_name(self):
        return 'M365OutlookMessages'

    def _get_provider_data(self):

        return     {
            "name": "Mergers & Acquisitions (web/Google PSE)",
            "active": True,
            "default": True,
            "connector": "RequestsGet",
            "url": "https://www.googleapis.com/customsearch/v1",
            "query_template": "{url}?cx={cx}&key={key}&q={query_string}",
            "query_processors": [
                "AdaptiveQueryProcessor"
            ],
            "query_mappings": "cx=b384c4e79a5394479,DATE_SORT=sort=date,PAGE=start=RESULT_INDEX,NOT_CHAR=-",
            "result_processors": [
                "MappingResultProcessor",
                "CosineRelevancyResultProcessor"
            ],
            "response_mappings": "FOUND=searchInformation.totalResults,RETRIEVED=queries.request[0].count,RESULTS=items",
            "result_mappings": "url=link,body=snippet,author=pagemap.metatags[*].['article:publisher'],cacheId,pagemap.metatags[*].['og:type'],pagemap.metatags[*].['article:tag'],pagemap.metatags[*].['og:site_name'],pagemap.metatags[*].['og:description'],NO_PAYLOAD",
            "results_per_query": 10,
            "credentials": "key=AIzaSyDvVeE-L6nCC9u-TTGuhggvSmzhtiTHJsA",
            "tags": [
                "News",
                "MergersAcquisitions"
            ]
        }

    def _get_request_api_url(self):
        return 'https://www.googleapis.com/customsearch/v1'

    def _create_search(self):
        provider_id = self._create_provider()
        try:
            new_search = Search.objects.create(query_string='MergersAcquisitions:Microsoft blizzrd activision',searchprovider_list=[provider_id],owner=self._test_suser)
        except Error as err:
            assert f'Search.create() failed: {err}'
        new_search.status = 'NEW_SEARCH'
        new_search.save()
        return new_search.id

    def _get_hits(self):
        data_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute file path for the JSON file in the 'data' subdirectory
        json_file_path = os.path.join(data_dir, 'data', 'ds-403-test-result.json')

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
        assert len(jsr) == 1
        assert jsr[0].get('body', None)
        jsr[0]['body'].startswith("U.K. Blocks <em>Microsoft's</em> $69 Billion")
        return True

    def _mock_response(self):
        return self._get_hits()

    @responses.activate
    def test_request_api(self):
        if self._get_connector_name() == '':
            return
        url_pattern = re.compile(r'https://www\.googleapis\.com/customsearch/.*')
        responses.add(responses.GET, url_pattern, body=json.dumps(self._mock_response()).encode('utf-8'), status=200)
        result = self._run_search()


class LenLimitingResultProcessorTest(GeneralRequestAPITestCase):

    def _get_connector_name(self):
        return 'RequestsGet'

    def _get_provider_data(self):
        return     {
        "name": "Articles (web/YouTrack.cloud)",
        "owner": "admin",
        "shared": True,
        "active": True,
        "default": True,
        "connector": "RequestsGet",
        "url": "https://swirl.youtrack.cloud/api/articles?fields=idReadable,reporter(fullName),summary,content,attachments(name),project(name),parentArticle(summary),childArticles(summary),created,updatedBy(fullName),comments(text)",
        "query_template": "{url}&query={query_string}",
        "query_processors": [
            "AdaptiveQueryProcessor"
        ],
        "query_mappings": "",
        "result_processors": [
            "MappingResultProcessor",
            "LenLimitingResultProcessor",
            "CosineRelevancyResultProcessor",
        ],
        "response_mappings": "",
        "result_mappings": "title=summary,body=content,date_published=created,author=reporter.fullName,url='https://swirl.youtrack.cloud/articles/{idReadable}',project.name,attachments[*].name,parentArticle.summary,childArticles[*].summary,updatedBy.fullName,comments[*].text,NO_PAYLOAD",
        "results_per_query": 10,
        "credentials": "bearer=perm:c2Jz.NTQtMw==.kxnYWBWzpGV0KEOgpOeJtGTJvLMQpV",
        "eval_credentials": "",
        "tags": [
            "Articles",
            "Wiki",
            "YouTrack"
        ]
    }

    def _get_request_api_url(self):
        return 'https://swirl.youtrack.cloud/api/articles'

    def _create_search(self):
        provider_id = self._create_provider()
        try:
            new_search = Search.objects.create(query_string='knowledge management',searchprovider_list=[provider_id],owner=self._test_suser)
        except Error as err:
            assert f'Search.create() failed: {err}'
        new_search.status = 'NEW_SEARCH'
        new_search.save()
        return new_search.id

    def _get_hits(self):
        data_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the absolute file path for the JSON file in the 'data' subdirectory
        json_file_path = os.path.join(data_dir, 'data', 'youtrack-big-result.json')

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
        assert len(jsr) == 10
        for i,r in enumerate(jsr):
            assert len(jsr[i]['body']) <= 1024
        return True

    def _mock_response(self):
        return self._get_hits()

    @responses.activate
    def test_request_api(self):
        if self._get_connector_name() == '':
            return
        url_pattern = re.compile(r'https://swirl\.youtrack\.cloud/api/articles.*')
        responses.add(responses.GET, url_pattern, body=json.dumps(self._mock_response()).encode('utf-8'), status=200)
        result = self._run_search()
