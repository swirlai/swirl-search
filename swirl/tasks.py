'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from celery import shared_task
from celery.schedules import crontab
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from swirl.models import OauthToken

import django

from swirl.processors.utils import remove_tags
from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

module_name = 'tasks.py'

from swirl.connectors import *
from swirl.models import SearchProvider
from swirl.performance_logger import *
from swirl.web_page import PageFetcherFactory
from swirl.authenticators import SWIRL_AUTHENTICATORS_DISPATCH

# use these to have the same options set for all fetches
# while developing
DEV_FETCH_OPTIONS = {
    "cache": "false",
    "headers": {
        "User-Agent": "Swirlbot/1.0 (+http://swirlaiconnect.com)"
    },
    "timeout": 10
}
FETCH_OPTIONS = DEV_FETCH_OPTIONS

@shared_task(name='rag_page_fetcher')
def page_fetcher_task(searchprovider, swirl_score, url, provider_id, body, user_query):
    from django.core.exceptions import ObjectDoesNotExist
    def get_authenticator_from_search_provider(provider_id):
        ret = None
        if not provider_id:
            logger.error(f"Blank provider ID getting fetch options")
            return ret
        try:
            search_provider_obj = SearchProvider.objects.get(id=provider_id)
            idp = search_provider_obj.authenticator
            ret = SWIRL_AUTHENTICATORS_DISPATCH.get(idp)()
        except ObjectDoesNotExist:
            logger.error(f"Could not find search provider with id {provider_id} getting fetch options")
        except KeyError as err:
            logger.error(f"KeyError encountered: {err}")
        except AttributeError:
            logger.error(f"Unexpected attribute error for {idp}")
        except Exception as err:
            logger.error(f"Unexecpected exception {err} getting fetch options")
        finally:
            return ret

    def get_page_fetcher_options_from_search_provider(provider_id):
        ret_options = {}

        if not provider_id:
            logger.error(f"Blank provider ID getting fetch options")
            return ret_options
        try:
            search_provider_obj = SearchProvider.objects.get(id=provider_id)
            ret_options = search_provider_obj.page_fetch_config_json
        except ObjectDoesNotExist:
            logger.error(f"Could not find search provider with id {provider_id} getting fetch options")
        except Exception as err:
            logger.error(f"Unexecpected exception {err} getting fetch options")

        return ret_options

    def format_result_as_page(body, url=""):
        logger.debug(f"RAG building page from result body : {body}")
        return f"body : {remove_tags(body)}", url, "Search Result", body, url, {}


    always_fallback_to_summary = getattr(settings, 'SWIRL_ALWAYS_FALL_BACK_TO_SUMMARY')
    logger.info(f"RAG {searchprovider} score: {swirl_score}")
    # try to fetch the item
    fetch_url = url
    if fetch_url:
        pf_options = get_page_fetcher_options_from_search_provider(provider_id=provider_id)
        # DEV ONLY pf_options = FETCH_OPTIONS
        pf = PageFetcherFactory.alloc_page_fetcher(url=fetch_url, options=pf_options)

        if not (pf and (page := pf.get_page())):
            if always_fallback_to_summary:
                logger.warning(f"RAG No page fetcher and fallback to summary")
                return format_result_as_page(body=body, url=url)
            return (False,)

        text_for_query = page.get_text_for_query(user_query)

        response_url = page.get_response_url()
        document_type = page.get_document_type()
        json = page.get_json()
        json = json if isinstance(json, dict) else {}
        return text_for_query, response_url, document_type, body, url, json
    else:
        logger.warning("RAG No url in item, continuing")
        if body:
            return format_result_as_page(body=body, url=url)
        return (False,)

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

    return subscriber()

@shared_task(name='update_microsoft_token')
def update_microsoft_token_task(headers):
    if headers['Authorization']:
        auth_header = headers['Authorization']
        auth_token = auth_header.split(' ')[1]
        token_obj = Token.objects.get(key=auth_token)
        token = headers['Authorizationmicrosoft']
        if token:
            try:
                logger.debug(f"{module_name}: update_microsoft_token_task: User - {token_obj.user.username}")
                microsoft_token_object, created = OauthToken.objects.get_or_create(owner=token_obj.user, defaults={'token': token})
                if not created:
                    microsoft_token_object.token = token
                    microsoft_token_object.save()
                return { 'user': token_obj.user.username, 'status': 'success' }
            except User.DoesNotExist:
                return {}
        return {}
    return {}