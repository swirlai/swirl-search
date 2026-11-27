"""
The API docs page loads its script, stylesheet and icon from a named version
of the swagger-ui package, not from a moving tag.
"""

import re

import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.mark.django_db
def test_docs_page_names_a_version():
    client = Client()
    client.force_login(User.objects.create_superuser('docs_reader', 'docs_reader@example.com', 'not-a-real-password'))

    response = client.get('/swirl/api/docs/')
    html = response.content.decode()
    addresses = re.findall(r'https://cdn\.jsdelivr\.net/npm/[^"\'\s]+', html)

    assert response.status_code == 200
    assert addresses, 'the page loads the package from the CDN'
    assert '@latest' not in html
    for address in addresses:
        assert re.search(r'swagger-ui-dist@\d+\.\d+\.\d+/', address), address
