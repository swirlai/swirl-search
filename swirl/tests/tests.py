from django.test import TestCase

# Create your tests here.

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.models import User, Permission
from rest_framework.authtoken.models import Token
from django.core.management import call_command

@pytest.mark.django_db
def test_user_viewset_list():

    # Set up the test client
    client = APIClient()

    test_user = User.objects.create_user(
        username='admin',
        password='password',
        is_staff=True,  # Set to True if your view requires a staff user
        is_superuser=True,  # Set to True if your view requires a superuser
    )

    is_logged_in = client.login(username='admin', password='password')

    # Check if the login was successful
    assert is_logged_in, 'Client login failed'

    # Call the viewset
    response = client.get(reverse('querytransforms/list'))

    # Check if the response is successful
    assert response.status_code == 200, 'Expected HTTP status code 200'

    # Check if the number of users in the response is correct
    print (f'DNDEBUG : {response.json}')
    # assert len(response.json()) == 1, 'Expected 2 users in the response'
