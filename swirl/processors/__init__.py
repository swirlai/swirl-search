'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from swirl.processors.generic import *
from swirl.processors.adaptive import *
from swirl.processors.backstage_query import *
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
from swirl.processors.processor import Processor, QueryProcessor, ResultProcessor, PostResultProcessor

def alloc_processor(processor, kind=None):
    """
    Return the processor class with the given name.

    The name comes from stored configuration or from the request, so it is only
    ever resolved to a processor class, never to another name in this module.
    When kind is given (QueryProcessor, ResultProcessor or PostResultProcessor)
    the class must also be of that kind: each slot of a search runs its
    processors with that slot's arguments, and a processor of another kind
    would read them as something else. Any other name raises KeyError, the
    same error as a name that does not exist.
    """
    if not processor:
        logger.error("blank processor")
        return None
    candidate = globals()[processor]
    if not (isinstance(candidate, type) and issubclass(candidate, Processor)):
        raise KeyError(processor)
    if kind is not None and not issubclass(candidate, kind):
        raise KeyError(processor)
    return candidate

# Add new processors here!