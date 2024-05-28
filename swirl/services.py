'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import logging
logger = logging.getLogger(__name__)

module_name = 'services.py'

# NOTE: ORDER BELOW IS IMPORTANT!!!
# NOTE: FIRST IN LIST IS FIRST STARTED
# NOTE: FIRST IN LIST IS LAST STOPPED

SWIRL_SERVICES = [
    {
        'name': 'redis',
        'path': 'retired : redis-server ./redis.conf',
        'default': False,
        'retired': True
    },
    {
        'name': 'django',
        'path': 'daphne -b 0.0.0.0 -p 8000 swirl_server.asgi:application',
        'default': True,
        'retired': False
    },
    {
        'name': 'celery-worker',
        'path': 'celery -A swirl_server worker',
        'default': True,
        'retired': False
    },
    {
        'name': 'celery-beats',
        'path': 'celery -A swirl_server beat --scheduler django_celery_beat.schedulers:DatabaseScheduler',
        'default': False,
        'retired': False
    }
]

SERVICES = SWIRL_SERVICES

SWIRL_SERVICES_DICT = {}
for swirl_service in SWIRL_SERVICES:
    SWIRL_SERVICES_DICT[swirl_service['name']] = swirl_service['path']

SERVICES_DICT = SWIRL_SERVICES_DICT

SWIRL_SERVICES_DEBUG = [
    {
        'name': 'redis',
        'path': 'retired : redis-server ./redis.conf',
        'default': False,
        'retired': True
    },
    {
        'name': 'django',
        'path': 'python manage.py runserver',
        'default': True,
        'retired': False
    },
    {
        'name': 'celery-worker',
        'path': 'celery -A swirl_server worker --loglevel DEBUG',
        'default': True,
        'retired': False
    },
    {
        'name': 'celery-beats',
        'path': 'celery -A swirl_server beat --scheduler django_celery_beat.schedulers:DatabaseScheduler',
        'default': False,
        'retired': False
    }
]

SWIRL_SERVICES_DEBUG_DICT = {}
for swirl_service in SWIRL_SERVICES_DEBUG:
    SWIRL_SERVICES_DEBUG_DICT[swirl_service['name']] = swirl_service['path']
