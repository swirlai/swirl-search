'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from operator import itemgetter
from urllib.parse import urlparse

from django.conf import settings

from swirl.processors.processor import *

from datetime import datetime

from swirl.openai.openai import OpenAIClient, AI_RAG_USE

from celery import group
import threading


# from swirl.web_page import PageFetcherFactory
from swirl.rag_prompt import RagPrompt

MODEL_3 = "gpt-3.5-turbo"
MODEL_3_TOK_MAX = 3800
MODEL_4 = "gpt-4"
MODEL_4_TOK_MAX = 7000
MODEL = MODEL_3
MODEL_TOK_MAX = MODEL_3_TOK_MAX
MODEL_DEFAULT_SYSTEM_GUIDE = "You are a helpful assistant who considers recent information when answering questions."
FETCH_TO_SECS=10
DO_MESSAGE_MOCK_ON_ERROR=False
MESSAGE_MOCK_ON_ERROR=f"Mock API resposne from {MODEL}. This is a mock response for testing purpose only."

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

#############################################
#############################################

def is_valid_url(url):
    parsed_url = urlparse(url)
    return bool(parsed_url.scheme)

import re

def find_substrings(string1, string2):
    # Remove punctuation and make lowercase
    string1 = re.sub(r'[^\w\s]', '', string1).lower()
    string2 = re.sub(r'[^\w\s]', '', string2).lower()

    # Split the string1 by spaces to get tokens
    tokens1 = string1.split()

    # Add the whole string1 as another token
    tokens1.append(string1)

    matching_indices = []

    # Tokenize string2 by spaces
    tokens2 = string2.split()

    for i, token2 in enumerate(tokens2):
        for token1 in tokens1:
            if token1 in token2:
                matching_indices.append(i)
                break # If a match is found for this token, no need to keep checking

    return matching_indices


#############################################
#############################################

from swirl.processors.utils import clean_string_keep_punct, remove_tags
from swirl.bs4 import bs
from readability import Document
from swirl.processors.utils import create_result_dictionary



class RAGPostResultProcessor(PostResultProcessor):

    type="RAGPostResultProcessor"

    def __init__(self, search_id, request_id='', should_get_results=False, rag_query_items=False):
        super().__init__(search_id=search_id, request_id=request_id, should_get_results=should_get_results, rag_query_items=rag_query_items)
        self.tasks = None
        self.stop_background_thread = False
        try:
            rag_result = Result.objects.get(search_id=search_id, searchprovider='ChatGPT')
            if rag_result:
                logger.debug(f'RAG: previous RAG result was deleted')
                rag_result.delete()
        except:
            pass

    def _log_n_store_warn(self, url, warn, buffer):
        logger.warning(warn)
        buffer[url] = warn

    def stop_processing(self):
        self.stop_background_thread = True

    def format_result_as_page(self, body, reason):
        logger.debug(f"post-fetch building page from result reason : {reason} body : {body}")
        return f"body : {remove_tags(body)}"

    def background_process(self):
        rag_item_list = []
        rag_query_items = self.rag_query_items or []
        for result in self.results:
            if result.json_results:
                for item in result.json_results:
                    if rag_query_items:
                        if 'swirl_id' in item and str(item['swirl_id']) in rag_query_items:
                            rag_item_list.append(item)
                            item['provider_id'] = result.provider_id
                    elif 'swirl_score' in item:
                        # to do: parameterize
                        if item['swirl_score'] > 50.0:
                            rag_item_list.append(item)
                            item['provider_id'] = result.provider_id

        if not rag_item_list:
            result = Result.objects.create(owner=self.search.owner, search_id=self.search, provider_id=5, searchprovider='ChatGPT', query_string_to_provider=self.search.query_string_processed.strip(), query_to_provider='None', status='READY', retrieved=1, found=1, json_results=[], time=0.0)
            result.save()
            return 0

        user_query = self.search.query_string_processed.strip()

        # remove tags from query string
        query_wot_list = []
        tag = ""
        for term in self.search.query_string_processed.strip().split():
            if ':' in term:
                if term.endswith(':'):
                    continue
                else:
                    query_wot_list.append(term.split(':')[1])
                # end if
            else:
                query_wot_list.append(term)
            # end if
        query_wot = ' '.join(query_wot_list)

        if query_wot != user_query:
            self.warning(f"RAG: revised query string to: {query_wot} ")
            user_query = query_wot

        # to do: check for searchprovider_rank and date_published? Verify that this works if they are missing?
        sorted_rag = sorted(sorted(sorted(rag_item_list, key=itemgetter('searchprovider_rank')), key=itemgetter('date_published'), reverse=True), key=itemgetter('swirl_score'), reverse=True)

        MAX_TO_CONSIDER = 10

        chosen_rag = sorted_rag[:MAX_TO_CONSIDER]
        max_tokens = MODEL_TOK_MAX
        fallback_text = ""
        fallback_tokens = 0
        rag_prompt = RagPrompt(user_query, max_tokens=max_tokens, model=self.client.get_encoding_model())

        fetch_prompt_errors = {}
        from swirl.tasks import page_fetcher_task
        tasks = [
                page_fetcher_task.s(
                item['searchprovider'],
                item['swirl_score'],
                item['url'],
                item.get('provider_id'),
                item['body'],
                user_query
            )
            for item in chosen_rag
        ]

        result_group = group(*tasks).apply_async()
        self.tasks = result_group
        results = result_group.get(interval=0.05, timeout=120)
        if self.stop_background_thread:
            return 0
        for nth_result, result in enumerate(results):
            if result[0] == False:
                continue
            else:
                text_for_query, response_url, document_type, body, url, json = result
                if body:
                    new_content = clean_string_keep_punct(body)
                    if fallback_tokens < max_tokens:
                        fallback_text = fallback_text + new_content
                        fallback_tokens = fallback_tokens + len(new_content.split())

                    # Getting search provider from the last item is questionable practice D.A.N.
                    # logger.info(f'RAG {item["searchprovider"]} PageFetcherFactory adding prompt content from page :\nurl : {url}\ncontent_url : {content_url}\nresponse_url:{response_url}')
                    if new_content := text_for_query:
                        # is_full = rag_prompt.put_chunk(new_content, url=url, type=document_type, filter_file_type=(not content_url))
                        is_full = rag_prompt.put_chunk(new_content, url=url, type=document_type, filter_file_type=True)
                        if not rag_prompt.is_last_chunk_added():
                            summary_page_text = self.format_result_as_page(chosen_rag[nth_result]['body'], rag_prompt.get_last_chunk_status())
                            is_full = rag_prompt.put_chunk(summary_page_text, url=url, type=document_type, filter_file_type=True)
                            if not rag_prompt.is_last_chunk_added():
                                warn =  f"RAG Chunk not added : {rag_prompt.get_last_chunk_status()}"
                                self._log_n_store_warn(url=url, warn=warn, buffer=fetch_prompt_errors)
                                fetch_prompt_errors[url] = warn

                        logger.debug(f'RAG : max_tokens:{max_tokens} num_tokens {rag_prompt.get_num_tokens()} is_full:{rag_prompt.is_full()}')
                        if is_full:
                            break
                    else:
                        summary_page_text = self.format_result_as_page(chosen_rag[nth_result]['body'], "NO CONTENT")
                        is_full = rag_prompt.put_chunk(summary_page_text, url=url, type=document_type, filter_file_type=True)
                        if not rag_prompt.is_last_chunk_added():
                            warn = f'RAG No content found in {url} max_tokens:{max_tokens} num_tokens {rag_prompt.get_num_tokens()} is_full:{rag_prompt.is_full()} JSON:{json}'
                            self._log_n_store_warn(url=url,warn=warn,buffer=fetch_prompt_errors)

        new_prompt_text = rag_prompt.get_promp_text()
        logger.debug(f"\nRAG Prompt:\n\t{new_prompt_text}")

        if len(new_prompt_text) < 5:
            self.warning(f"RAG too short after trying {MAX_TO_CONSIDER} items, trying fallback")
            new_prompt_text = fallback_text

        if len(new_prompt_text) < 5:
            self.warning(f"RAG too short after fallback, giving up")
            result = Result.objects.create(owner=self.search.owner, search_id=self.search, provider_id=5, searchprovider='ChatGPT', query_string_to_provider=new_prompt_text[:256], query_to_provider='None', status='READY', retrieved=1, found=1, json_results=[], time=0.0)
            result.save()
            return 0

        client_model=self.client.get_model()
        try:
            completions_new = self.client.openai_client.chat.completions.create(
                model=client_model,
                messages=[
                    {"role": "system", "content": rag_prompt.get_role_system_guide_text()},
                    {"role": "user", "content": new_prompt_text},
                ],
                temperature=0
            )
            model_response = completions_new.choices[0].message.content
            logger.warning(f'RAG: fetch_prompt_errors follow:')
            for (k,v) in fetch_prompt_errors.items():
                logger.warning(f'RAG:\t url:{k} problem:{v}')
        except Exception as err:
            if DO_MESSAGE_MOCK_ON_ERROR:
                logger.error(f"error : {err} while creating CGPT response")
                logger.debug(f'Returning mock message instead : {MESSAGE_MOCK_ON_ERROR}')
                model_response = MESSAGE_MOCK_ON_ERROR
            else:
                logger.error(f"error : {err} while creating CGPT response")
                result = Result.objects.create(owner=self.search.owner, search_id=self.search, provider_id=5, searchprovider='ChatGPT', query_string_to_provider=new_prompt_text[:256], query_to_provider='None', status='READY', retrieved=1, found=1, json_results=[], time=0.0)
                result.save()
                return 0

        logger.debug(f'RAG-TITLE: {self.search.query_string_processed}')
        logger.debug(f'RAG-BODY: {model_response}')
        logger.debug(f'RAG-MODEL: {client_model}')
        logger.debug("RAG Saving result object")

        rag_result = create_result_dictionary()
        rag_result['date_published'] = str(datetime.now())
        rag_result['title'] = self.search.query_string_processed,
        rag_result['body'] = model_response,
        rag_result['author'] = 'ChatGPT'
        rag_result['searchprovider'] = f'ChatGPT-{client_model}'
        rag_result['searchprovider_rank'] = 1
        if settings.SWIRL_DEFAULT_RESULT_BLOCK:
            rag_result['result_block'] = getattr(settings, 'SWIRL_DEFAULT_RESULT_BLOCK', 'ai_summary')
        rag_result['rag_query_items'] = [str(item['swirl_id']) for item in chosen_rag]

        result = Result.objects.create(owner=self.search.owner, search_id=self.search, provider_id=5, searchprovider='ChatGPT', query_string_to_provider=new_prompt_text[:256], query_to_provider='None', status='READY', retrieved=1, found=1, json_results=[rag_result], time=0.0)
        result.save()
        return result

    def process(self, should_return=True):
        self.client = None
        try :
            logger.debug('RAG allocating client')
            self.client = OpenAIClient(usage=AI_RAG_USE)
            logger.debug(f'RAG allocate client complete {self.client}')
        except ValueError as err:
            logger.warning(f"RAG : {err} allocating openAI client")
            logger.warning(err)
            return 0

        if should_return:
            return self.background_process()
        else:
            background_thread = threading.Thread(target=self.background_process)
            background_thread.start()
            return 1
