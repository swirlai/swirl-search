'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from django.conf import settings

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.processors.generic import QueryProcessor, ResultProcessor

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine, OperatorConfig

# Instantiate Presidio Analyzer and Anonymizer
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

#############################################

def remove_pii(text: str) -> str:
    """
    Removes PII from the given text string using Presidio.
    
    :param text: The input string (either query or result) to clean.
    :return: The text with PII removed.
    """
    # Analyze the input text for PII entities
    pii_entities = analyzer.analyze(text=text, language='en')
    
    if not pii_entities:
        return text

    # operators = {"DEFAULT": OperatorConfig("replace", {"new_value": "<>"})}
    operators = {"DEFAULT": OperatorConfig("redact")}

    # Remove PII by anonymizing the identified entities
    anonymized_result = anonymizer.anonymize(
        text=text, 
        analyzer_results=pii_entities, 
        operators=operators
    )
    
    return anonymized_result.text

#############################################

class RemovePIIQueryProcessor(QueryProcessor):
    """
    A SWIRL metasearch query processor that removes PII from search queries.
    Inherits from SWIRL's base QueryProcessor class.
    """
    
    type = 'RemovePIIQueryProcessor'

    def process(self) -> str:
        """
        Overrides the base QueryProcessor's process method.
        It processes the query to remove PII before the query is further handled.
        
        :return: The processed query with PII removed.
        """
        
        # Remove PII from the query
        cleaned_query = remove_pii(self.query_string)
        self.warning(f"Removed PII from {self.query_string} -> {cleaned_query}!")
        
        return cleaned_query

#############################################

class RemovePIIResultProcessor(ResultProcessor):
    """
    A SWIRL result processor that removes PII from the search results.
    Inherits from SWIRL's base ResultProcessor class.
    """
    
    type = "RemovePIIResultProcessor"

    def __init__(self, results, provider, query_string, request_id='', **kwargs):
        super().__init__(results, provider, query_string, request_id=request_id, **kwargs)
        self.modified = 0

    def process(self) -> int:
        """
        Overrides the base ResultProcessor's process method.
        It processes each result to remove PII and tracks the number of modified results.
        
        :return: The number of modified results.
        """
        logger.debug(f"Processing {len(self.results)} results for PII removal.")
        
        modified = 0
        for result in self.results:
            pii_modified = False
            
            # Remove PII from 'title' and 'body' fields of each result
            if 'title' in result:
                cleaned_title = remove_pii(result['title'])
                if cleaned_title != result['title']:
                    result['title'] = cleaned_title
                    pii_modified = True

            if 'body' in result:
                cleaned_body = remove_pii(result['body'])
                if cleaned_body != result['body']:
                    result['body'] = cleaned_body
                    pii_modified = True
            
            if pii_modified:
                modified += 1

        self.processed_results = self.results
        self.modified = modified
        logger.debug(f"PII removal complete. {self.modified} results modified.")
        
        return self.modified
