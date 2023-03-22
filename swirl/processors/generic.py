'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from datetime import datetime

from jsonpath_ng import parse
from jsonpath_ng.exceptions import JsonPathParserError

from swirl.processors.processor import *
from swirl.processors.utils import clean_string, create_result_dictionary

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

    def process(self):

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

            # final assembly

            swirl_result['payload'] = {}
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
                logger.warning("Truncating extra results, found & retrieved may be incorrect")
                break
        # end for

        self.processed_results = list_results
        return self.processed_results

#############################################

class TestResultProcessor(ResultProcessor):

    type="TestResultProcessor"

    def process(self):

        # to do: test to ensure operation on a SWIRL result, i.e. after Generic or MappingResultProcessor
        for item in self.results:
            item['test'] = True

        self.processed_results = self.results
        return self.processed_results

#############################################

class DuplicateHalfResultProcessor(ResultProcessor):

    type="DuplicateHalfResultProcessor"

    def process(self):

        # to do: test to ensure operation on a SWIRL result, i.e. after Generic or MappingResultProcessor
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
        return self.processed_results
