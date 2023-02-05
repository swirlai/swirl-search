'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from datetime import datetime

from jsonpath_ng import parse
from jsonpath_ng.exceptions import JsonPathParserError

from django.conf import settings

from swirl.processors.processor import *
from swirl.processors.utils import clean_string, create_result_dictionary
from swirl.connectors.utils import get_mappings_dict

import openai
  
#############################################    
#############################################    

class QueryGPT3Processor(QueryProcessor):

    type = 'QueryGPT3Processor'

    def __init__(self, query_string, query_mappings, tags):

        self.prompt = "write a better search query for: {query_string}"
        return super().__init__(query_string, query_mappings, tags)

    def set_prompt(self, prompt):
        self.prompt = prompt

    def process(self):
        
        openai.api_key = settings.OPENAI_API_KEY

        completions = openai.Completion.create(
            engine="text-davinci-002",
            prompt=self.prompt.format(query_string=self.query_string),
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=0.5,
        )

        message = completions.choices[0].text
        if '\n\n' in message:
            # '\n\n"management consulting"\n\n"management consulting firms"\n\n"management consulting services"\n\n"management consulting companies"'
            term_list = [s.strip().strip('"') for s in message.split("\n\n") if s.strip()]
            # to do
            return clean_string(' OR '.join(term_list))

        self.warning(f"{self}: GPT3 response didn't parse clean: {message}")
        
        return clean_string(self.query_string)
