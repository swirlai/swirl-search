'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import logging as logger

module_name = 'services.py'

# NOTE: ORDER BELOW IS IMPORTANT!!!
# NOTE: FIRST IN LIST IS FIRST STARTED
# NOTE: FIRST IN LIST IS LAST STOPPED

SWIRL_SERVICES = [
    {
        'name': 'rabbitmq',
        'path': 'rabbitmq-server',
        'default': True
    },
    {
        'name': 'django',
        'path': 'daphne -b 0.0.0.0 -p 8000 swirl_server.asgi:application',
        'default': True
    },
    {
        'name': 'celery-worker',
        'path': 'celery -A swirl_server worker --loglevel INFO',
        'default': True
    },
    {
        'name': 'celery-beats',
        'path': 'celery -A swirl_server beat --scheduler django_celery_beat.schedulers:DatabaseScheduler',
        'default': False
    }
]

SERVICES = SWIRL_SERVICES

SWIRL_SERVICES_DICT = {}
for swirl_service in SWIRL_SERVICES:
    SWIRL_SERVICES_DICT[swirl_service['name']] = swirl_service['path']

SERVICES_DICT = SWIRL_SERVICES_DICT

SWIRL_SERVICES_DEBUG = [
    {
        'name': 'rabbitmq',
        'path': 'rabbitmq-server',
        'default': True

    },
    {
        'name': 'django',
        'path': 'python manage.py runserver',
        'default': True
    },
    {
        'name': 'celery-worker',
        'path': 'celery -A swirl_server worker --loglevel DEBUG',
        'default': True
    },
    {
        'name': 'celery-beats',
        'path': 'celery -A swirl_server beat --scheduler django_celery_beat.schedulers:DatabaseScheduler',
        'default': False
    }
]

SWIRL_SERVICES_DEBUG_DICT = {}
for swirl_service in SWIRL_SERVICES_DEBUG:
    SWIRL_SERVICES_DEBUG_DICT[swirl_service['name']] = swirl_service['path']
