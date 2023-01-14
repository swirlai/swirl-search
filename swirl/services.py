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
        'path': 'rabbitmq-server'
    },
    {
        'name': 'django',
        'path': 'daphne swirl_server.asgi:application'
    },
    {
        'name': 'celery-worker',
        'path': 'celery -A swirl_server worker'
    },
    {
        'name': 'celery-beats',
        'path': 'celery -A swirl_server beat --scheduler django_celery_beat.schedulers:DatabaseScheduler'
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
        'path': 'rabbitmq-server'
    },
    {
        'name': 'django',
        'path': 'python manage.py runserver'
    },
    {
        'name': 'celery-worker',
        'path': 'celery -A swirl_server worker --loglevel DEBUG'
    },
    {
        'name': 'celery-beats',
        'path': 'celery -A swirl_server beat --scheduler django_celery_beat.schedulers:DatabaseScheduler'
    }
]

SWIRL_SERVICES_DEBUG_DICT = {}
for swirl_service in SWIRL_SERVICES_DEBUG:
    SWIRL_SERVICES_DEBUG_DICT[swirl_service['name']] = swirl_service['path']

