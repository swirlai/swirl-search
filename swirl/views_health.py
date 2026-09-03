'''
Backstage health endpoint (TECH_DESIGN_swirl_for_backstage.md section 3.7).

GET /swirl/sapi/health/backstage/ , AllowAny, no secrets. The Backstage engine
module logs a warning at startup when this is not ok.

    {
      "ok": true,
      "redis": {"ok": true, "url": "redis://localhost:6379/0"},
      "celery_search_worker": {"ok": true, "workers": ["celery@host"]},
      "tantivy": {"ok": true, "types": [...]},
      "license": {"edition": "community", "backstage": true}
    }

The Redis URL is reported with any password stripped. Nothing else in the body
comes from configuration.
'''

import logging
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

#: How long to wait for a Celery worker to answer a ping, in seconds.
CELERY_PING_TIMEOUT = 2.0

#: Community has no license file. Enterprise replaces this in WP10.
COMMUNITY_LICENSE = {'edition': 'community', 'backstage': True}


def redact_url(url):
    '''Return the URL with any password removed, so the body carries no secret.'''
    if not url:
        return ''
    try:
        parts = urlsplit(url)
    except ValueError:
        return ''
    if not parts.hostname:
        return url
    netloc = parts.hostname
    if parts.username:
        netloc = '{}:***@{}'.format(parts.username, netloc)
    if parts.port:
        netloc = '{}:{}'.format(netloc, parts.port)
    return urlunsplit((parts.scheme, netloc, parts.path, '', ''))


def check_redis():
    url = getattr(settings, 'CELERY_BROKER_URL', '')
    row = {'ok': False, 'url': redact_url(url)}
    try:
        import redis as redis_module

        client = redis_module.Redis.from_url(url, socket_connect_timeout=2,
                                             socket_timeout=2)
        row['ok'] = bool(client.ping())
    except Exception as err:
        row['error'] = str(err)
        logger.warning('health: redis is not reachable: %s', err)
    return row


def check_celery():
    '''Ping the workers that run the search queue.

    Community runs one worker (swirl/services.py "celery-worker"), which is the
    worker that executes federate. Enterprise splits it per queue; the key name
    stays celery_search_worker on both so the engine module reads one shape.
    '''
    row = {'ok': False, 'workers': []}
    try:
        from swirl_server.celery import app

        replies = app.control.ping(timeout=CELERY_PING_TIMEOUT) or []
        workers = []
        for reply in replies:
            if isinstance(reply, dict):
                workers.extend(reply.keys())
        row['workers'] = sorted(workers)
        row['ok'] = bool(workers)
    except Exception as err:
        row['error'] = str(err)
        logger.warning('health: could not ping celery: %s', err)
    return row


def check_tantivy():
    row = {'ok': False, 'types': []}
    try:
        from swirl.tantivy_index.manager import default_manager

        row['types'] = default_manager.types()
        row['ok'] = True
    except Exception as err:
        row['error'] = str(err)
        logger.warning('health: tantivy is not readable: %s', err)
    return row


def check_license():
    '''Community has no license. Enterprise overrides this in WP10.'''
    return dict(COMMUNITY_LICENSE)


class BackstageHealthView(APIView):
    '''GET /swirl/sapi/health/backstage/'''

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        redis_row = check_redis()
        celery_row = check_celery()
        tantivy_row = check_tantivy()
        body = {
            'ok': bool(redis_row['ok'] and celery_row['ok'] and tantivy_row['ok']),
            'redis': redis_row,
            'celery_search_worker': celery_row,
            'tantivy': tantivy_row,
            'license': check_license(),
        }
        code = status.HTTP_200_OK if body['ok'] else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(body, status=code)
