# Some utlity functions for external use

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.core.exceptions import ObjectDoesNotExist
from swirl.models import QueryTransform
from swirl.processors.transform_query_processor import TransformQueryProcessorFactory
from swirl.processors import alloc_processor

module_name = 'transform_query_processor_utils'
def __find_query_transform(name, type, user=None):
    """
    Atttempt to find the trasnform in the DB
    """
    try:
        if user:
            if not user.has_perm('swirl.view_querytransform'):
                logger.warning(f"User {user} needs permission view_querytransform")
                return False
        return QueryTransform.objects.get(name=name,qrx_type=type)
    except ObjectDoesNotExist as err:
        # It's okay for it to not be there, just warning
        logger.warn(f'{module_name}_{id}: ObjectDoesNotExist: {err}')
        return False

def __fall_back_to_query_transform(processor, query, err, user=None):
        """
        To be called after we failed to find a processor using eval
        """
        s_processor = str(processor)
        tmp = s_processor.split('.')
        if len(tmp) != 2:
            raise err # throw the original error
        name = tmp[0].strip()
        qrx_type = tmp[1].strip()
        if not (qxr := __find_query_transform(name=name, type=qrx_type, user=user)):
            raise err # throw the original error
        return TransformQueryProcessorFactory.alloc_query_transform(query, name, qrx_type,
                                                                                 qxr.config_content)

def get_pre_query_processor_or_transform(processor, query_temp, tags, user=None ):
    """
    Get the pre-query processed based on an entry from from the pre_query_processor(s) fields
    """
    try:
        pre_query_processor = alloc_processor(processor=processor)(query_temp, None, tags)
    except (Exception) as err:
        # catch all exceptions here, because anything can come back from eval
        pre_query_processor = __fall_back_to_query_transform(processor, query_temp, err, user)

    return pre_query_processor

def get_query_processor_or_transform(processor, query_temp, mappings, tags, user=None):
    """
    Get the query processed based on an entry from from the query_processor(s) fields
    """
    try:
        query_processor = alloc_processor(processor=processor)(query_temp, mappings, tags)
    except (Exception) as err:
        query_processor = __fall_back_to_query_transform(processor, query_temp, err, user)

    return query_processor
