from django.conf import settings

import os

import logging
logger = logging.getLogger(__name__)

MODEL_3 = "gpt-3.5-turbo"
MODEL_4 = "gpt-4"
MODEL = MODEL_4

AI_RAG_USE  = "AI_RAG_USE"
AI_REWRITE_USE =  "AI_REWRITE_USE"
AI_QUERY_USE = "AI_QUERY_USE"

class OpenAIClient:
    """
    Encapsulates the logic for initializing different types of AI clients,
    abstracts the complexity of client creation, and provides clear access to the
    client.
    throws ValueError when no key is configured or passed in.
    """
    def __init__(self, usage, key=None):
        if usage not in [AI_RAG_USE, AI_REWRITE_USE, AI_QUERY_USE]:
            raise NotImplementedError(f"Unknown AI {usage}. Client initialization not supported.")

        self._usage = usage
        self._openapi_key     = getattr(settings, 'OPENAI_API_KEY', None)
        self._azure_model     = getattr(settings, "AZURE_MODEL", None)
        self._azureapi_key    = getattr(settings, 'AZURE_OPENAI_KEY', None)
        self._azure_endpoint  = getattr(settings, "AZURE_OPENAI_ENDPOINT", None)
        self._swirl_rw_model  = getattr(settings, "SWIRL_REWRITE_MODEL", None)
        self._swirl_q_model   = getattr(settings,"SWIRL_QUERY_MODEL", None)
        self._swirl_rag_model = getattr(settings,'SWIRL_RAG_MODEL',None)

        logger.debug(f'cons config : {self._openapi_key} {self._azure_model}'
                    f'{self._azureapi_key} {self._azure_endpoint} {self._swirl_rw_model} {self._swirl_q_model} {self._swirl_rag_model}')

        self._api_key = None
        self._api_provider = None
        if self._azureapi_key and self._azure_model and self._azure_endpoint:
            self._api_provider = "AZUREAI"
            self._api_key = key if key else self._azureapi_key
        elif self._openapi_key:
            self._api_provider = "OPENAI"
            self._api_key = key if key else self._openapi_key

        if not self._api_key:
            raise ValueError("API key is required to initialize AIClient")

        self.openai_client = self._init_openai_client(self._api_provider, self._api_key)

    def _init_openai_client(self, provider, key):
        ai_client = None
        logger.debug(f'init_openai_client: {provider} {key}')
        try:
            if provider == "OPENAI":
                from openai import OpenAI
                ai_client = OpenAI(api_key=key)
            elif provider == "AZUREAI":
                from openai import AzureOpenAI
                ai_client = AzureOpenAI(api_key=key, azure_endpoint=self._azure_endpoint, api_version="2023-10-01-preview")
            else:
                raise NotImplementedError(f"Unknown AI provider {provider}. Client initialization not supported.")
        except Exception as err:
                raise err
        return ai_client

    def get_model(self):
        # If the provder is AZURE and the az model is set, use it.
        logger.info(f'get model {self._api_provider} {self._azure_model}')
        if self._api_provider == 'AZUREAI' and self._azure_model:
            return self._azure_model
        else:
            # otherwise use models as per usage
            if self._usage == AI_REWRITE_USE:
                return self._swirl_rw_model
            elif self._usage == AI_QUERY_USE:
                return self._swirl_q_model
            else:
                return self._swirl_rag_model

    def get_encoding_model(self):
        # otherwise use models as per usage
        if self._usage == AI_REWRITE_USE:
            return self._swirl_rw_model
        elif self._usage == AI_QUERY_USE:
            return self._swirl_q_model
        else:
            return self._swirl_rag_model
