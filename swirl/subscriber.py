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

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

from swirl.models import Search
from django.contrib.auth.models import User
from swirl.tasks import search_task

module_name = 'subscriber.py'

##################################################
##################################################

def subscriber():

    '''
    This fires whenever a Celery Beat event arrives
    Re-run searches that have subscribe = True, setting date:sort
    Mark new results unretrieved
    '''
    
    # security review for 1.7 - OK - system function
    searches = Search.objects.filter(subscribe=True)
    for search in searches:
        logger.info(f"{module_name}: subscriber: {search.id}")
        owner = search.owner # User(search.owner)
        # check permissions
        if not (owner.has_perm('swirl.change_search') and owner.has_perm('swirl.change_result')):
            logger.warning(f"{module_name}: User {owner} needs permissions change_search({owner.has_perm('swirl.change_search')}), change_result({owner.has_perm('swirl.change_result')})")
            # to do: handle this better
            continue
        # security check
        search.status = 'UPDATE_SEARCH'
        search.save()
        search_task.delay(search.id)
        # to do: parameterize
        time.sleep(20)
        # to do: check to see # of results and then do another logger.info?
    # end for

    return True