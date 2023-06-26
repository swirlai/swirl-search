'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from django.conf import settings

from swirl.processors.processor import *
from swirl.processors.utils import get_tag

import openai

#############################################
#############################################

def clean_reply(message):
    # to do: leave the quotes
    return message.replace('\n\n', '') #.replace('\"','')

class ChatGPTQueryProcessor(QueryProcessor):

    type = 'ChatGPTQueryProcessor'

    def __init__(self, query_string, query_mappings, tags):

        self.prompt = ""
        return super().__init__(query_string, query_mappings, tags)

    def set_prompt(self, prompt):
        self.prompt = str(prompt)

    def get_prompt(self):
        return str(self.prompt)

    def process(self):

        if getattr(settings, 'OPENAI_API_KEY', None):
            openai.api_key = settings.OPENAI_API_KEY
        else:
            return self.query_string

        self.warning(f"Tags: {self.tags}")
        self.prompt = get_tag('prompt', self.tags)    
        self.warning(f"prompt: {self.prompt}")
        if not self.prompt:
            return self.query_string
        
        if type(self.prompt) != str:
            self.warning(f"Ignoring invalid prompt: {self.prompt}")
            return self.query_string
        
        # to do: improve the below
        if not self.prompt.endswith('{query_string}'):
            if self.prompt.endswith(':'):
                self.prompt = self.prompt + ' {query_string}'
            else:
                if not self.prompt.endswith('?'):
                    self.prompt = self.prompt + ':  {query_string}'

        self.warning(f"Prompt is: {self.prompt.format(query_string=self.query_string)}")

        completions = openai.Completion.create(
            engine="text-davinci-002",
            prompt=self.prompt.format(query_string=self.query_string),
            max_tokens=(5 * len(self.query_string)),
            n=1,
            stop=None,
            temperature=0.5,
        )

        message = completions.choices[0].text
        self.warning(f"ChatGPT Response: {message}")

        if message.strip().lower() == self.query_string.strip().lower():
            return self.query_string

        if len(message) > 5 * len(self.query_string):
            self.warning(f"{self}: ChatGPT response more than 5x query string length, ignoring: {message}")
            return self.query_string

        if message.endswith('?'):
            # question rewriting
            return clean_reply(message)

        if len(message) <= 1.25 * len(self.query_string):
            # short response
            return clean_reply(message)

        if ('OR' in message) or ('AND' in message):
            # boolean response
            return clean_reply(message)

        if '?' in message:
            # restatement of question? bc it won't end with ?
            message = message.split('?')[1]
            # continue

        if ':' in message:
            # restatement of question?
            message = message.split(':')[1]
            # continue

        if '1.' in message:
            # '\n\n1. cryptocurrency\n2. Bitcoin\n3. blockchain\n4. Ethereum\n5. Litecoin'
            term_list = [term.strip().split('.')[1].strip() for term in message.strip().split('\n') if term.strip()]
            return ' OR '.join(term_list[:5])

        if message.startswith('\n\n'):
            # to do: watch for a restatement of the question! P1
            # '\n\n"management consulting"\n\n"management consulting firms"\n\n"management consulting services"\n\n"management consulting companies"'
            term_list = [term.strip().strip('"') for term in message.split("\n\n") if term.strip()]
            return ' OR '.join(term_list[:5])

        self.warning(f"{self}: ChatGPT response didn't parse clean: {message}")
        return self.query_string
