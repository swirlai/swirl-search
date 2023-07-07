'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from swirl.processors.generic import *
from swirl.processors.adaptive import *
from swirl.processors.mapping import *
from swirl.processors.dedupe import *
from swirl.processors.relevancy import *
from swirl.processors.spellcheck_query import *
from swirl.processors.chatgpt_query import *
from swirl.processors.transform_query_processor import *
from swirl.processors.write_to_filesystem import *
from swirl.processors.temporal_relevancy import *
from swirl.processors.date_finder import *
from swirl.processors.entity_matcher import *
from swirl.models import Search, SearchProvider

SWIRL_PROCESSOR_LIST = SearchProvider.QUERY_PROCESSOR_CHOICES + SearchProvider.RESULT_PROCESSOR_CHOICES + Search.PRE_QUERY_PROCESSOR_CHOICES + Search.POST_RESULT_PROCESSOR_CHOICES

SWIRL_PROCESSOR_DISPATCH = {}
# DS-612 DONE
for t in SWIRL_PROCESSOR_LIST:
    SWIRL_PROCESSOR_DISPATCH[t[0]] = globals()[t[0]]

def alloc_processor(processor):
    if not processor:
        logger.error("blank processor")
        return None
    return globals()[processor]

# Add new processors here!