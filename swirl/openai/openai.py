from django.conf import settings

import logging
logger = logging.getLogger(__name__)

AI_RAG_USE = "AI_RAG_USE"
AI_REWRITE_USE = "AI_REWRITE_USE"
AI_QUERY_USE = "AI_QUERY_USE"


class OpenAIClient:
    """
    Encapsulates the logic for initializing different types of AI clients,
    abstracts the complexity of client creation, and provides clear access to the
    client.

    Raises:
        ValueError: when no key is configured or passed in.
        NotImplementedError: when an unknown usage or provider is requested.
    """

    def __init__(self, usage, key=None):
        if usage not in [AI_RAG_USE, AI_REWRITE_USE, AI_QUERY_USE]:
            raise NotImplementedError(
                f"Unknown AI usage {usage}. Client initialization not supported."
            )

        self._usage = usage

        # Provider configuration from Django settings / env
        self._openapi_key    = getattr(settings, "OPENAI_API_KEY", None)
        self._azure_model    = getattr(settings, "AZURE_MODEL", None)
        self._azureapi_key   = getattr(settings, "AZURE_OPENAI_KEY", None)
        self._azure_endpoint = getattr(settings, "AZURE_OPENAI_ENDPOINT", None)
        self._azure_api_version = getattr(settings, "AZURE_API_VERSION", None)

        # Logical SWIRL model choices per usage (rewrite/query/rag)
        self._swirl_rw_model  = getattr(settings, "SWIRL_REWRITE_MODEL", None)
        self._swirl_q_model   = getattr(settings, "SWIRL_QUERY_MODEL", None)
        self._swirl_rag_model = getattr(settings, "SWIRL_RAG_MODEL", None)

        logger.debug(
            "OpenAIClient config: explicit_key=%s openai_key=%s azure_model=%s "
            "azure_key=%s azure_endpoint=%s swirl_rw_model=%s swirl_q_model=%s swirl_rag_model=%s",
            bool(key),
            bool(self._openapi_key),
            self._azure_model,
            bool(self._azureapi_key),
            self._azure_endpoint,
            self._swirl_rw_model,
            self._swirl_q_model,
            self._swirl_rag_model,
        )

        self._api_provider = None
        self._api_key = None

        # If a key is explicitly provided, treat it as an OpenAI key.
        #    This allows provider-level credentials (like GenAI) to use
        #    OpenAI even when Azure is globally configured.
        if key:
            self._api_provider = "OPENAI"
            self._api_key = key

        # Otherwise, prefer Azure if fully configured...
        elif self._azureapi_key and self._azure_model and self._azure_endpoint:
            self._api_provider = "AZUREAI"
            self._api_key = self._azureapi_key

        # ...then fall back to OpenAI if available.
        elif self._openapi_key:
            self._api_provider = "OPENAI"
            self._api_key = self._openapi_key

        if not self._api_key:
            raise ValueError("API key is required to initialize OpenAIClient")

        self.openai_client = self._init_openai_client()

    def _init_openai_client(self):
        logger.debug("init_openai_client: provider=%s", self._api_provider)

        try:
            if self._api_provider == "OPENAI":
                from openai import OpenAI
                return OpenAI(api_key=self._api_key)
            elif self._api_provider == "AZUREAI":
                from openai import AzureOpenAI
                return AzureOpenAI(
                    api_key=self._api_key,
                    azure_endpoint=self._azure_endpoint,
                    api_version=self._azure_api_version,
                )
            else:
                raise NotImplementedError(
                    f"Unknown AI provider {self._api_provider}. "
                    "Client initialization not supported."
                )
        except Exception as err:
            # Let the caller see the original error
            raise err

    def _get_swirl_model_for_usage(self):
        """Return the SWIRL_* model configured for this usage."""
        if self._usage == AI_REWRITE_USE:
            model = self._swirl_rw_model
        elif self._usage == AI_QUERY_USE:
            model = self._swirl_q_model
        else:
            model = self._swirl_rag_model

        if self._api_provider == "OPENAI" and not model:
            raise ValueError(
                f"No SWIRL_* model configured for usage {self._usage}. "
                "Set SWIRL_REWRITE_MODEL / SWIRL_QUERY_MODEL / SWIRL_RAG_MODEL in your environment."
            )

        return model

    def get_model(self):
        """
        Return the model/deployment name to pass to chat.completions.

        - For AZUREAI, this is the Azure deployment name (AZURE_MODEL).
        - For OPENAI, this is one of SWIRL_REWRITE_MODEL / SWIRL_QUERY_MODEL / SWIRL_RAG_MODEL.
        """
        if self._api_provider == "AZUREAI" and self._azure_model:
            model = self._azure_model
        else:
            model = self._get_swirl_model_for_usage()

        logger.info("get model %s %s", self._api_provider, model)
        return model

    def get_encoding_model(self):
        """
        Return the model name used for token encoding.

        For now we just use the logical SWIRL_* model corresponding to this usage.
        This is what RagPrompt and any tiktoken-style logic should use.
        """
        return self._get_swirl_model_for_usage()
