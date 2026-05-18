"""
@author:     Sid Probstein
@contact:    sid@swirl.today
"""

import copy
import json
import os
import threading
import time
from collections import OrderedDict

from django.db.models import Q

import logging
logger = logging.getLogger(__name__)

from abc import ABCMeta

import litellm

# Clear litellm's callback lists so no downstream logging handlers fire.
try:
    litellm.success_callback = []
    litellm.failure_callback = []
    litellm._async_success_callback = []
    litellm._async_failure_callback = []
except Exception as _e:
    logger.debug(f"litellm callback silencing skipped: {_e}")

# Suppress RuntimeWarnings litellm emits when its coroutines are GC'd.
import warnings as _warnings
_warnings.filterwarnings(
    "ignore",
    message=r"coroutine 'LoggingWorker\._worker_loop' was never awaited",
    category=RuntimeWarning,
)
_warnings.filterwarnings(
    "ignore",
    message=r"coroutine 'Logging\.async_success_handler' was never awaited",
    category=RuntimeWarning,
)

import numpy as np
import requests
import torch
from django.conf import settings
from openai import OpenAIError

# ---------------------------------------------------------------------------
# LiteLLM response cache (off by default; opt-in via settings)
# ---------------------------------------------------------------------------

def _configure_litellm_cache():
    enabled = getattr(settings, "SWIRL_LITELLM_CACHE_ENABLED", False)
    if not enabled:
        try:
            litellm.cache = None
        except Exception:
            pass
        return
    cache_type = getattr(settings, "SWIRL_LITELLM_CACHE_TYPE", "local")
    ttl = getattr(settings, "SWIRL_LITELLM_CACHE_TTL", 300)
    try:
        if cache_type == "redis":
            host = getattr(settings, "SWIRL_LITELLM_CACHE_REDIS_HOST", "")
            port = getattr(settings, "SWIRL_LITELLM_CACHE_REDIS_PORT", 6379)
            password = getattr(settings, "SWIRL_LITELLM_CACHE_REDIS_PASSWORD", "")
            if not host:
                logger.warning(
                    "SWIRL_LITELLM_CACHE_TYPE=redis but "
                    "SWIRL_LITELLM_CACHE_REDIS_HOST is empty; cache disabled."
                )
                litellm.cache = None
                return
            litellm.cache = litellm.Cache(
                type="redis", host=host, port=port, password=password, ttl=ttl,
            )
            logger.info(f"LiteLLM cache enabled: redis {host}:{port} ttl={ttl}s")
        else:
            litellm.cache = litellm.Cache(type="local", ttl=ttl)
            logger.info(f"LiteLLM cache enabled: local in-memory ttl={ttl}s")
    except Exception as cache_err:
        logger.warning(f"LiteLLM cache configuration failed ({cache_err}); cache disabled.")
        try:
            litellm.cache = None
        except Exception:
            pass


_configure_litellm_cache()

import swirl_server.celery as celery_init
from swirl.models import AIProvider
from swirl.spacy import get_sentence_vector, get_spacy_nlp

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EPS32: float = np.finfo(np.float32).eps

USE_FAST_SIMILARITY = getattr(settings, "SWIRL_USE_FAST_SIMILARITY", True)
USE_UNIT_EMBEDDINGS = getattr(settings, "SWIRL_USE_UNIT_EMBEDDINGS", True)


def pick_torch_device():
    override = os.environ.get("SWIRL_TORCH_DEVICE")
    if override:
        return override
    try:
        if torch.cuda.is_available():
            return "cuda"
        mps = getattr(torch.backends, "mps", None)
        if mps is not None and mps.is_available() and mps.is_built():
            return "mps"
    except Exception as err:
        logger.debug(f"pick_torch_device probe failed: {err}")
    return "cpu"


def _is_finite_1d(x: np.ndarray) -> bool:
    return x.ndim == 1 and np.isfinite(x).all()


# ---------------------------------------------------------------------------
# RequestPost helper classes
# ---------------------------------------------------------------------------

class ProviderMessage:
    def __init__(self, content):
        self.content = content


class ProviderChoice:
    def __init__(self, message):
        self.message = message


class ProviderCompletions:
    def __init__(self, choices):
        self.choices = choices


# ---------------------------------------------------------------------------
# LocalEmbeddingGenerator — HuggingFace / trusted remote code models
# ---------------------------------------------------------------------------

class LocalEmbeddingGenerator:
    def __init__(self, provider, cache_capacity=10000):
        self.provider = provider
        self.model_name = self.provider.model
        if "trusted_code_numpy_conversion" in self.provider.config:
            self.num_py_conversion = bool(self.provider.config["trusted_code_numpy_conversion"])
        else:
            self.num_py_conversion = False

        if self.model_name.startswith("huggingface/"):
            self.model_name = self.model_name[len("huggingface/"):]

        self.cache_capacity = cache_capacity
        self.embedding_cache = OrderedDict()
        self.cache_lock = threading.Lock()

    def _get_text_embedding(self, text):
        if not text:
            return None
        with self.cache_lock:
            cached = self.embedding_cache.get(text)
            if cached is not None:
                self.embedding_cache.move_to_end(text)
                return cached
        try:
            self.model = celery_init.models[self.model_name]
            self.tokenizer = celery_init.tokenizers[self.model_name]
            self.device = celery_init.device
            start = time.time()
            inputs = self.tokenizer(
                text, return_tensors="pt", truncation=True, max_length=512, padding=False,
            )
            with torch.no_grad():
                outputs = self.model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1)
            elapsed = time.time() - start
            logger.info(f"TRACE embedding generation({len(text)}): {elapsed:.4f}s")
            with self.cache_lock:
                self.embedding_cache[text] = embeddings
                self.embedding_cache.move_to_end(text)
                if len(self.embedding_cache) > self.cache_capacity:
                    self.embedding_cache.popitem(last=False)
            return embeddings
        except Exception as e:
            logger.error(f"Error during inference: {e}")
            raise

    def _get_embedding_local(self, text):
        return self._get_text_embedding(text)


# ---------------------------------------------------------------------------
# LLMWrapper
# ---------------------------------------------------------------------------

class LLMWrapper(metaclass=ABCMeta):

    def __init__(self, llm, ai_provider, fallback_list=None, tools_list=None, tools_choice=None):
        self.llm = llm
        self.provider = ai_provider
        self.fallback_list = fallback_list
        self.loaded_keys = []
        self.engine = None
        self.custom_llm = False
        self.use_trusted_remote_code_model = False
        self.custom_tokenizer_embedding_generator = None
        self._tools = tools_list if tools_list else []
        self._tool_choice = (tools_choice if tools_choice else "auto") if self._tools else None
        self._last_response_model = None

        if fallback_list is not None and not isinstance(self.fallback_list, list):
            logger.error("Fallback list is not a list!")
            return
        if not self.llm:
            logger.error("No LLM allocated")
            return
        if not self.provider:
            logger.error("No AIProvider found")
            return

        if self.provider.name.lower() == "spacy":
            return

        if logger.getEffectiveLevel() == logging.DEBUG:
            os.environ["LITELL_LOG"] = "DEBUG"
            if getattr(settings, "SWIRL_LITELLM_DEBUG", False):
                litellm_logger = logging.getLogger("LiteLLM")
                litellm_logger.setLevel(logging.DEBUG)

        litellm.drop_params = getattr(settings, "SWIRL_AI_DROP_UNSUP_PARAMS", True)
        litellm.modify_params = getattr(settings, "SWIRL_LITELLM_MODIFY_PARAMS", True)

        self.api_base = self.api_version = self.organization = None
        cfg = self.provider.config or {}
        if "api_base" in cfg:
            self.api_base = cfg["api_base"]
        if "api_version" in cfg:
            self.api_version = cfg["api_version"]
        if "organization" in cfg:
            self.organization = cfg["organization"]
        if "custom_llm" in cfg:
            self.custom_llm = cfg["custom_llm"]
        if "enable_trusted_remote_code" in cfg:
            self.use_trusted_remote_code_model = bool(cfg["enable_trusted_remote_code"])
            self.custom_tokenizer_embedding_generator = LocalEmbeddingGenerator(self.provider)

        self.use_sentence_transformers_model = bool(cfg.get("sentence_transformers"))

        if "engine" in cfg:
            if "requestpost" in cfg:
                raise ValueError("Engine cannot be set when requestpost is also set")
            self.engine = cfg["engine"]
        if "requestpost" in cfg:
            self.engine = "requestpost"

        skip_litellm_checks = (
            self.use_sentence_transformers_model
            or bool(cfg.get("cross_encoder"))
        )
        if not ("NO_KEY_CHECK" in cfg or self.engine == "requestpost" or skip_litellm_checks):
            if not self._check_valid_key():
                logger.warning(
                    f"Key {self.provider.api_key} not valid for model {self.provider.model}"
                )

        use_model_max_tokens = not (
            "NO_MODEL_CHECK" in cfg or self.engine == "requestpost" or skip_litellm_checks
        )
        max_tokens_override = cfg.get("max_tokens") or cfg.get("MAX_TOKENS")

        if use_model_max_tokens and max_tokens_override is not None:
            try:
                model_info = self.llm.get_model_info(model=self.provider.model)
                model_max = model_info.get("max_input_tokens", max_tokens_override)
                self.max_tokens = min(max_tokens_override, model_max)
            except Exception as e:
                logger.warning(f"Skipping model info for {self.provider.model}: {e}")
                self.max_tokens = max_tokens_override
        elif use_model_max_tokens:
            try:
                model_info = self.llm.get_model_info(model=self.provider.model)
                self.max_tokens = model_info.get(
                    "max_input_tokens", getattr(settings, "SWIRL_RAG_TOK_DEFAULT", 4000)
                )
            except Exception as e:
                logger.warning(f"Skipping model info for {self.provider.model}: {e}")
                self.max_tokens = getattr(settings, "SWIRL_RAG_TOK_DEFAULT", 4000)
        else:
            self.max_tokens = (
                max_tokens_override if max_tokens_override
                else getattr(settings, "SWIRL_RAG_TOK_DEFAULT", 4000)
            )

        self.llm.set_verbose = False
        if "set_verbose" in cfg:
            self.llm.set_verbose = True

        stdkeys = ["api_base", "api_version", "organization", "set_verbose",
                   "max_tokens", "engine", "requestpost"]
        self.loaded_keys = []
        for k in cfg:
            if k.lower() not in stdkeys:
                os.environ[k] = str(cfg[k])
                self.loaded_keys.append(k)

    def __str__(self):
        return f"{self.provider.name if self.provider else 'LLMWrapper'}"

    def get_provider(self):
        return self.provider

    def get_encoding_model(self):
        """
        Return a tiktoken-compatible model name for token counting.

        LiteLLM model strings often carry a provider prefix
        (e.g. 'anthropic/claude-3-5-sonnet', 'azure/my-deployment',
        'ollama/llama3.1:8b').  tiktoken only knows OpenAI model names,
        so we strip the prefix and fall back to 'gpt-4o' when the
        remainder isn't recognised.
        """
        model = (self.provider.model or '') if self.provider else ''
        # Strip provider prefix (everything up to and including the first '/')
        if '/' in model:
            model = model.split('/', 1)[1]
        # tiktoken probe — fall back to gpt-4o on KeyError
        try:
            import tiktoken
            tiktoken.encoding_for_model(model)
            return model
        except (KeyError, Exception):
            return 'gpt-4o'

    def reader(self):
        return self.llm

    def is_zero_vector(self, embedding):
        return np.all(embedding == 0)

    def _extract_completions(self, openai_response):
        if "error" in openai_response:
            logger.error(f"Error in completion: {openai_response['error']}")
            choices_list = [ProviderChoice(ProviderMessage(openai_response["error"]["message"]))]
            return ProviderCompletions(choices_list)
        choices_list = [
            ProviderChoice(ProviderMessage(choice["message"]["content"]))
            for choice in openai_response["choices"]
        ]
        return ProviderCompletions(choices_list)

    def _put_request_post_config_headers(self, headers=None):
        ret_headers = headers if headers else {}
        if not self.provider.config:
            return ret_headers
        if "headers" in self.provider.config.get("requestpost", {}):
            for k, v in self.provider.config["requestpost"]["headers"].items():
                ret_headers[k] = v
        return ret_headers

    def _put_request_post_config_body(self, body=None):
        ret_body = body if body else {}
        if not self.provider.config:
            return ret_body
        if "body" in self.provider.config.get("requestpost", {}):
            for k, v in self.provider.config["requestpost"]["body"].items():
                ret_body[k] = v
        return ret_body

    def _check_valid_key(self):
        messages = [{"role": "user", "content": "Hey, how's it going?"}]
        try:
            self.llm.completion(
                messages=messages,
                model=self.provider.model,
                api_key=self.provider.api_key,
                api_base=self.api_base,
                api_version=self.api_version,
                organization=self.organization,
                temperature=0,
                max_tokens=10,
                fallbacks=copy.deepcopy(self.fallback_list),
            )
            return True
        except litellm.AuthenticationError:
            logger.error(f"Authentication error for model {self.provider.model}")
            return False
        except Exception:
            logger.error(f"Unexpected error for model {self.provider.model}")
            return False

    def encode(self, messages):
        return self.llm.encode(self.provider.model, text=messages)

    def decode(self, enc_messages):
        return self.llm.decode(self.provider.model, tokens=enc_messages)

    def completion(self, messages, enable_tools=False, response_format=None,
                   timeout=None, stream=None, num_retries=None):
        """Run a completion via LiteLLM."""
        if "NO_MODEL_CHECK" not in (self.provider.config or {}):
            message_tok_count = self.llm.token_counter(self.provider.model, messages=messages)
            logger.info(f"message_tok_count: {message_tok_count}")

        custom_llm_provider = self.custom_llm if self.custom_llm else None

        if enable_tools:
            tools_arg = self._tools
            tools_choice_arg = self._tool_choice
        else:
            tools_arg = None
            tools_choice_arg = None

        if timeout is None:
            timeout = getattr(settings, "SWIRL_LITELLM_TIMEOUT", 90)

        extra_kwargs = {}
        if response_format is not None:
            extra_kwargs["response_format"] = response_format
        if timeout is not None:
            extra_kwargs["timeout"] = timeout
        if stream:
            extra_kwargs["stream"] = True
        if num_retries is not None:
            extra_kwargs["num_retries"] = num_retries

        if self.engine:
            if self.engine == "requestpost":
                try:
                    headers = self._put_request_post_config_headers(
                        headers={"Content-Type": "application/json"}
                    )
                    body = self._put_request_post_config_body(body={"messages": messages})
                    response = requests.post(
                        self.provider.config["api_base"], json=body, headers=headers
                    )
                    response = response.json()
                    content = None
                    content_s = response.get("result", {})
                    if content_s:
                        content_j = json.loads(content_s)
                        content = content_j.get("content", None)
                    if content:
                        openai_response = {"choices": [{"message": {"content": content}}]}
                    else:
                        openai_response = response
                    return self._extract_completions(openai_response)
                except requests.exceptions.RequestException as req_err:
                    logger.error(f"Network error posting completion: {req_err}")
                    return self._extract_completions(
                        {"choices": [{"message": {"content": f"Network error: {req_err}"}}]}
                    )
                except Exception as err:
                    logger.error(f"Error posting completion: {err}")
                    return self._extract_completions(
                        {"choices": [{"message": {"content": f"Error: {err}"}}]}
                    )
            try:
                response = self.llm.completion(
                    messages=messages,
                    engine=self.engine,
                    api_key=self.provider.api_key,
                    api_base=self.api_base,
                    api_version=self.api_version,
                    organization=self.organization,
                    custom_llm_provider=custom_llm_provider,
                    temperature=0,
                    fallbacks=copy.deepcopy(self.fallback_list),
                    tools=tools_arg,
                    tool_choice=tools_choice_arg,
                    **extra_kwargs,
                )
            except OpenAIError as err:
                logger.error(f"Error generating completion: {err}")
                raise
        else:
            try:
                response = self.llm.completion(
                    messages=messages,
                    model=self.provider.model,
                    api_key=self.provider.api_key,
                    api_base=self.api_base,
                    api_version=self.api_version,
                    organization=self.organization,
                    custom_llm_provider=custom_llm_provider,
                    temperature=0,
                    fallbacks=copy.deepcopy(self.fallback_list),
                    tools=tools_arg,
                    tool_choice=tools_choice_arg,
                    **extra_kwargs,
                )
            except OpenAIError as err:
                logger.error(f"Error generating completion: {err}")
                raise

        try:
            self._last_response_model = getattr(response, "model", None)
        except Exception:
            self._last_response_model = None
        return response

    def completion_stream(self, messages, on_chunk=None, enable_tools=False,
                          response_format=None, timeout=None, num_retries=None):
        """Run a streaming completion, accumulate and return (full_text, raw_response)."""
        if self.engine == "requestpost":
            raise ValueError(
                "completion_stream() is not supported with the requestpost engine."
            )
        gen = self.completion(
            messages=messages, enable_tools=enable_tools,
            response_format=response_format, timeout=timeout,
            stream=True, num_retries=num_retries,
        )
        full = []
        last_model = None
        last_chunk = None
        try:
            for chunk in gen:
                last_chunk = chunk
                delta_text = ""
                try:
                    choices = getattr(chunk, "choices", None) or []
                    if choices:
                        delta = getattr(choices[0], "delta", None)
                        if delta is not None:
                            delta_text = getattr(delta, "content", "") or ""
                except Exception as err:
                    logger.debug(f"streaming chunk parse skipped: {err}")
                if delta_text:
                    full.append(delta_text)
                    if on_chunk is not None:
                        try:
                            on_chunk(delta_text, "".join(full))
                        except Exception as cb_err:
                            logger.warning(f"completion_stream on_chunk callback raised: {cb_err}")
                m = getattr(chunk, "model", None)
                if m and not last_model:
                    last_model = m
        finally:
            if last_model:
                self._last_response_model = last_model
        return "".join(full), last_chunk

    def embedding(self, text, text_type="passage"):
        """Generate an embedding for the given text."""
        cache = getattr(self, "_embed_cache", None)
        if cache is not None:
            cached = cache.get((text, text_type))
            if cached is not None:
                return cached

        prefixed_text = text
        try:
            cfg = self.provider.config or {}
            if text_type == "query" and cfg.get("query_prefix"):
                prefixed_text = cfg["query_prefix"] + text
            elif text_type == "passage" and cfg.get("passage_prefix"):
                prefixed_text = cfg["passage_prefix"] + text
        except Exception as prefix_err:
            logger.debug(f"embedding prefix resolution failed: {prefix_err}")

        if self.provider.name.lower() == "spacy":
            return get_sentence_vector(prefixed_text)
        elif getattr(self, "use_sentence_transformers_model", False):
            return self._embedding_sentence_transformers(prefixed_text)
        elif getattr(self, "use_trusted_remote_code_model", False):
            return self.custom_tokenizer_embedding_generator._get_embedding_local(prefixed_text)
        else:
            custom_llm_provider = self.custom_llm if self.custom_llm else None
            try:
                text_embedding = self.llm.embedding(
                    input=prefixed_text,
                    model=self.provider.model,
                    api_key=self.provider.api_key,
                    api_base=self.api_base,
                    api_version=self.api_version,
                    organization=self.organization,
                    custom_llm_provider=custom_llm_provider,
                )
            except OpenAIError as err:
                logger.error(f"Error generating embedding: {err}")
                return None
            if text_embedding:
                data = text_embedding.get("data") if isinstance(text_embedding, dict) else getattr(text_embedding, "data", None)
                if data and len(data) > 0:
                    row = data[0]
                    emb = row.get("embedding") if isinstance(row, dict) else getattr(row, "embedding", None)
                    return emb
        return None

    def _embedding_sentence_transformers(self, text):
        if not text:
            return None
        vecs = self._embedding_sentence_transformers_batch([text])
        return vecs[0] if vecs else None

    def _embedding_sentence_transformers_batch(self, texts):
        if not texts:
            return []
        model_name = self.provider.model
        if model_name.startswith("huggingface/"):
            model_name = model_name[len("huggingface/"):]
        st_models = getattr(celery_init, "sentence_transformer_models", None)
        if not st_models or model_name not in st_models:
            logger.warning(f"sentence-transformers model '{model_name}' not loaded")
            return [None] * len(texts)
        st_model = st_models[model_name]
        to_encode = []
        idx_map = []
        for i, t in enumerate(texts):
            if t:
                idx_map.append(i)
                to_encode.append(t)
        if not to_encode:
            return [None] * len(texts)
        try:
            start = time.time()
            vecs = st_model.encode(
                to_encode,
                batch_size=int(getattr(settings, "SWIRL_ST_BATCH_SIZE", 32)),
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            elapsed = time.time() - start
            logger.info(f"TRACE sentence-transformers embedding_batch({len(to_encode)}): {elapsed:.4f}s")
        except Exception as err:
            logger.error(f"sentence-transformers batch embedding failed: {err}")
            return [None] * len(texts)
        out = [None] * len(texts)
        for src_i, vec in zip(idx_map, vecs):
            out[src_i] = vec.tolist() if hasattr(vec, "tolist") else list(vec)
        return out

    def _is_ollama_provider(self):
        try:
            model = (self.provider.model or "").lower()
            if model.startswith("ollama/"):
                return True
            cfg = self.provider.config or {}
            if (cfg.get("engine") or "").lower() == "ollama":
                return True
            api_base = (self.api_base or "").lower()
            if "11434" in api_base or "ollama" in api_base:
                return True
        except Exception:
            return False
        return False

    def _embedding_ollama_batch(self, texts):
        if not texts:
            return []
        to_encode = []
        idx_map = []
        for i, t in enumerate(texts):
            if t:
                idx_map.append(i)
                to_encode.append(t)
        if not to_encode:
            return [None] * len(texts)
        try:
            chunk_size = int(getattr(settings, "SWIRL_OLLAMA_EMBED_BATCH_SIZE", 128))
        except Exception:
            chunk_size = 128
        if chunk_size <= 0:
            chunk_size = 128
        custom_llm_provider = self.custom_llm if self.custom_llm else None
        all_vecs = []
        for ofs in range(0, len(to_encode), chunk_size):
            chunk = to_encode[ofs:ofs + chunk_size]
            try:
                resp = self.llm.embedding(
                    input=chunk,
                    model=self.provider.model,
                    api_key=self.provider.api_key,
                    api_base=self.api_base,
                    api_version=self.api_version,
                    organization=self.organization,
                    custom_llm_provider=custom_llm_provider,
                )
            except Exception as err:
                logger.warning(f"litellm batch embed failed ({self.provider.model}, {len(chunk)} texts): {err}")
                return None
            data = resp["data"] if isinstance(resp, dict) else getattr(resp, "data", None)
            if not isinstance(data, list) or len(data) != len(chunk):
                logger.warning("litellm batch embed unexpected response shape")
                return None
            for row in data:
                vec = row.get("embedding") if isinstance(row, dict) else getattr(row, "embedding", None)
                all_vecs.append(vec if isinstance(vec, list) else None)
        out = [None] * len(texts)
        for src_i, vec in zip(idx_map, all_vecs):
            out[src_i] = vec
        return out

    def embedding_batch(self, texts, text_type="passage"):
        """Batched embedding. Returns list[list[float] | None] same length as texts."""
        if not texts:
            return []
        cache = getattr(self, "_embed_cache", None)
        if cache is not None:
            out_cached = [cache.get((t, text_type)) if t else None for t in texts]
            if all(v is not None for t, v in zip(texts, out_cached) if t):
                return out_cached
        cfg = self.provider.config or {}
        prefix = None
        if text_type == "query" and cfg.get("query_prefix"):
            prefix = cfg["query_prefix"]
        elif text_type == "passage" and cfg.get("passage_prefix"):
            prefix = cfg["passage_prefix"]
        missing_idx = []
        missing_text = []
        for i, t in enumerate(texts):
            if not t:
                continue
            if cache is not None and cache.get((t, text_type)) is not None:
                continue
            missing_idx.append(i)
            missing_text.append(t)
        new_vecs = []
        if missing_text:
            if getattr(self, "use_sentence_transformers_model", False):
                prefixed = [(prefix + t if (prefix and t) else t) for t in missing_text]
                new_vecs = self._embedding_sentence_transformers_batch(prefixed)
            elif self._is_ollama_provider():
                prefixed = [(prefix + t if (prefix and t) else t) for t in missing_text]
                new_vecs = self._embedding_ollama_batch(prefixed)
                if new_vecs is None:
                    new_vecs = []
                    for t in missing_text:
                        try:
                            new_vecs.append(self.embedding(t, text_type=text_type))
                        except TypeError:
                            new_vecs.append(self.embedding(t))
            else:
                new_vecs = []
                for t in missing_text:
                    try:
                        new_vecs.append(self.embedding(t, text_type=text_type))
                    except TypeError:
                        new_vecs.append(self.embedding(t))
            if cache is not None:
                for t, v in zip(missing_text, new_vecs):
                    if v is not None:
                        cache[(t, text_type)] = v
        out = [None] * len(texts)
        new_by_idx = dict(zip(missing_idx, new_vecs))
        for i, t in enumerate(texts):
            if not t:
                out[i] = None
                continue
            fresh = new_by_idx.get(i)
            if fresh is not None:
                out[i] = fresh
            elif cache is not None:
                out[i] = cache.get((t, text_type))
            else:
                out[i] = None
        return out

    def prefetch_embeddings(self, texts, text_type="passage"):
        """Batch-embed texts and stash in self._embed_cache for fast lookup."""
        if not texts:
            return
        cache = getattr(self, "_embed_cache", None)
        if cache is None:
            cache = {}
            self._embed_cache = cache
        seen = set()
        uncached = []
        for t in texts:
            if not t:
                continue
            key = (t, text_type)
            if key in seen or cache.get(key) is not None:
                continue
            seen.add(key)
            uncached.append(t)
        if not uncached:
            return
        try:
            vecs = self.embedding_batch(uncached, text_type=text_type)
        except Exception as err:
            logger.warning(f"prefetch_embeddings failed: {err}")
            return
        for t, v in zip(uncached, vecs):
            if v is not None:
                cache[(t, text_type)] = v

    def clear_embed_cache(self):
        self._embed_cache = {}

    def rerank(self, query, documents):
        """Score (query, document) pairs with a cross-encoder reranker."""
        if not documents:
            return []
        model_name = self.provider.model
        if model_name.startswith("huggingface/"):
            model_name = model_name[len("huggingface/"):]
        cross_encoders = getattr(celery_init, "cross_encoders", None)
        if cross_encoders is None:
            cross_encoders = {}
            celery_init.cross_encoders = cross_encoders
        import os as _os
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        if model_name not in cross_encoders:
            _os.environ["TOKENIZERS_PARALLELISM"] = "false"
            device = "cpu"
            max_length = int((self.provider.config or {}).get("max_length", 512))
            logger.warning(f"rerank: lazy-loading cross-encoder {model_name!r} on {device}")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            model.to(device)
            model.eval()
            cross_encoders[model_name] = {
                "model": model, "tokenizer": tokenizer,
                "device": device, "max_length": max_length,
            }
        ce = cross_encoders[model_name]
        pairs = [(query, doc) for doc in documents]
        try:
            encoded = ce["tokenizer"](
                pairs, padding=True, truncation=True,
                max_length=ce["max_length"], return_tensors="pt",
            )
            encoded = {k: v.to(ce["device"]) for k, v in encoded.items()}
            with torch.no_grad():
                logits = ce["model"](**encoded).logits
            if logits.dim() == 2 and logits.shape[1] == 1:
                scores = logits.squeeze(1)
            else:
                scores = logits[:, 0] if logits.dim() == 2 else logits
            scores = scores.cpu().numpy()
        except Exception as err:
            logger.error(f"Cross-encoder inference failed: {err}")
            raise
        return [float(s) for s in scores]

    def cosine_unit(self, a_u16, b_u16) -> float:
        a = np.asarray(a_u16, dtype=np.float32, order="C")
        b = np.asarray(b_u16, dtype=np.float32, order="C")
        if not (_is_finite_1d(a) and _is_finite_1d(b)) or a.size != b.size:
            return 0.0
        if not a.any() or not b.any():
            return 0.0
        return float(np.clip(np.dot(a, b), -1.0, 1.0))

    def _cosine_generic_fp32(self, e1, e2) -> float:
        a = np.asarray(e1, dtype=np.float32, order="C")
        b = np.asarray(e2, dtype=np.float32, order="C")
        if not (_is_finite_1d(a) and _is_finite_1d(b)) or a.size != b.size:
            return 0.0
        n1 = float(np.linalg.norm(a))
        n2 = float(np.linalg.norm(b))
        denom = max(n1 * n2, _EPS32)
        return float(np.clip(np.dot(a, b) / denom, -1.0, 1.0))

    def _fast_similarity(self, e1, e2):
        if USE_UNIT_EMBEDDINGS:
            return self.cosine_unit(e1, e2)
        return self._cosine_generic_fp32(e1, e2)

    def similarity(self, embedding1, embedding2):
        if USE_FAST_SIMILARITY:
            return self._fast_similarity(embedding1, embedding2)
        a = np.asarray(embedding1, dtype=np.float32, order="C")
        b = np.asarray(embedding2, dtype=np.float32, order="C")
        n1 = float(np.linalg.norm(a))
        n2 = float(np.linalg.norm(b))
        denom = max(n1 * n2, _EPS32)
        return float(np.clip(np.dot(a, b) / denom, -1.0, 1.0))

    def similarity_text(self, text1, text2):
        return self.similarity(self.embedding(text1), self.embedding(text2))

    def get_last_completion_info(self):
        """Return a dict describing what actually ran on the last completion() call."""
        info = {
            "requested_model": getattr(self.provider, "model", None),
            "requested_provider_name": getattr(self.provider, "name", None),
            "actual_model": self._last_response_model,
            "actual_provider_name": None,
            "fallback_engaged": False,
        }
        if not info["actual_model"]:
            return info
        req = (info["requested_model"] or "").lower()
        act = (info["actual_model"] or "").lower()
        if req and act and req != act and not (req.endswith(act) or act.endswith(req)):
            info["fallback_engaged"] = True
        elif not req and act:
            info["fallback_engaged"] = True
        if info["fallback_engaged"]:
            try:
                for fb in (self.fallback_list or []):
                    fb_model = (fb.get("model") or "").lower()
                    if fb_model and (fb_model == act or act.endswith(fb_model) or fb_model.endswith(act)):
                        try:
                            ap = AIProvider.objects.filter(model=fb.get("model"), active=True).first()
                            if ap:
                                info["actual_provider_name"] = ap.name
                                break
                        except Exception:
                            pass
            except Exception:
                pass
            if not info["actual_provider_name"]:
                try:
                    for ap in AIProvider.objects.filter(active=True).only("name", "model"):
                        ap_model = (ap.model or "").lower()
                        if ap_model and (ap_model == act or act.endswith(ap_model) or ap_model.endswith(act)):
                            info["actual_provider_name"] = ap.name
                            break
                except Exception:
                    pass
        else:
            info["actual_provider_name"] = info["requested_provider_name"]
        return info

    def get_swirl_config(self):
        if not (self.provider and self.provider.config):
            return None
        try:
            return self.provider.config.get("swirl", None)
        except Exception as e:
            logger.error(f"{e} while getting swirl config")
        return None

    def __del__(self):
        if self.loaded_keys:
            for k in self.loaded_keys:
                if k in os.environ:
                    del os.environ[k]


# ---------------------------------------------------------------------------
# AIProviderFactory
# ---------------------------------------------------------------------------

class AIProviderFactory(metaclass=ABCMeta):

    def __init__(self):
        self.provider = None
        self.fallback_list = []

    def alloc_ai_provider(
        self,
        request_type_tag,
        owner=None,
        options=None,
        tools=None,
        tools_choice=None,
        provider_id=None,
    ):
        """
        Allocate an LLMWrapper for the given request_type_tag.

        provider_id: optional override — when supplied and it resolves to an
        active provider tagged with request_type_tag, that provider wins.
        Falls back to defaults → tag logic when the override doesn't resolve.
        """
        if options and options.get("unit_test", False):
            active_providers = AIProvider.objects.filter(active=True)
        elif owner:
            active_providers = AIProvider.objects.filter(
                Q(shared=True) | Q(owner=owner)
            ).filter(active=True)
        else:
            active_providers = AIProvider.objects.filter(shared=True, active=True)

        if not active_providers:
            logger.warning("No active AI providers available")
            return None

        provider_candidates = []
        default_candidates = []
        override_provider = None

        for provider in active_providers:
            has_tag = any(t.lower() == request_type_tag.lower() for t in provider.tags)
            if has_tag:
                provider_candidates.append(provider)
            if any(d.lower() == request_type_tag.lower() for d in provider.defaults):
                default_candidates.append(provider)
            if (
                provider_id is not None
                and str(provider.id) == str(provider_id)
                and has_tag
            ):
                override_provider = provider

        if override_provider is not None:
            self.provider = override_provider
            provider_candidates = [p for p in provider_candidates if p.id != override_provider.id]
            default_candidates = [p for p in default_candidates if p.id != override_provider.id]
        elif default_candidates:
            self.provider = default_candidates.pop(0)
        elif provider_candidates:
            self.provider = provider_candidates.pop(0)
        else:
            logger.debug(f"No AI Providers configured for type {request_type_tag}")
            return None

        # Build the fallback list — family-restricted by default.
        fallback_fields = ["api_key", "api_base", "api_version", "model", "organization"]
        fallback_providers = list(dict.fromkeys(
            [fp for fp in (provider_candidates + default_candidates) if fp != self.provider]
        ))

        try:
            primary_family = self.provider.get_family()
        except Exception:
            primary_family = (self.provider.name or "").lower()

        cross_family_fallback = bool((self.provider.config or {}).get("cross_family_fallback"))
        if not cross_family_fallback:
            same_family = []
            for fp in fallback_providers:
                try:
                    fp_family = fp.get_family()
                except Exception:
                    fp_family = (fp.name or "").lower()
                if fp_family == primary_family:
                    same_family.append(fp)
            fallback_providers = same_family

        self.fallback_list = []
        for provider in fallback_providers:
            provider_dict = {}
            for field in fallback_fields:
                provider_dict[field] = None
                if field in (provider.config or {}):
                    provider_dict[field] = provider.config[field]
                if hasattr(provider, field):
                    provider_dict[field] = getattr(provider, field, None)
            self.fallback_list.append(provider_dict)

        logger.debug(f"Selected AI Provider: {self.provider.name}")
        logger.debug(f"Fallback list: {self.fallback_list}")

        if self.provider.name.lower() == "spacy":
            wrapped_llm = LLMWrapper(
                get_spacy_nlp(), self.provider, self.fallback_list, tools, tools_choice
            )
        else:
            llm = litellm
            llm.telemetry = False
            wrapped_llm = LLMWrapper(llm, self.provider, self.fallback_list, tools, tools_choice)

        return wrapped_llm if wrapped_llm else None
