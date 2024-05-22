'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ
import logging
logger = logging.getLogger(__name__)

import time
import jwt

import django
from django.utils import timezone
from django.conf import settings

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

from swirl.models import Search, OauthToken
from swirl.authenticators import *
from swirl.search import search as run_search, get_query_selectd_provder_list
from datetime import datetime


module_name = 'subscriber.py'

SWIRL_SUBSCRIBE_WAIT = getattr(settings, 'SWIRL_SUBSCRIBE_WAIT', 20)

##################################################
##################################################

# def update(search_id):
#     return subscriber(search_id=search_id)

##################################################

def _get_oauth_idp_for_providers(search):
    """
    Return a list of the IDPs for the providers in the search
    """
    logger.debug(f"{module_name}: _get_oauth_idp_for_providers(search): {search.id}")
    ret = list()

    if not search:
        logger.debug(f"{module_name}: _get_oauth_idp_for_providers(search): no search")
        return ret
    selected_provider_list = get_query_selectd_provder_list(search=search)
    for provider in selected_provider_list:
        if provider.authenticator:
            ret.append(provider.authenticator)
        else:
            logger.debug(f"{module_name}: _get_oauth_idp_for_providers(search): provider : {provider.name} no authenticatr")

    return list(set(ret)) # dedup the list before return

def _get_session_for_oauth_providers(search, owner, session_data):
    """
    update session headers with current token
    """
    logger.debug(f"{module_name}: _get_session_for_oauth_providers {search.id}")
    idps = _get_oauth_idp_for_providers(search)
    logger.debug(f"{module_name}: idps {idps}")

    # Code below loops through all idps, but see error above for information
    for idp in idps:
        try:
            oauth_obj = SWIRL_AUTHENTICATORS_DISPATCH.get(idp)()
            oauth_token_obj = OauthToken.objects.get(owner=owner, idp=idp)
            session_data[oauth_obj.get_access_token_session_field()] = oauth_token_obj.token
            session_data[oauth_obj.get_access_token_expiration_time_session_field()] = int(jwt.decode(oauth_token_obj.token, options={"verify_signature": False}, algorithms=["RS256"])['exp'])
            if not oauth_obj.is_authenticated(session_data=session_data):
                logger.info(f'{idp} token expired, refreshing')
                oauth_obj.update_access_from_refresh_token(search.owner,oauth_token_obj.refresh_token)
                oauth_token_obj = OauthToken.objects.get(owner=owner, idp=idp)
                session_data[oauth_obj.get_access_token_session_field()] = oauth_token_obj.token
                session_data[oauth_obj.get_access_token_expiration_time_session_field()] = int(jwt.decode(oauth_token_obj.token, options={"verify_signature": False}, algorithms=["RS256"])['exp'])
                logger.info(f'{idp} token refreshed')
                search.messages.append(f'[{datetime.now()}] {idp} token refreshed: {owner}')
            else:
                logger.info(f'{idp} token current : {owner}')
                search.messages.append(f'[{datetime.now()}] {idp} token current : {owner}')
            logger.info(f'token microsoft_access_token_expiration_time : {session_data[oauth_obj.get_access_token_expiration_time_session_field()]}')
        except OauthToken.DoesNotExist:
            logger.error(f'{idp} token not found owner : {owner}')
            search.messages.append(f'[{datetime.now()}] {idp} token not found for owner : {owner}')
        except KeyError as e:
            logger.error(f"KeyError encountered: {e}")
            search.messages.append(f"[{datetime.now()}] KeyError encountered: {e}")
        except jwt.DecodeError:
            logger.error(f"Failed to decode JWT token for {idp} and owner: {owner}")
            search.messages.append(f"[{datetime.now()}] Failed to decode JWT token for {idp} and owner: {owner}")
        except AttributeError:
            logger.error(f"Unexpected attribute error for {idp} and owner: {owner}")
            search.messages.append(f"[{datetime.now()}] Unexpected attribute error for {idp} and owner: {owner}")
        except Exception as e:
            logger.error(f"Unexpected error for {idp} and owner {owner}: {str(e)}")
            search.messages.append(f"[{datetime.now()}] Unexpected error for {idp} and owner {owner}: {str(e)}")

def subscriber():
    '''
    This is fired whenever a Celery Beat event arrives
    Re-run searches that have subscribe = True, setting date:sort
    Mark new results unretrieved
    '''
    searches = Search.objects.filter(subscribe=True)
    logger.debug(f"START {module_name}")
    for search in searches:
        logger.debug(f"{module_name}: subscriber: {search.id}")
        owner = search.owner # User(search.owner)
        # check permissions
        if not (owner.has_perm('swirl.change_search') and owner.has_perm('swirl.change_result')):
            logger.warning(f"{module_name}: User {owner} needs permissions change_search({owner.has_perm('swirl.change_search')}), change_result({owner.has_perm('swirl.change_result')})")
            search.status = 'ERR_SUBSCRIBE_PERMISSIONS'
            if search.subscribe:
                search.messages.append(f'[{datetime.now()}] Subscriber disabled updates due to permission error')
                search.subscribe = False
            search.save()
            continue
        # Update oauth tokens if necessary
        session_data = dict()
        logger.debug(f"{module_name}: update session: {search.id}")
        _get_session_for_oauth_providers(search=search,owner=owner, session_data=session_data)
        search.status = 'UPDATE_SEARCH'
        search.save()
        # to do: better than below and renaming upon import
        success = run_search(search.id, session_data)
        if success:
            logger.debug(f"{module_name}: subscriber: updated {search.id}")
        else:
            logger.error(f"{module_name}: subscriber: error {search.status} updating {search.id}")
            if search.subscribe:
                search.messages.append(f'[{datetime.now()}] Subscriber disabled updates due to error {search.status}')
                search.subscribe = False
            search.save()
        # end if
        # time.sleep(SWIRL_SUBSCRIBE_WAIT)
    # end for
    logger.debug(f"END {module_name}")
    return True