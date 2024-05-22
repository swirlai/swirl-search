import os
import json
import re
from sqlite3 import IntegrityError
from swirl.serializers import SearchProviderSerializer
from django.conf import settings
import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.core.exceptions import ObjectDoesNotExist
from swirl.processors.transform_query_processor import TransformQueryProcessorFactory, SynonymQueryProcessor
from django.contrib.auth.models import User
from unittest.mock import patch, ANY, MagicMock
import responses
import requests

## General and shared

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_suser_pw():
    return 'password'

@pytest.fixture
def test_suser(test_suser_pw):
    """
    return the user if it's aleady there, otherwise create it.
    """
    try:
        return User.objects.get(username='admin')
    except ObjectDoesNotExist:
        pass

    return User.objects.create_user(
        username='admin',
        password=test_suser_pw,
        is_staff=True,  # Set to True if your view requires a staff user
        is_superuser=True,  # Set to True if your view requires a superuser
    )

@pytest.fixture
def search_provider_pre_query_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Build the absolute file path for the JSON file in the 'data' subdirectory
    json_file_path = os.path.join(script_dir, 'data', 'sp_web_google_pse.json')

    # Read the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    return data

@pytest.fixture
def web_google_pse_sample_results_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Build the absolute file path for the JSON file in the 'data' subdirectory
    json_file_path = os.path.join(script_dir, 'data', 'web_google_pse_sample_results.json')

    # Read the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    return data


@pytest.fixture
def search_provider_query_processor_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Build the absolute file path for the JSON file in the 'data' subdirectory
    json_file_path = os.path.join(script_dir, 'data', 'sp_web_google_pse_with_qrx_processor.json')

    # Read the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    return data

@pytest.fixture
def search_provider_query_processors_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Build the absolute file path for the JSON file in the 'data' subdirectory
    json_file_path = os.path.join(script_dir, 'data', 'sp_web_google_pse_with_qrx_processors.json')

    # Read the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    return data


@pytest.fixture
def search_provider_open_search_query_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Build the absolute file path for the JSON file in the 'data' subdirectory
    json_file_path = os.path.join(script_dir, 'data', 'open_search_provider.json')

    # Read the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    return data


@pytest.fixture
def qrx_synonym_search_test():
    return {
        "name": "test one",
        "shared": True,
        "qrx_type": "synonym",
        "config_content": "# column1, column2\nnotebook, laptop\nlaptop, personal computer\npc, personal computer\npersonal computer, pc"
}

@pytest.fixture
def mock_small_result():
    return {
    "items": [
    {
      "kind": "customsearch#result",
      "title": "Notebook | Financial Times",
      "htmlTitle": "\u003cb\u003eNotebook\u003c/b\u003e | Financial Times",
      "link": "https://www.ft.com/content/b6f32818-aeda-11da-b04a-0000779e2340",
      "displayLink": "www.ft.com",
      "snippet": "Mar 8, 2006 ... We'll send you a myFT Daily Digest email rounding up the latest MG Rover Group Ltd news every morning. Patricia Hewitt once confided to Notebook ...",
      "htmlSnippet": "Mar 8, 2006 \u003cb\u003e...\u003c/b\u003e We&#39;ll send you a myFT Daily Digest email rounding up the latest MG Rover Group Ltd news every morning. Patricia Hewitt once confided to \u003cb\u003eNotebook\u003c/b\u003e&nbsp;...",
      "formattedUrl": "https://www.ft.com/content/b6f32818-aeda-11da-b04a-0000779e2340",
      "htmlFormattedUrl": "https://www.ft.com/content/b6f32818-aeda-11da-b04a-0000779e2340",
      "pagemap": {
        "cse_thumbnail": [
          {
            "src": "https://encrypted-tbn3.gstatic.com/images?q=tbn:ANd9GcSr8n8mzhsf6uFZw3uY-3pizLTj1JFydMfMwCQ3e_GZTxjRnHSAXg5apLU",
            "width": "310",
            "height": "163"
          }
        ],
      }
    }
  ]
}

class SearchQueryTransformTestCase(TestCase):
    @pytest.fixture(autouse=True)
    def _init_fixtures(self, api_client,test_suser, test_suser_pw, search_provider_pre_query_data, search_provider_query_processors_data,
                       search_provider_query_processor_data, search_provider_open_search_query_data,
                       qrx_synonym_search_test, mock_small_result, web_google_pse_sample_results_data):
        self._api_client = api_client
        self._test_suser = test_suser
        self._test_suser_pw = test_suser_pw
        self._search_provider_pre_query = search_provider_pre_query_data
        self._search_provider_query_processor = search_provider_query_processor_data
        self._search_provider_query_processors = search_provider_query_processors_data
        self._search_provider_open_search_query_data = search_provider_open_search_query_data
        self._qrx_synonym = qrx_synonym_search_test
        self._mock_result = mock_small_result
        self._web_google_pse_sample_results_data = web_google_pse_sample_results_data

    def setUp(self):
        settings.SWIRL_TIMEOUT = 1
        settings.CELERY_TASK_ALWAYS_EAGER = True
        is_logged_in = self._api_client.login(username=self._test_suser.username, password=self._test_suser_pw)
        # Check if the login was successful
        assert is_logged_in, 'Client login failed'

        # Create a search provider
        #1
        serializer = SearchProviderSerializer(data=self._search_provider_pre_query)
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=self._test_suser)
        #2
        serializer = SearchProviderSerializer(data=self._search_provider_query_processor)
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=self._test_suser)
        #3
        serializer = SearchProviderSerializer(data=self._search_provider_open_search_query_data)
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=self._test_suser)
        #4
        serializer = SearchProviderSerializer(data=self._search_provider_query_processors)
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=self._test_suser)

        # Create a query transform
        response = self._api_client.post(reverse('create'),data=self._qrx_synonym, format='json')
        assert response.status_code == 201, 'Expected HTTP status code 201'
        response = self._api_client.get(reverse('querytransforms/list'))
        assert response.status_code == 200, 'Expected HTTP status code 200'
        assert len(response.json()) == 1, 'Expected 1 transform'

    def tearDown(self):
        purl = reverse('delete', kwargs={'pk': 1})
        response = self._api_client.delete(purl)
        assert response.status_code == 410, 'Expected HTTP status code 410'
        settings.SWIRL_TIMEOUT = 10
        settings.CELERY_TASK_ALWAYS_EAGER = False

    def get_data(self, url):
        response = requests.get(url)
        return response.json()

    @responses.activate
    def test_pre_query_transform_processor(self):
        # Call the viewset
        surl = reverse('search')
        ret = TransformQueryProcessorFactory.alloc_query_transform('notebook',
                                        self._qrx_synonym.get('name'),
                                        self._qrx_synonym.get('qrx_type'),
                                        self._qrx_synonym.get('config_content'))
        mock_alloc = MagicMock(return_value=ret)
        mock_process= MagicMock(return_value = '(notebook OR laptop)')
        json_response = self._mock_result
        url_pattern = re.compile(r'https://www\.googleapis\.com/customsearch/.*')
        responses.add(responses.GET,url_pattern , json=json_response, status=200)
        with patch('swirl.processors.transform_query_processor.TransformQueryProcessorFactory.alloc_query_transform',new=mock_alloc):
            with patch('swirl.processors.transform_query_processor.SynonymQueryProcessor.process', new=mock_process):
                response = self._api_client.get(surl, {'qs': 'notebook', 'pre_query_processor':'test one.synonym','providers':1})
                mock_alloc.assert_called_once_with('notebook', 'test one','synonym', ANY)
                mock_process.assert_called_once()

    @responses.activate
    def test_query_transform_processor(self):
        # Call the viewset
        surl = reverse('search')
        ret = TransformQueryProcessorFactory.alloc_query_transform('notebook',
                                        self._qrx_synonym.get('name'),
                                        self._qrx_synonym.get('qrx_type'),
                                        self._qrx_synonym.get('config_content'))
        mock_alloc = MagicMock(return_value=ret)
        mock_process= MagicMock(return_value = '(notebook OR laptop)')
        json_response = self._mock_result
        url_pattern = re.compile(r'https://www\.googleapis\.com/customsearch/.*')
        responses.add(responses.GET,url_pattern , json=json_response, status=200)
        with patch('swirl.processors.transform_query_processor.TransformQueryProcessorFactory.alloc_query_transform',new=mock_alloc):
            with patch('swirl.processors.transform_query_processor.SynonymQueryProcessor.process', new=mock_process):
                response = self._api_client.get(surl, {'qs': 'notebook','providers':2})
                mock_alloc.assert_called_once_with('notebook', 'test one','synonym', ANY)
                mock_process.assert_called_once()

    @responses.activate
    def test_query_transform_processor_with_tag(self):
        # Call the viewset
        surl = reverse('search')
        ret = TransformQueryProcessorFactory.alloc_query_transform('notebook',
                                        self._qrx_synonym.get('name'),
                                        self._qrx_synonym.get('qrx_type'),
                                        self._qrx_synonym.get('config_content'))
        mock_alloc = MagicMock(return_value=ret)
        mock_process= MagicMock(return_value = '(notebook OR laptop)')
        json_response = self._mock_result
        url_pattern = re.compile(r'https://www\.googleapis\.com/customsearch/.*')
        responses.add(responses.GET,url_pattern , json=json_response, status=200)
        with patch('swirl.processors.transform_query_processor.TransformQueryProcessorFactory.alloc_query_transform',new=mock_alloc):
            with patch('swirl.processors.transform_query_processor.SynonymQueryProcessor.process', new=mock_process):
                response = self._api_client.get(surl, {'qs': 'xnews:notebook'})
                mock_alloc.assert_called_once_with('notebook', 'test one','synonym', ANY)
                mock_process.assert_called_once()

    @responses.activate
    def test_query_transform_processor_full_results(self):
        # Call the viewset
        surl = reverse('search')
        ret = TransformQueryProcessorFactory.alloc_query_transform('notebook',
                                        self._qrx_synonym.get('name'),
                                        self._qrx_synonym.get('qrx_type'),
                                        self._qrx_synonym.get('config_content'))
        mock_alloc = MagicMock(return_value=ret)
        mock_process= MagicMock(return_value = '(notebook OR laptop)')
        json_response = self._web_google_pse_sample_results_data
        url_pattern = re.compile(r'https://www\.googleapis\.com/customsearch/.*')
        responses.add(responses.GET,url_pattern , json=json_response, status=200)
        with patch('swirl.processors.transform_query_processor.TransformQueryProcessorFactory.alloc_query_transform',new=mock_alloc):
            with patch('swirl.processors.transform_query_processor.SynonymQueryProcessor.process', new=mock_process):
                response = self._api_client.get(surl, {'qs': 'notebook','providers':2})
                mock_alloc.assert_called_once_with('notebook', 'test one','synonym', ANY)
                mock_process.assert_called_once()
        assert response
        assert response.data.get('results', False)
        assert len(response.data['results']) == 7
        assert response.data['results'][0].get('body',False)
        assert "<em>Notebook</em>" in response.data['results'][0]['body']




################################################################################
## individual cases

## Test fixtures
@pytest.fixture
def qrx_record_1():
    return {
        "name": "xxx",
        "shared": True,
        "qrx_type": "rewrite",
        "config_content": "# This is a test\n# column1, colum2\nmobiles; ombile; mo bile, mobile\ncheapest smartphones, cheap smartphone"
}

@pytest.fixture
def qrx_synonym():
    return {
        "name": "synonym 1",
        "shared": True,
        "qrx_type": "synonym",
        "config_content": "# column1, column2\nnotebook, laptop\nlaptop, personal computer\npc, personal computer\npersonal computer, pc"
}

@pytest.fixture
def qrx_synonym_bag():
    return {
        "name": "bag 1",
        "shared": True,
        "qrx_type": "bag",
        "config_content": "# column1....columnN\nnotebook, personal computer, laptop, pc\ncar,automobile, ride"
}
@pytest.fixture
def qrx_rewrite():
    return {
        "name": "rewrite 1",
        "shared": True,
        "qrx_type": "rewrite",
        "config_content": "# This is a test\n# column1, colum2\nmobiles; ombile; mo bile, mobile\ncheapest smartphones, cheap smartphone\non"
}
@pytest.fixture
def noop_query_string():
    return "noop"
######################################################################

@pytest.mark.django_db
def test_query_transform_allocation(noop_query_string, qrx_rewrite, qrx_synonym, qrx_synonym_bag):
    ret = TransformQueryProcessorFactory.alloc_query_transform(noop_query_string,
                                        qrx_rewrite.get('name'),
                                        qrx_rewrite.get('qrx_type'),
                                        qrx_rewrite.get('config_content'))
    assert str(ret) == 'RewriteQueryProcessor'

    ret = TransformQueryProcessorFactory.alloc_query_transform(noop_query_string,
                                        qrx_rewrite.get('name'),
                                        qrx_synonym.get('qrx_type'),
                                        qrx_rewrite.get('config_content'))
    assert str(ret) == 'SynonymQueryProcessor'

    ret = TransformQueryProcessorFactory.alloc_query_transform(noop_query_string,
                                        qrx_rewrite.get('name'),
                                        qrx_synonym_bag.get('qrx_type'),
                                        qrx_rewrite.get('config_content'))
    assert str(ret) == 'SynonymBagQueryProcessor'

######################################################################
@pytest.mark.django_db
def test_query_transform_synonym_parse(noop_query_string, qrx_synonym):
    sy_qxr = TransformQueryProcessorFactory.alloc_query_transform(noop_query_string,
                                        qrx_synonym.get('name'),
                                        qrx_synonym.get('qrx_type'),
                                        qrx_synonym.get('config_content'))
    assert str(sy_qxr) == 'SynonymQueryProcessor'
    sy_qxr.parse_config()
    rps = sy_qxr.get_replace_patterns()
    assert len(rps) == 4
    assert str(rps[0]) == "<<notebook>> -> <<['laptop']>>"
    assert str(rps[1]) == "<<laptop>> -> <<['personal computer']>>"
    assert str(rps[2]) == "<<pc>> -> <<['personal computer']>>"
    assert str(rps[3]) == "<<personal computer>> -> <<['pc']>>"

######################################################################

@pytest.mark.django_db
def test_query_transform_rewwrite_parse(noop_query_string, qrx_rewrite):
    rw_qxr = TransformQueryProcessorFactory.alloc_query_transform(noop_query_string,
                                        qrx_rewrite.get('name'),
                                        qrx_rewrite.get('qrx_type'),
                                        qrx_rewrite.get('config_content'))
    assert str(rw_qxr) == 'RewriteQueryProcessor'
    rw_qxr.parse_config()
    rps = rw_qxr.get_replace_patterns()
    assert len(rps) == 5
    assert str(rps[0]) == "<<mobiles>> -> <<['mobile']>>"
    assert str(rps[1]) == "<<ombile>> -> <<['mobile']>>"
    assert str(rps[2]) == "<<mo bile>> -> <<['mobile']>>"
    assert str(rps[3]) == "<<cheapest smartphones>> -> <<['cheap smartphone']>>"
    assert str(rps[4]) == '<<\\bon\\b\\s?>> -> <<[\'\']>>'

######################################################################
@pytest.mark.django_db
def test_query_transform_synonym_bag_parse(noop_query_string, qrx_synonym_bag):
    sy_qxr = TransformQueryProcessorFactory.alloc_query_transform(noop_query_string,
                                            qrx_synonym_bag.get('name'),
                                            qrx_synonym_bag.get('qrx_type'),
                                            qrx_synonym_bag.get('config_content'))
    assert str(sy_qxr) == 'SynonymBagQueryProcessor'
    sy_qxr.parse_config()
    rps = sy_qxr.get_replace_patterns()
    assert str(rps[0]) == "<<notebook>> -> <<['personal computer', 'laptop', 'pc']>>"
    assert str(rps[1]) == "<<personal computer>> -> <<['notebook', 'laptop', 'pc']>>"
    assert str(rps[2]) == "<<laptop>> -> <<['notebook', 'personal computer', 'pc']>>"
    assert str(rps[3]) == "<<pc>> -> <<['notebook', 'personal computer', 'laptop']>>"
    assert str(rps[4]) == "<<car>> -> <<['automobile', 'ride']>>"
    assert str(rps[5]) == "<<automobile>> -> <<['car', 'ride']>>"
    assert str(rps[6]) == "<<ride>> -> <<['car', 'automobile']>>"

@pytest.fixture
def qrx_rewrite_process():
    return {
        "name": "rewrite 1",
        "shared": True,
        "qrx_type": "rewrite",
        "config_content":
        """
# This is a test
# column1, colum2
mobiles; ombile; mo bile, mobile
computers, computer
cheap.* smartphones, cheap smartphone
on
to
What is the % In-Stock for (.+?) YTD\?, [% In Stock] \\1 ‘Year to date’
"""
}
@pytest.fixture
def qrx_rewrite_test_queries():
    return ['mobile phone', 'mobiles','ombile', 'mo bile', 'on computing', 'cheaper smartphones','computers, go figure','to the moon and back','What is the % In-Stock for MST YTD?']

@pytest.fixture
def qrx_rewrite_expected_queries():
    return ['mobile phone', 'mobile','mobile', 'mobile', 'computing', 'cheap smartphone','computer go figure','the moon and back','[% In Stock] MST ‘Year to date’']
@pytest.mark.django_db
def test_query_transform_rewwrite_process(qrx_rewrite_test_queries, qrx_rewrite_expected_queries, qrx_rewrite_process):
    assert len(qrx_rewrite_test_queries) == len (qrx_rewrite_expected_queries)
    i = 0
    for q in qrx_rewrite_test_queries:
        rw_qxr = TransformQueryProcessorFactory.alloc_query_transform(
                                            q,
                                            qrx_rewrite_process.get('name'),
                                            qrx_rewrite_process.get('qrx_type'),
                                            qrx_rewrite_process.get('config_content'))
        assert str(rw_qxr) == 'RewriteQueryProcessor'
        ret = rw_qxr.process()
        assert ret == qrx_rewrite_expected_queries[i]
        i = i + 1

######################################################################
@pytest.fixture
def qrx_synonym_test_queries():
    return [
        '',
        'a',
        'robot human',
        'notebook',
        'pc',
        'personal computer',
        'I love my notebook',
        'This pc, it is better than a notebook',
        'My favorite song is "You got a fast car"'
        ]

@pytest.fixture
def qrx_synonym_expected_queries():
    return [
        '',
        'a',
        'robot human',
        '(notebook OR laptop)',
        '(pc OR personal computer)',
        '(personal computer OR pc)',
        'I love my (notebook OR laptop)',
        'This (pc OR personal computer) , it is better than a (notebook OR laptop)',
        'My favorite song is " You got a fast (car OR ride) "'
        ]

@pytest.fixture
def qrx_synonym_process():
    return {
        "name": "synonym 1",
        "shared": True,
        "qrx_type": "synonym",
        "config_content":
        """
# column1, column2
notebook, laptop
laptop, personal computer
pc, personal computer
personal computer, pc
car, ride
"""
}

@pytest.mark.django_db
def test_query_transform_synonym_process(qrx_synonym_test_queries, qrx_synonym_expected_queries, qrx_synonym_process):
    assert len(qrx_synonym_test_queries) == len(qrx_synonym_expected_queries)
    i = 0
    for q in qrx_synonym_test_queries:
        rw_qxr = TransformQueryProcessorFactory.alloc_query_transform(
                                            q,
                                            qrx_synonym_process.get('name'),
                                            qrx_synonym_process.get('qrx_type'),
                                            qrx_synonym_process.get('config_content'))
        assert str(rw_qxr) == 'SynonymQueryProcessor'
        ret = rw_qxr.process()
        assert ret == qrx_synonym_expected_queries[i]
        i = i + 1

@pytest.fixture
def qrx_synonym_bag_process():
    return {
        "name": "bag 1",
        "shared": True,
        "qrx_type": "bag",
        "config_content": """
# column1....columnN
notebook, personal computer, laptop, pc
car,automobile, ride
"""
}
######################################################################
@pytest.fixture
def qrx_synonym_bag_test_queries():
    return [
        '',
        'a',
        'machine human',
        'car',
        'automobile',
        'ride',
        'pimp my ride',
        'automobile, yours is fast',
        'I love the movie The Notebook',
        'My new notebook is slow'
        ]

@pytest.fixture
def qrx_synonym_bag_expected_queries():
    return [
        '',
        'a',
        'machine human',
        '(car OR automobile OR ride)',
        '(automobile OR car OR ride)',
        '(ride OR car OR automobile)',
        'pimp my (ride OR car OR automobile)',
        '(automobile OR car OR ride) , yours is fast',
        'I love the movie The Notebook',
        'My new (notebook OR personal computer OR laptop OR pc) is slow'
        ]

@pytest.mark.django_db
def test_query_transform_synonym_bag_process(qrx_synonym_bag_test_queries, qrx_synonym_bag_expected_queries, qrx_synonym_bag_process):
    assert len(qrx_synonym_bag_test_queries) == len(qrx_synonym_bag_expected_queries)
    i = 0
    for q in qrx_synonym_bag_test_queries:
        rw_qxr = TransformQueryProcessorFactory.alloc_query_transform(
                                            q,
                                            qrx_synonym_bag_process.get('name'),
                                            qrx_synonym_bag_process.get('qrx_type'),
                                            qrx_synonym_bag_process.get('config_content'))
        assert str(rw_qxr) == 'SynonymBagQueryProcessor'
        ret = rw_qxr.process()
        assert ret == qrx_synonym_bag_expected_queries[i]
        i = i + 1
