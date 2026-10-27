"""
Admin changelist under Django 6: the filtered changelist renders with the
filter sidebar markup. Django 6.0's changelist template change is why the old
``Django<6.0`` cap existed; 6.0.6+ renders the sidebar correctly with the
Community admin theme (checked in a browser against 6.0.8).
"""
import django
import pytest
from django.contrib.auth.models import User
from django.urls import reverse


@pytest.mark.django_db
def test_searchprovider_changelist_renders_with_filter_sidebar(client):
    admin = User.objects.create_superuser("admin-dj6", "admin@example.com", "not-a-real-password")
    client.force_login(admin)

    response = client.get(reverse("admin:swirl_searchprovider_changelist"))

    assert response.status_code == 200
    assert django.VERSION >= (6, 0, 6), django.VERSION
    html = response.content.decode()
    assert 'class="module filtered" id="changelist"' in html
    assert 'id="changelist-filter"' in html
