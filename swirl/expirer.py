'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ
import logging
logger = logging.getLogger(__name__)

from datetime import timedelta

import django
from django.utils import timezone

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

from swirl.models import Search

module_name = 'expirer.py'

# Retention choice 3 is "Expire after 1 month"; a month is counted as this many days.
RETENTION_MONTH_DAYS = 30

RETENTION_PERIODS = {
    1: timedelta(hours=1),
    2: timedelta(days=1),
    3: timedelta(days=RETENTION_MONTH_DAYS),
}

##################################################
##################################################

def expire_if_due(search):

    '''
    Delete the search when its retention period has passed.
    Returns True when it was deleted.
    '''

    logger.debug(f"{module_name}: expirer checking: {search.id}")
    if search.retention == 0:
        # don't delete - this should not happen because of the filter in expirer()
        logger.warning(f"{module_name}: filter error, reviewed a search with retention = {search.retention}")
        return False
    period = RETENTION_PERIODS.get(search.retention)
    if period is None:
        logger.error(f"{module_name}: unexpected retention setting: {search.retention}")
        return False
    if search.date_updated + period < timezone.now():
        # to do: fix this to show local time, someday P4
        logger.info(f"{module_name}: expirer deleted {search.id}")
        search.delete()
        return True
    return False

def expirer():

    '''
    This fires whenever a Celery Beat event arrives
    Remove searches that are past expiration date, if expiration is not 0
    '''

    # security review for 1.7 - OK - system function
    searches = Search.objects.filter(retention__gt=0)
    for search in searches:
        # One search that cannot be checked or deleted must not stop the run:
        # the searches after it belong to other users.
        try:
            expire_if_due(search)
        except Exception as err:
            logger.error(f"{module_name}: expirer could not process search {search.id}: {err}")
    # end for

    return True
