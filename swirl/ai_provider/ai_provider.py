from django.conf import settings

import logging
from litellm import LiteLLM, get_max_tokens
from swirl.ai_provider.swirl_ai_provider import SwirlAIClient
logger = logging.getLogger(__name__)


AI_RAG_USE  = "AI_RAG_USE"
AI_REWRITE_USE =  "AI_REWRITE_USE"
AI_QUERY_USE = "AI_QUERY_USE"

class LLMClient(SwirlAIClient):
    """
    Encapsulates the methods by which we dynamically switch between LLM providers, abstracts client creation and utilization.
    
        usage: client = LLMClient(api_key = key, usage = USAGE)
                response = client.chat.completions.create(model=model, messages=messages, temperature=0)
    Returns:
        A single instance of the LLMClient() class
    
    Exceptions:
        - ValueError when no API keys are found
    """
    def __init__(self, usage, key=None):
        #Initializes LLMClient with proper key, base/endpoint, model, deployment, etc ...
        if usage not in [AI_RAG_USE, AI_REWRITE_USE, AI_QUERY_USE]:
            raise NotImplementedError(f"Unknown AI {usage}. Client initialization not supported.")

        """
        _api_provider (str): internal marker for LLM provider: str
        _api_key (str): API key for set LLM: str
        _model_deploy (str): model or deployment name, depending on what's needed: str
        _api_base (str): endpoint or base name, generally url format
        _api_version (str): self-explanatory, unused for most LLMs
        """

        self._usage = usage
        self._api_provider = None    
        self._api_key = None    
        self._model_deploy = None   
        self._api_base = None
        self._api_version = None
        self._swirl_rw_model  = getattr(settings, "SWIRL_REWRITE_MODEL", None)
        self._swirl_q_model   = getattr(settings,"SWIRL_QUERY_MODEL", None)
        self._swirl_rag_model = getattr(settings,'SWIRL_RAG_MODEL',None)

        """
        Grabbing vars from .env
        """

        self._openapi_key = getattr(settings, 'OPENAI_API_KEY', None)
        self._azure_model = getattr(settings, "AZURE_MODEL", None)
        self._azureapi_key = getattr(settings, 'AZURE_OPENAI_KEY', None)
        self._azure_endpoint = getattr(settings, "AZURE_OPENAI_ENDPOINT", None)

        """
        Grabbing additional vars from .env
        """

        self._anthropic_base = getattr(settings, 'ANTHROPIC_API_BASE', None)
        self._anthropic_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
        self._huggingface_base = getattr(settings, 'HUGGINGFACE_API_BASE', None)
        self._huggingface_key = getattr(settings, 'HUGGINGFACE_API_KEY', None)

        logger.info(f'Getters done')  
        """
        Setting Provider, API Key, API ENDPOINT/BASE, Model/deployment name, etc ...
        """


        if self._azureapi_key and self._azure_model and self._azure_endpoint:
            self._api_provider = "AZUREAI"
            self._api_key = key if key else self._azureapi_key
            self._api_base = self._azure_endpoint
            self._model_deploy = 'azure/gpt-35-turbo'
            self._api_version = '2023-10-01-preview'
            logger.info(f'Azure\'s OpenAI enabled for RAG')
        elif self._anthropic_key and self._anthropic_base:
            self._api_provider = 'ANTHROPICAI'
            self._api_key = key if key else self._anthropic_key
            self._api_base = self._anthropic_base
            self._model_deploy = 'claude-2' #idk, this is a placeholder
            logger.info(f'AnthropicAI enabled for RAG')
        elif self._openapi_key:
            self._api_provider = "OPENAI"
            self._api_key = key if key else self._openapi_key
            self._model_deploy = 'gpt-4'
            logger.info(f'OpenAI enabled for RAG')
        elif self._huggingface_key:
            self._api_provider = "HUGGINGFACEAI"
            self._model_deploy = 'huggingface/WizardLM/WizardCoder-Python-34B-V1.0'
            self._model_base = self._huggingface_base
            logger.info(f'Hugging Face AI enabled for RAG')
        if not self._api_key:
            logger.error("No API Key provided, RAG unavailable")
            raise ValueError(f"No API Key for any LLM given, RAG unavailable")


        self.llm_client=self.__init_client__(self._api_key)

    def __init_client__(self, key): #Creates LiteLLM client instance with correct api key
        ai_client = LiteLLM(api_key=key)
        logger.info(f'LLMClient created')
        return ai_client

    """
    Below commands return various arguments needed when creating a completion:
    - get_model(str): returns the model name or deployment name for the associated LLM
    - get_base(str): returns the api base or endpoint for the associated LLM
    - get_provider(str): returns internal naming scheme for the asscociated LLM
    - get_version(str): not needed for most LLMs, returns api version
    - max_tokens(int): returns int of max tokens - arbitrary headroom for associated LLM
    """

    def get_model(self):
        return self._model_deploy

    def get_base(self):
        return self._api_base

    def get_provider(self):
        return self._api_provider

    def get_version(self):
        if self._api_provider == 'AZUREAI':
            return self._api_version
        else:
            return ''

    def max_tokens(self):
        return get_max_tokens(self._model_deploy) - 3000

    def get_encoding_model(self):
        # otherwise use models as per usage
        if self._usage == AI_REWRITE_USE:
            return self._swirl_rw_model
        elif self._usage == AI_QUERY_USE:
            return self._swirl_q_model
        else:
            return self._swirl_rag_model

    def get_completion(self, system_text, prompt, temperature):
        completions_new = self.llm_client.chat.completions.create(
            model=self.get_model(),
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            api_base = self._api_base,
            api_version = self._api_version,
            max_tokens = self.max_tokens()
        )
        return completions_new