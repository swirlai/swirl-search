import os
import json
from swirl.serializers import SearchProviderSerializer
from django.conf import settings
import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.core.exceptions import ObjectDoesNotExist
from swirl.processors.transform_query_processor import TransformQueryProcessorFactory, SynonymQueryProcessor
from django.contrib.auth.models import User
import re
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
    json_file_path = os.path.join(script_dir, 'data', 'sp_post_request.json')

    # Read the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    return data

@pytest.fixture
def mock_small_result():
    return {
    "count": 3,
    "total_count": 3,
    "results": [
        {
            "names": [
                {
                    "personNameKey": 1887767,
                    "firstName": "Steven",
                    "lastName": "Pinker",
                    "name": "Steven Pinker"
                }
            ]
        },
        {
            "names": [
                {
                    "personNameKey": 3592890,
                    "firstName": "Anna",
                    "lastName": "Fisher-Pinkert",
                    "name": "Anna Fisher-Pinkert"
                }
            ]
        },
        {
            "names": [
                {
                    "personNameKey": 2217301,
                    "firstName": "Alexandra",
                    "lastName": "Pinkerson",
                    "name": "Alexandra Pinkerson"
                }
            ]
        }
    ]
}

class PostSearchProviderTestCase(TestCase):
    @pytest.fixture(autouse=True)
    def _init_fixtures(self, api_client,test_suser, test_suser_pw, search_provider_pre_query_data, mock_small_result,):
        self._api_client = api_client
        self._test_suser = test_suser
        self._test_suser_pw = test_suser_pw
        self._search_provider_pre_query = search_provider_pre_query_data
        self._mock_small_result = mock_small_result


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


    def get_data(self, url):
        response = requests.get(url)
        return response.json()

    @responses.activate
    def test_request_post(self):
        # Call the viewset
        surl = reverse('search')
        # Mock the POST request
        json_response = self._mock_small_result
        url_pattern = re.compile(r'https://xx\.apis\.it\.place\.edu/.*')
        responses.add(responses.POST, url_pattern, json=json_response, status=200)
        response = self._api_client.get(surl, {'qs': 'pinker', 'providers':1})
        assert response.status_code == 200, 'Expected HTTP status code 200'
        resp_json = response.json()
        print(resp_json)
