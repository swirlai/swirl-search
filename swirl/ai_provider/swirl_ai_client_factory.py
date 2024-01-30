from django.conf import settings

import logging
from swirl.swirlai.swirlai import OpenAIClient
from swirl.ai_provider.ai_provider import LLMClient
logger = logging.getLogger(__name__)


class SwirlAIClientFactory():
        """
        SwirlAIClientFactory allocates an AIClient for use with RAG. It chooses based on an environment variable 'LLM_API'. If it is set to 'litellm', it instantiates an instance of LLMClient. 
        If it is unset, it defaults to our internal OpenAIClient. If it is set to anything else, no client will be allocated. 
        """


        @staticmethod
        def alloc_ai_client(usage):
            llm_api = getattr(settings, 'LLM_API', None)


            if llm_api == None or llm_api == 'internal':
                api_provider = 'internal'
                logger.info(f'Provider {api_provider} selected')
                try:
                    client = OpenAIClient(usage=usage)
                except:
                    logger.error(f'Error when attempting to allocate an OpenAIClient')
                return client
            elif llm_api == 'litellm':
                api_provider = 'litellm'
                logger.info(f'Provider {api_provider} selected')
                try:
                    client = LLMClient(usage=usage)
                except NotImplementedError as e:
                    logger.error(f'Error {e} when attempting to allocate an LLMClient')
                return client
            else:
                logger.error(f'API Provider {api_provider} unknown/unsupported') 
                return None