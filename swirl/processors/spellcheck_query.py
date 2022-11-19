'''
@author:     Sid Probstein
@contact:    sid@swirl.today
@version:    SWIRL 1.x
'''

import logging as logger

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

    if query_string != corrected_query_string:
        logger.info(f"{module_name}: rewrote query from {query_string} to {corrected_query_string}")

    return corrected_query_string
