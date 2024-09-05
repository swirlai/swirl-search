from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

import re

from urllib.parse import urlparse

import tiktoken

MODEL_DEFAULT_SYSTEM_GUIDE = "You are a helpful assistant who considers recent information when responding. You are positive and do not report negative or upsetting things, like poor ratings."

RAG_PROMPT_CHUNK_OK = "OK"
RAG_PROMPT_CHUNK_TOOSHORT = "TOO SHORT"
RAG_PROMPT_CHUNK_BAD_TYPE = "BAD TYPE"
RAG_PROMPT_CHUNK_MISSING_TERMS = "MISSING TERMS"
RAG_PROMPT_CHUNK_NO_TERMS = "NO TERMS"
class RagPrompt():

    def __str__(self):
        return f"{self.__class__.__name__}"

    def __init__(self, query, max_tokens, model):
        self._query = query
        self._max_tokens = max_tokens
        self._model = model
        self._prompt_text = f"Answer this query '{query}' given the following recent search results as background information. Do not mention that you are using the provided background information. Please cite the sources at the end of your response. Ignore information that is off-topic or obviously conflicting, without warning about it."
        self._is_full = False
        self._num_tokens = 0
        self._last_chunk_status = RAG_PROMPT_CHUNK_OK
        self._model_encoding = tiktoken.encoding_for_model(model)

        self._prompt_footer = (
        f"\n\n\n\n--- Final Instructions ---\nIn your response do not assume people with vastly different work histories are the same person. "
        f"If the query appears to be a proper name, focus on answering the question, 'Who is?' or 'What is?', as appropriate. "
        f"If the query appears to be a question, then try to answer it. "
        f"For the list of sources, use the HTML tags and format in the example below, do not generate duplicate entries, one entry per source.:\n"
        f"\n<p>"
        f"\n<br><b>Sources:</b>"
        f"\n<br><i>example description 1</i> &nbsp;&nbsp;&nbsp; <b>example URL or source name 1</b>"
        f"\n<br><i>example description 2</i> &nbsp;&nbsp;&nbsp; <b>example URL or source name 2</b>"
        f"\n</p>"
        f"\n\nEnclose your response in HTML tags <p></p> and insert a <br> HTML tag every two sentences."
        )

    def get_num_tokens(self):
        return self._num_tokens

    def is_full(self):
        return self._num_tokens >= self._max_tokens

    def _all_tokens_exist(self, string1, string2):
        tokens1 = set(string1.lower().split())
        tokens2 = set(string2.lower().split())
        return tokens1.issubset(tokens2)

    def _no_tokens_exist(self, string1, string2):
        tokens1 = set(string1.lower().split())
        tokens2 = set(string2.lower().split())
        return not tokens1.intersection(tokens2)

    def _is_good_chunk(self,chunk, file_type):
        # too short in relation to the query
        self._last_chunk_status = RAG_PROMPT_CHUNK_OK
        ca = chunk.split()
        qa = self._query.split()
        if len(ca) < len(qa) + 5:
            self._last_chunk_status = RAG_PROMPT_CHUNK_TOOSHORT
            return False
        if file_type and file_type == "pdf":
            self._last_chunk_status = RAG_PROMPT_CHUNK_BAD_TYPE
            return False

        if self._no_tokens_exist(self._query,chunk):
            self._last_chunk_status = RAG_PROMPT_CHUNK_NO_TERMS
            return False

        return True

    def _count_model_tokens_in_string(self, str):
        """Returns the number of tokens in a text string."""
        num_tokens = len(self._model_encoding.encode(str))
        return num_tokens

    def _trim_punctuation(self,s):
        return re.sub(r'^[^\w]+|[^\w]+$', '', s)

    def _sprint_chunk(self, chunk, domain, type, file_type):
        if not self._is_good_chunk(chunk=chunk, file_type=file_type):
            return "" # does not add value
        if type and type.lower() == "organization": type = "organization description"
        return f"\n\nConsider the following {type if type else ''}, it is about or mentions the query terms '{self._query}' from the website {domain}\n:{self._trim_punctuation(chunk)}"

    def is_last_chunk_added(self):
        return self._last_chunk_status == RAG_PROMPT_CHUNK_OK

    def get_last_chunk_status(self):
        return self._last_chunk_status

    def put_chunk(self, chunk, url, type, filter_file_type=True):
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        # Extract the file extension
        file_type = None
        if filter_file_type:
            path_parts = parsed_url.path.split('.')
            if len(path_parts) > 1:
                file_type = path_parts[-1]

        if not chunk:
            self.is_full()
        if self.is_full():
            return self._is_full()
        try:
            new_content = self._sprint_chunk(domain=domain,type=type, chunk=chunk, file_type=file_type)
            if not new_content:
                return self.is_full()

            n  = self._count_model_tokens_in_string(new_content)
            while self._num_tokens + n > self._max_tokens:
                nca = new_content.split()
                excess_tokens = (self._num_tokens + n) - self._max_tokens
                nca = nca[:-excess_tokens] if excess_tokens <= len(nca) else []
                new_content = " ".join(nca)
                n  = self._count_model_tokens_in_string(new_content)

            self._prompt_text = self._prompt_text + new_content + " "
            self._num_tokens = self._num_tokens + n
            self._last_chunk_status = RAG_PROMPT_CHUNK_OK
        except Exception as err:
            logger.info(f"{self} {err} while putting chunk")
        finally:
            return self.is_full()

    def get_promp_text(self):
        logger.info(f'{self} : max_tokens:{self._max_tokens} num_tokens {self.get_num_tokens()} is_full:{self.is_full()}')
        return self._prompt_text + self._prompt_footer

    def get_role_system_guide_text(self):
        return MODEL_DEFAULT_SYSTEM_GUIDE
