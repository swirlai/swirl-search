'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

from textblob import TextBlob
import logging as logger

#############################################    
#############################################     

def spellcheck_query_processor(query_string):

    module_name = 'spellcheck_query_processor'

    if len(query_string) == 0:
        return

    try:
        corrected_query_string = "{0}".format(TextBlob(query_string).correct())
    except NameError as err:
        logger.warning(f'{module_name}: Error: NameError: {err}')
    except TypeError as err:
        logger.warning(f'{module_name}: Error: TypeError: {err}')

    if query_string != corrected_query_string:
        logger.info(f"{module_name}: rewrote query from {query_string} to {corrected_query_string}")

    return corrected_query_string

#############################################    
#############################################  
