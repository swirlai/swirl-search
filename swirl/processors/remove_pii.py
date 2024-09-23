'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from django.conf import settings

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.processors.generic import QueryProcessor, ResultProcessor, PostResultProcessor

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine, OperatorConfig

# Instantiate Presidio Analyzer and Anonymizer
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

#############################################

def redact_pii(text: str, query_string=None) -> str:
    """
    Redacts PII from the given text string using Presidio.

    :param text: The input string (either query or result) to clean.
    :return: The text with PII redacted.
    """

    return remove_pii(text, query_string, redact=True)

from swirl.processors.utils import remove_tags, highlight_list

def remove_pii(text: str, query_string=None, redact=False) -> str:
    """
    Removes PII from the given text string using Presidio.

    By default, Presidio redacts entities, replacing it with <entity-type>.
    The Presidio "redact" option removes the PII entirely.
    In SWIRL, remove means "remove the PII" and "redact" means "replace it with <entity-type>".

    :param text: The input string (either query or result) to clean.
    :return: The text with PII removed.
    """

    untagged_text = remove_tags(text)
    pii_entities = analyzer.analyze(text=untagged_text, language='en')

    if not pii_entities:
        return text

    operators = {"DEFAULT": OperatorConfig("redact")}
    if redact:
        # if specified
        operators = {"DEFAULT": OperatorConfig("replace")}

    anonymized_result = anonymizer.anonymize(
        text=untagged_text,
        analyzer_results=pii_entities,
        operators=operators
    )

    anonymized_text = anonymized_result.text

    if redact:
        anonymized_text = anonymized_text.replace('<', '[').replace('>', ']')

    if query_string:
        highlighted_anonymized_text = highlight_list(anonymized_text, query_string.split())
        return highlighted_anonymized_text

    return anonymized_text

#############################################

class RemovePIIQueryProcessor(QueryProcessor):
    """
    A SWIRL metasearch query processor that removes PII from search queries.
    """

    type = 'RemovePIIQueryProcessor'

    def process(self) -> str:
        """
        :return: The processed query with PII removed.
        """

        # Remove PII from the query
        cleaned_query = remove_pii(self.query_string)

        return cleaned_query

#############################################

class RedactPIIResultProcessor(ResultProcessor):
    """
    A SWIRL result processor that removes PII from the search results.
    Meant to be run after CosineResultProcessor.
    """

    type = "RemovePIIResultProcessor"

    def process(self) -> int:
        """
        :return: The number of modified results.
        """
        logger.debug(f"Processing {len(self.results)} results for PII removal.")

        modified = 0
        for item in self.results:
            pii_modified = False

            # Remove PII from 'title' and 'body' fields of each result
            if 'title' in item:
                cleaned_title = redact_pii(item['title'], self.query_string)
                if cleaned_title != item['title']:
                    item['title'] = cleaned_title
                    pii_modified = True

            if 'body' in item:
                cleaned_body = redact_pii(item['body'], self.query_string)
                if cleaned_body != item['body']:
                    item['body'] = cleaned_body
                    pii_modified = True

            if 'payload' in item:
                for key in item['payload']:
                    if type(item['payload'][key]) is not str:
                        continue
                    cleaned_payload = redact_pii(item['payload'][key], self.query_string)
                    if cleaned_payload != item['payload'][key]:
                        item['payload'][key] = cleaned_payload
                        pii_modified = True

            if pii_modified:
                modified += 1

        self.processed_results = self.results
        self.modified = modified
        logger.debug(f"PII removal complete. {self.modified} results modified.")

        return self.modified

#############################################

class RedactPIIPostResultProcessor(PostResultProcessor):
    """
    A SWIRL result processor that removes PII from all results.
    """

    type = "RemovePIIPostResultProcessor"

    def process(self) -> int:
        """
        :return: The number of modified results.
        """

        modified = 0

        for result in self.results:
            for item in result.json_results:
                pii_modified = False
                if 'title' in item:
                    cleaned_title = redact_pii(item['title'], self.search.query_string_processed)
                    if cleaned_title != item['title']:
                        item['title'] = cleaned_title
                        pii_modified = True
                if 'body' in item:
                    cleaned_body = redact_pii(item['body'], self.search.query_string_processed)
                    if cleaned_body != item['body']:
                        item['body'] = cleaned_body
                        pii_modified = True
                if 'payload' in item:
                    for key in item['payload']:
                        if type(item['payload'][key]) is not str:
                            continue
                        cleaned_payload = redact_pii(item['payload'][key], self.search.query_string_processed)
                        if cleaned_payload != item['payload'][key]:
                            item['payload'][key] = cleaned_payload
                            pii_modified = True
                if pii_modified:
                    modified += 1
            result.save()

        self.results_updated = modified
        return self.results_updated
