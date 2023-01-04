'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ
import logging as logger
logger.basicConfig(level=logger.INFO)
import time

import django
from django.utils import timezone
from django.conf import settings

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

from swirl.models import Search
from swirl.search import search as run_search
from datetime import datetime

module_name = 'subscriber.py'

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
        logger.info(f"{module_name}: subscriber: {search.id}")
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
        search.status = 'UPDATE_SEARCH'
        search.save()
        # to do: better than below and renaming upon import
        success = run_search(search.id)
        if success:
            logger.info(f"{module_name}: subscriber: updated {search.id}")
        else:
            logger.error(f"{module_name}: subscriber: error {search.status} updating {search.id}")
            if search.subscribe:
                search.messages.append(f'[{datetime.now()}] Subscriber disabled updates due to error {search.status}')
                search.subscribe = False
            search.save()
        # end if
        time.sleep(settings.SWIRL_SUBSCRIBE_WAIT)
    # end for

    return True