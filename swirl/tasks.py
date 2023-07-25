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
from swirl.perfomance_logger import *

##################################################
##################################################

@shared_task(name='federate', ignore_result=True)
def federate_task(search_id, provider_id, provider_connector, update, session, request_id):
    logger.debug(f"{module_name}: federate_task: {search_id}_{provider_id}_{provider_connector} update: {update} request_id {request_id}")
    try:
        with ProviderQueryRequestLogger(provider_connector+'_'+str(provider_id), request_id):
            connector = alloc_connector(connector=provider_connector)(provider_id, search_id, update, request_id=request_id)
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

    logger.debug(f"{module_name}: search_task: {search_id}")
    return search(search_id, session)

##################################################

@shared_task(name='expirer')
def expirer_task():
    from swirl.expirer import expirer

    logger.debug(f"{module_name}: expirer()")
    return expirer()

##################################################


@shared_task(name='subscriber')
def subscriber_task():
    from swirl.subscriber import subscriber

    logger.debug(f"{module_name}: subscriber()")
    return subscriber()
