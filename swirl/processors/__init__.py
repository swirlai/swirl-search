'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from swirl.processors.generic import *
from swirl.processors.adaptive import *
from swirl.processors.mapping import *
from swirl.processors.dedupe import *
from swirl.processors.relevancy import *
from swirl.processors.rag import *
from swirl.processors.spellcheck_query import *
from swirl.processors.gen_ai_query import *
from swirl.processors.transform_query_processor import *
from swirl.processors.date_finder import *
from swirl.processors.remove_pii import *
from swirl.models import Search, SearchProvider

def alloc_processor(processor):
    if not processor:
        logger.error("blank processor")
        return None
    return globals()[processor]

# Add new processors here!