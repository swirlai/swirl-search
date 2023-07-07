'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ

from celery.utils.log import get_task_logger
from celery import shared_task
from celery.schedules import crontab

import django

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

logger = get_task_logger(__name__)
module_name = 'tasks.py'

from swirl.connectors import *
from swirl.models import SearchProvider

SWIRL_OBJECT_LIST = SearchProvider.CONNECTOR_CHOICES

SWIRL_OBJECT_DICT = {}
# DS-612
for t in SWIRL_OBJECT_LIST:
    SWIRL_OBJECT_DICT[t[0]]=eval(t[0])

##################################################
##################################################

@shared_task(name='federate', ignore_result=True)
def federate_task(search_id, provider_id, provider_connector, update, session):
    logger.info(f"{module_name}: federate_task: {search_id}_{provider_id}_{provider_connector} update: {update}")
    try:
        # DS-612
        connector = eval(provider_connector, {"provider_connector": provider_connector, "__builtins__": None}, SWIRL_OBJECT_DICT)(provider_id, search_id, update)
        connector.federate(session)
    except NameError as err:
        message = f'Error: NameError: {err}'
        logger.error(f'{module_name}: {message}')
    except TypeError as err:
        message = f'Error: TypeError: {err}'
        logger.error(f'{module_name}: {message}')
    return

##################################################


@shared_task(name='search', ignore_result=True)
def search_task(search_id, session):
    from swirl.search import search

    logger.info(f"{module_name}: search_task: {search_id}")
    return search(search_id, session)

##################################################


@shared_task(name='rescore', ignore_result=True)
def rescore_task(search_id):
    from swirl.search import rescore

    logger.info(f"{module_name}: rescore_task: {search_id}")
    return rescore(search_id)

##################################################


@shared_task(name='expirer')
def expirer_task():
    from swirl.expirer import expirer

    logger.info(f"{module_name}: expirer()")
    return expirer()

##################################################


@shared_task(name='subscriber')
def subscriber_task():
    from swirl.subscriber import subscriber

    logger.info(f"{module_name}: subscriber()")
    return subscriber()
