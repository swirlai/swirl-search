'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

from celery.utils.log import get_task_logger
from celery import shared_task
from celery.schedules import crontab
from sys import path
from os import environ
import django

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

logger = get_task_logger(__name__)
module_name = 'tasks.py'

##################################################
# installed connectors

from swirl.connectors import *

##################################################
##################################################

@shared_task(name='federate', ignore_result=True)
def federate_task(search_id, provider_id, provider_connector):
    logger.info(f'{module_name}: federate_task: {search_id}, {provider_id}, {provider_connector}')  
    # eval(provider_connector).search(provider_id, search_id)
    try:
        connector = eval(provider_connector)(provider_id, search_id)
        connector.federate()
    except NameError as err:
        message = f'Error: NameError: {err}'
        logger.error(f'{module_name}: {message}')
    except TypeError as err:
        message = f'Error: TypeError: {err}'
        logger.error(f'{module_name}: {message}')
    return 

##################################################
##################################################

from .search import search

@shared_task(name='search', ignore_result=True)
def search_task(search_id):
    logger.info(f'{module_name}: search_task: {search_id}')  
    return search(search_id)

##################################################
##################################################

from .search import rescore

@shared_task(name='rescore', ignore_result=True)
def rescore_task(search_id):
    # logger.info(f'{module_name}: rescore_task: {search_id}')  
    return rescore(search_id)

##################################################
##################################################

from .expirer import expirer

@shared_task(name='expirer')
def expirer_task():
    # logger.info(f'{module_name}: expirer_task')  
    return expirer()