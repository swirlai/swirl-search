'''
@author:     Sid Probstein
@contact:    sid@swirl.today
@version:    Swirl 1.x
'''

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from textblob import TextBlob

#############################################    
#############################################     

def SpellcheckQueryProcessor(query_string):

    module_name = 'SpellcheckQueryProcessor'

    if len(query_string) == 0:
        return query_string

    try:
        corrected_query_string = "{0}".format(TextBlob(query_string).correct())
    except NameError as err:
        logger.warning(f'{module_name}: Error: NameError: {err}')
    except TypeError as err:
        logger.warning(f'{module_name}: Error: TypeError: {err}')

    return corrected_query_string
