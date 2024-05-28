'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.conf import settings

from swirl.processors.processor import *
from swirl.processors.utils import get_tag
from swirl.openai.openai import OpenAIClient, AI_REWRITE_USE


MODEL_3 = "gpt-3.5-turbo"
MODEL_4 = "gpt-4"

MODEL = MODEL_3

TAG_LEGACY_PROMPT = "prompt"
TAG_PROMPT = "CHAT_QUERY_REWRITE_PROMPT"
TAG_SYSTEM_GUIDE= "CHAT_QUERY_REWRITE_GUIDE"
TAG_DO_FILTER= "CHAT_QUERY_DO_FILTER"
MODEL_DEFAULT_SYSTEM_GUIDE = "You are helping a user formulate better queries"
MODEL_DEFAULT_PROMPT = "Write a more precise query of similar length to this one {query_string}"
MODEL_DEFAULT_DO_FILTER = True

#############################################
#############################################

def clean_reply(message):
    if not message:
        return message
    return message.replace('\n\n', '').replace('\"','')

class GenAIQueryProcessor(QueryProcessor):


    type = 'GenAIQueryProcessor'

    def __init__(self, query_string, query_mappings, tags):
        return super().__init__(query_string, query_mappings, tags)

    def set_prompt(self, prompt):
        self.prompt = str(prompt)

    def get_prompt(self):
        return str(self.prompt)

    def set_prompt_from_tags(self):
        self.prompt = get_tag(TAG_LEGACY_PROMPT, self.tags)
        if not self.prompt:
            self.prompt = get_tag(TAG_PROMPT, self.tags)
        if not self.prompt:
            self.warning(f"No prompt provided, using default {MODEL_DEFAULT_PROMPT}")
            self.prompt = MODEL_DEFAULT_PROMPT
        # to do: improve the below
        # NOTE: D.A.N kept for backward compatability
        if not self.prompt.endswith('{query_string}'):
            self.warning("Prompt does not end w/ {query_string}, it may be modified")
            if self.prompt.endswith(':'):
                self.prompt = self.prompt + ' {query_string}'
            else:
                if not self.prompt.endswith('?'):
                    self.prompt = self.prompt + ':  {query_string}'

    def set_guide_from_tags(self):
        self.system_guide = get_tag(TAG_SYSTEM_GUIDE, self.tags)
        if not self.system_guide:
            self.warning(f"No prompt provided, using default {MODEL_DEFAULT_SYSTEM_GUIDE}")
            self.system_guide = MODEL_DEFAULT_SYSTEM_GUIDE

    def set_do_filter_from_tags(self):
        filter_tag_value = get_tag(TAG_DO_FILTER, self.tags)

        if filter_tag_value == None or len(filter_tag_value) <= 0:
            self.do_filter = MODEL_DEFAULT_DO_FILTER
        else:
            try:
                if filter_tag_value.lower() == 'true':
                    self.do_filter = True
                elif filter_tag_value.lower() == 'false':
                    self.do_filter = False
                else:
                    logger.error(f"Error parsing filter tag {filter_tag_value} using default: {MODEL_DEFAULT_DO_FILTER}")
                    self.do_filter = MODEL_DEFAULT_DO_FILTER
            except Exception as x:
                logger.error(f"Exception parsing filter tag {filter_tag_value} using default: {MODEL_DEFAULT_DO_FILTER}")
                self.do_filter = MODEL_DEFAULT_DO_FILTER

    def process(self, client=None):
        try:
            self.set_guide_from_tags()
            self.set_prompt_from_tags()
            self.set_do_filter_from_tags()
            if client is None:
                try:
                    client = OpenAIClient(usage=AI_REWRITE_USE)
                except ValueError as err:
                    self.warning('API key not available')
                    return self.query_string
            logger.info(f"{self.type} model {client.get_model()} system guide {self.system_guide} prompt {self.prompt} Do Filter {self.do_filter}")
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": self.system_guide},
                    {"role": "user", "content": self.prompt.format(query_string=self.query_string)    },
                ],
                temperature=0
            )
            response = client.openai_client.chat.completions.create(
                model=client.get_model(),
                messages=[
                    {"role": "system", "content": self.system_guide},
                    {"role": "user", "content": self.prompt.format(query_string=self.query_string)    },
                ],
                temperature=0
            )
            message = response.choices[0].message.content
            logger.info(f"ChatGPT Response: {message}")

            if not self.do_filter:
                return clean_reply(message=message)
            else:
                logger.info(f"applying legacy filters to resposne, it may not be used")

            if message.strip().lower() == self.query_string.strip().lower():
                return self.query_string

            if len(message) > 1.25 * len(self.query_string):
                self.warning(f"{self}: ChatGPT response more than 5x query string length, ignoring: {message}")
                return self.query_string

            if message.endswith('?'):
                # question rewriting
                return clean_reply(message)

            if len(message) <= 4 * len(self.query_string):
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
        except Exception as x:
            logger.error(f"unexpected excecption while rewriting query, returning original")
            return self.query_string
