'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ
import logging as logger
logger.basicConfig(level=logger.INFO)
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
from swirl.authenticators.microsoft import Microsoft
from swirl.search import search as run_search
from datetime import datetime

module_name = 'subscriber.py'

SWIRL_SUBSCRIBE_WAIT = getattr(settings, 'SWIRL_SUBSCRIBE_WAIT', 20)

##################################################
##################################################

# def update(search_id):
#     return subscriber(search_id=search_id)

##################################################

def subscriber():

    '''
    This is fired whenever a Celery Beat event arrives
    Re-run searches that have subscribe = True, setting date:sort
    Mark new results unretrieved
    '''

    searches = Search.objects.filter(subscribe=True)
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
        # security check
        session_data = dict()
        try:
            microsoft_token_obj = OauthToken.objects.get(owner=owner, idp='microsoft')
            session_data['microsoft_access_token'] = microsoft_token_obj.token
            session_data['microsoft_access_token_expiration_time'] = int(jwt.decode(microsoft_token_obj.token, options={"verify_signature": False}, algorithms=["RS256"])['exp'])
            ms_auth = Microsoft()
            logger.info(f'DNDEBUG : MS token microsoft_access_token_expiration_time : {session_data["microsoft_access_token_expiration_time"]}')
            if not ms_auth.is_authenticated(session_data=session_data):
                logger.info(f'DNDEBUG : MS token expired, refreshing')
                ms_auth.update_access_from_refresh_token(search.owner,microsoft_token_obj.refresh_token)
                microsoft_token_obj = OauthToken.objects.get(owner=owner, idp='microsoft')
                microsoft_token_obj = OauthToken.objects.get(owner=owner, idp='microsoft')
                session_data['microsoft_access_token'] = microsoft_token_obj.token
                session_data['microsoft_access_token_expiration_time'] = int(jwt.decode(microsoft_token_obj.token, options={"verify_signature": False}, algorithms=["RS256"])['exp'])
            else:
                logger.info(f'DNDEBUG : MS token current')
        except OauthToken.DoesNotExist:
            logger.info(f'DNDEBUG : MS token not found owner : {owner}')
            session_data = dict()
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

    return True