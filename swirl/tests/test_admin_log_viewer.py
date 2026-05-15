"""
Unit tests for the admin Log Viewer page.

Covers the read-only log tail endpoint exposed at /admin/log-viewer/:
- Renders for a superuser even when log files are missing (fresh install).
- The ``?file=`` query param is whitelisted (no path traversal).
- ``?lines=`` is bounded by the documented hard cap.
- Forwarding the /swirl/ index to /admin/ still works (covers the redirect
  introduced alongside the log viewer).

Run with: pytest swirl/tests/test_admin_log_viewer.py -v
"""

import os
import pytest

from django.contrib.auth.models import User
from django.test import Client


@pytest.fixture
def superuser(db):
    return User.objects.create_user(
        username='log_admin', password='password',
        is_staff=True, is_superuser=True,
    )


@pytest.fixture
def admin_client(client, superuser):
    client.force_login(superuser)
    return client


# ---------------------------------------------------------------------------
# /admin/log-viewer/
# ---------------------------------------------------------------------------

def test_log_viewer_renders_for_superuser(admin_client):
    resp = admin_client.get('/admin/log-viewer/')
    assert resp.status_code == 200
    # Tab strip + the default tab label are present.
    assert b'Log Viewer' in resp.content
    assert b'lv-tabs' in resp.content


def test_log_viewer_unknown_file_falls_back_to_default(admin_client):
    # Path-traversal attempt — must fall back to the first whitelisted file,
    # not read anything off the filesystem outside logs/.
    resp = admin_client.get('/admin/log-viewer/?file=../../etc/passwd')
    assert resp.status_code == 200
    assert b'lv-tab-selected' in resp.content
    # The selected tab should be 'django' (the first whitelisted file),
    # not the bogus query value.
    assert b'>django</a>' in resp.content


def test_log_viewer_lines_clamped_to_max(admin_client):
    # ?lines=99999 must clamp to the documented cap (5000) so a stray
    # query string can't trigger a multi-second render.
    resp = admin_client.get('/admin/log-viewer/?lines=99999')
    assert resp.status_code == 200
    # The input field reflects the clamped value.
    assert b'value="5000"' in resp.content


def test_log_viewer_lines_minimum_enforced(admin_client):
    # ?lines=0 must clamp to the minimum (50). Otherwise the page would
    # render an empty pane and look broken.
    resp = admin_client.get('/admin/log-viewer/?lines=0')
    assert resp.status_code == 200
    assert b'value="50"' in resp.content


def test_log_viewer_redirects_anonymous(client):
    # Django admin always sends unauthenticated users to /admin/login/ —
    # this confirms our extra URL is wrapped by admin.site.admin_view().
    resp = client.get('/admin/log-viewer/')
    assert resp.status_code in (302, 301)
    assert '/admin/login' in resp['Location']


# ---------------------------------------------------------------------------
# /swirl/ → /admin/ redirect (companion change to the log viewer)
# ---------------------------------------------------------------------------

def test_swirl_index_redirects_to_admin(client):
    resp = client.get('/swirl/')
    assert resp.status_code in (302, 301)
    assert resp['Location'] == '/admin/'
