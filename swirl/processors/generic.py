'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from datetime import datetime

import re

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.conf import settings

from swirl.processors.processor import *
from swirl.processors.utils import get_tag, clean_string, create_result_dictionary, get_mappings_dict

#############################################
#############################################

class GenericQueryProcessor(QueryProcessor):

    type = 'GenericQueryProcessor'

    def process(self):
        return clean_string(self.query_string).strip()
    
#############################################

class TestQueryProcessor(QueryProcessor):

    type = 'TestQueryProcessor'

    def process(self):
        return clean_string(self.query_string).strip() + " test"

#############################################

class GenericResultProcessor(ResultProcessor):

    type="GenericResultProcessor"

    def __init__(self, results, provider, query_string, request_id='', **kwargs):
        super().__init__(results, provider, query_string, request_id=request_id, **kwargs)

    def process(self):

        use_payload = True
        file_system = False
        # result_block = None
        if 'NO_PAYLOAD' in self.provider.result_mappings:
            self.warning(f"NO_PAYLOAD is not supported by GenericResultProcessor, ignoring")
        if 'FILE_SYSTEM' in self.provider.result_mappings:
            file_system = True
        # if 'BLOCK' in self.provider.result_mappings:
        #     result_block = get_mappings_dict(self.provider.result_mappings)['BLOCK']

        list_results = []
        result_number = 1

        for result in self.results:
            swirl_result = create_result_dictionary()
            # payload = {}
            # report searchprovider rank, not ours
            swirl_result['searchprovider_rank'] = result_number
            swirl_result['date_retrieved'] = str(datetime.now())

            #############################################
            # copy fields, avoiding collisions
            for key in result.keys():
                if key in swirl_result.keys():
                    if not swirl_result[key]:
                        swirl_result[key] = result[key]
             # end for

            if swirl_result['date_published'] == "":
                swirl_result['date_published'] = 'unknown'

            #############################################
            # final assembly
            swirl_result['payload'] = {}

            # mark results from SearchProviders with result_mapping FILE_SYSTEM
            if file_system:
                swirl_result['_relevancy_model'] = 'FILE_SYSTEM'

            # if result_block:
            #     swirl_result['result_block'] = result_block

            # try to find a title, if none provided
            if swirl_result['title'] == "":
                if swirl_result['url']:
                    swirl_result['title'] = swirl_result['url']
                elif swirl_result['author']:
                    swirl_result['title'] = swirl_result['author']
                # end if
            # end if
            swirl_result['searchprovider'] = self.provider.name
            list_results.append(swirl_result)
            result_number = result_number + 1
            if result_number > self.provider.results_per_query:
                # self.warning("Truncating extra results, found & retrieved may be incorrect")
                break
        # end for

        self.processed_results = list_results
        self.modified = len(self.processed_results)
        return self.modified

#############################################

SWIRL_MAX_FIELD_LEN = getattr(settings, 'SWIRL_MAX_FIELD_LEN', 256)
FIELDS_TO_LIMIT = ['title', 'body']

def match_any(source_list, s_target, max_length):
    target_cleaned = re.sub(r'[^\w\s]', '', s_target)  # Remove punctuation
    target_words = target_cleaned.split()  # Split the cleaned target string into words

    source_set = set(word.lower() for word in source_list)  # Create a set of lowercase source words

    for i, word in enumerate(target_words):
        cleaned_word = word.lower()
        if cleaned_word in source_set:
            start_index = s_target.lower().index(cleaned_word)
            substring = s_target[start_index:]
            words = substring.split()
            accumulated_length = 0
            result = []
            for w in words:
                if accumulated_length + len(w) <= max_length:
                    result.append(w)
                    accumulated_length += len(w) + 1  # +1 for the space between words
                else:
                    break
            return ' '.join(result)
    return ''

class LenLimitingResultProcessor(ResultProcessor):

    type="LenLimitingResultProcessor"

    def __init__(self, results, provider, query_string, request_id='', **kwargs):
        super().__init__(results, provider, query_string, request_id=request_id, **kwargs)

    def process(self):

        max_length = get_tag('max_length', self.provider_tags)
        if max_length:
            if type(max_length) != int:
                if type(max_length) == str:
                    max_length=int(max_length)
                else:
                    self.error(f"Can't extract max_length from tag: {max_length}")
                    return 0
        else:
            max_length = SWIRL_MAX_FIELD_LEN

        modified = 0
        for item in self.results:
            for field in FIELDS_TO_LIMIT:
                if field in item:
                    if type(item[field]) == str:
                        if len(item[field]) > max_length:
                            # copy to payload
                            item['payload'][field+'_full'] = item[field]
                            snippet = match_any(self.query_string.split(), item[field], max_length)
                            if snippet:
                                item[field] = '...' + snippet + '...'
                            else:
                                # no match, so just take first N
                                item[field] = item[field][:max_length-3] + '...'
                            # end if
                            modified = modified + 1
                    else:
                        self.warning(f"Field {field} is not str, found type: {type(item[field])}")

        self.processed_results = self.results
        self.modified = modified
        return self.modified

#############################################

FIELDS_TO_CLEAN = ['title', 'body']

def remove_non_alphanumeric(text):
    # Define the regular expression pattern
    pattern = r"[^\w().?!'\",\s]|(\.{4,})|(\.{3})|(-{3,})|(-{2})"

    # Define the replacement function
    def replace(match):
        if match.group(1):
            return "..."
        elif match.group(2):
            return "..."
        elif match.group(3):
            return "--"
        elif match.group(4):
            return "--"
        else:
            return " "

    # Apply the pattern and replacement function
    return re.sub(pattern, replace, text)

class CleanTextResultProcessor(ResultProcessor):

    type="CleanTextResultProcessor"

    def __init__(self, results, provider, query_string, request_id='', **kwargs):
        super().__init__(results, provider, query_string, request_id=request_id, **kwargs)

    def process(self):

        modified = 0
        for item in self.results:
            for field in FIELDS_TO_CLEAN:
                if field in item:
                    if type(item[field]) == str:
                        modified = modified + 1
                        item[field] = remove_non_alphanumeric(item[field])

        self.processed_results = self.results
        self.modified = modified
        return self.modified

#############################################

from swirl.processors.utils import match_all, remove_tags

class RequireQueryStringInTitleResultProcessor(ResultProcessor):

    type="RequireQueryStringInTitleResultProcessor"

    def __init__(self, results, provider, query_string, request_id='', **kwargs):
        super().__init__(results, provider, query_string, request_id=request_id, **kwargs)

    def process(self):
        
        self.processed_results = []
        self.modified = 0

        for item in self.results:
            if 'title' in item:
                if match_all(remove_non_alphanumeric(remove_tags(self.query_string)).lower().split(),remove_non_alphanumeric(remove_tags(item['title'])).lower().split()):
                    self.processed_results.append(item)
                else:
                    self.modified = self.modified - 1
            else:
                self.modified = self.modified - 1

        return self.modified
     
#############################################

class TestResultProcessor(ResultProcessor):

    type="TestResultProcessor"

    def __init__(self, results, provider, query_string, request_id='', **kwargs):
        super().__init__(results, provider, query_string, request_id=request_id, **kwargs)

    def process(self):

        # to do: test to ensure operation on a Swirl result, i.e. after Generic or MappingResultProcessor
        for item in self.results:
            item['test'] = True

        self.processed_results = self.results
        self.modified = len(self.processed_results)
        return self.modified

#############################################

class DuplicateHalfResultProcessor(ResultProcessor):

    type="DuplicateHalfResultProcessor"

    def __init__(self, results, provider, query_string, request_id='', **kwargs):
        super().__init__(results, provider, query_string, request_id=request_id, **kwargs)

    def process(self):

        # to do: test to ensure operation on a Swirl result, i.e. after Generic or MappingResultProcessor
        switch = 0
        results_hd = []
        for item in self.results:
            if switch == 0:
                results_hd.append(item)
                switch = 1
                continue
            if switch == 1:
                switch = 0
                continue
        # end for

        self.processed_results = self.results + results_hd
        self.modified = len(self.processed_results)
        return self.modified
