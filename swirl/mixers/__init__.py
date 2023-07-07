'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from swirl.mixers.relevancy import *
from swirl.mixers.date import *
from swirl.mixers.stack import *

def alloc_mixer(mixer):
    if not mixer:
        logger.error("blank mixer")
        return None
    return globals()[mixer]


# Add new mixers here!