import swirl_server.settings as settings
import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.models import User

import logging
## General and shared

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_suser_pw():
    return 'password'

@pytest.fixture
def test_suser(test_suser_pw):
    return User.objects.create_user(
        username='admin',
        password=test_suser_pw,
        is_staff=True,  # Set to True if your view requires a staff user
        is_superuser=True,  # Set to True if your view requires a superuser
    )

class SearchTestCase(TestCase):
    @pytest.fixture(autouse=True)
    def _init_fixtures(self, api_client,test_suser, test_suser_pw):
        self._api_client = api_client
        self._test_suser = test_suser
        self._test_suser_pw = test_suser_pw

    def setUp(self):
        settings.CELERY_TASK_ALWAYS_EAGER = True

    def tearDown(self):
        settings.CELERY_TASK_ALWAYS_EAGER = False

    def test_query_search_viewset_search(self):
        is_logged_in = self._api_client.login(username=self._test_suser.username, password=self._test_suser_pw)
        # Check if the login was successful
        assert is_logged_in, 'Client login failed'
        # Call the viewset
        surl = reverse('search')
        # DN: FIX ME: finish this test, commented out now to avoid errors
        # response = self._api_client.get(surl, {'qs': 'notebook', 'pre_query_processor':'foo.bar'})
