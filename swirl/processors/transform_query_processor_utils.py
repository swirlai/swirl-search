# Some utility functions for external use

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from swirl.models import QueryTransform
from swirl.processors.transform_query_processor import TransformQueryProcessorFactory
from swirl.processors import alloc_processor
from swirl.processors.processor import QueryProcessor

module_name = 'transform_query_processor_utils'
def __find_query_transform(name, type, user=None, provider_owner=None):
    """
    Attempt to find the transform in the DB

    A user gets a transform that is theirs or shared, as the API lists them.
    A transform named by a SearchProvider may also belong to that provider's
    owner, who chose it.
    """
    try:
        transforms = QueryTransform.objects.filter(name=name,qrx_type=type)
        if user:
            if not user.has_perm('swirl.view_querytransform'):
                logger.warning(f"User {user} needs permission view_querytransform")
                return False
            allowed = Q(shared=True) | Q(owner=user)
            if provider_owner:
                allowed = allowed | Q(owner=provider_owner)
            transforms = transforms.filter(allowed)
        return transforms.get()
    except ObjectDoesNotExist as err:
        # It's okay for it to not be there, just warning
        logger.warn(f'{module_name}_{id}: ObjectDoesNotExist: {err}')
        return False

def __fall_back_to_query_transform(processor, query, err, user=None, provider_owner=None):
        """
        To be called after we failed to find a processor using eval
        """
        s_processor = str(processor)
        tmp = s_processor.split('.')
        if len(tmp) != 2:
            raise err # throw the original error
        name = tmp[0].strip()
        qrx_type = tmp[1].strip()
        if not (qxr := __find_query_transform(name=name, type=qrx_type, user=user, provider_owner=provider_owner)):
            raise err # throw the original error
        return TransformQueryProcessorFactory.alloc_query_transform(query, name, qrx_type,
                                                                                 qxr.config_content)

def get_pre_query_processor_or_transform(processor, query_temp, tags, user=None ):
    """
    Get the pre-query processed based on an entry from from the pre_query_processor(s) fields
    """
    try:
        pre_query_processor = alloc_processor(processor=processor, kind=QueryProcessor)(query_temp, None, tags)
    except (Exception) as err:
        # catch all exceptions here, because anything can come back from eval
        pre_query_processor = __fall_back_to_query_transform(processor, query_temp, err, user)

    return pre_query_processor

def get_query_processor_or_transform(processor, query_temp, mappings, tags, user=None, provider_owner=None):
    """
    Get the query processed based on an entry from from the query_processor(s) fields
    """
    try:
        query_processor = alloc_processor(processor=processor, kind=QueryProcessor)(query_temp, mappings, tags)
    except (Exception) as err:
        query_processor = __fall_back_to_query_transform(processor, query_temp, err, user, provider_owner)

    return query_processor
