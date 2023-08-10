'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ

from celery.utils.log import get_task_logger
from celery import shared_task
from celery.schedules import crontab
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from swirl.models import MicrosoftToken


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

@shared_task(name='federate', ignore_result=False)
def federate_task(search_id, provider_id, provider_connector, update, session, request_id):
    logger.debug(f"{module_name}: federate_task: {search_id}_{provider_id}_{provider_connector} update: {update} request_id {request_id}")
    try:
        with ProviderQueryRequestLogger(provider_connector+'_'+str(provider_id), request_id):
            connector = alloc_connector(connector=provider_connector)(provider_id, search_id, update, request_id=request_id)
            return connector.federate(session)
    except NameError as err:
        message = f'Error: NameError: {err}'
        logger.error(f'{module_name}: {message}')
    except TypeError as err:
        message = f'Error: TypeError: {err}'
        logger.error(f'{module_name}: {message}')

##################################################


@shared_task(name='search', ignore_result=False)
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

@shared_task(name='update_microsoft_token')
def update_microsoft_token_task(headers):
    auth_header = headers['Authorization']
    auth_token = auth_header.split(' ')[1]
    token_obj = Token.objects.get(key=auth_token)
    token = headers['Microsoft-Authorization']
    if token:
        try:
            logger.debug(f"{module_name}: update_microsoft_token_task: User - {token_obj.user.username}")
            microsoft_token_object, created = MicrosoftToken.objects.get_or_create(owner=token_obj.user, defaults={'token': token})
            if not created:
                microsoft_token_object.token = token
                microsoft_token_object.save()
            return { 'user': token_obj.user.username, 'status': 'success' }
        except User.DoesNotExist:
            return {}
    return {}