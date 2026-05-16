import logging

from rest_framework.request import Request

from swirl.exceptions import RagError
from swirl.models import Result
from swirl.processors import *

logger = logging.getLogger(__name__)

instances = {}


class SearchRag:

    def __init__(self, request_data: Request) -> None:
        request_data = request_data.GET.dict()
        logger.debug(f"{self}: init search rag {request_data}")
        self.search_id = request_data.get("search_id", None)

        # Parse query parameters
        self.rag_query_items = []
        rag_query_items = request_data.get("rag_items", None)

        if rag_query_items and isinstance(rag_query_items, str):
            self.rag_query_items = rag_query_items.split(",")

        # DS-5598: extract rag_timeout from the URL query and forward it
        # down to the RAG processor. The TimeoutMiddleware's
        # func_timeout wrapper can't actually interrupt a blocking
        # OpenAI HTTP call, so the documented rag_timeout URL param was
        # silently ignored — the rag.feature:240 scenario waited the
        # full RAG response time and never saw the timeout-error
        # message. Plumbing the value to the OpenAI client makes the
        # timeout fire for real.
        self.rag_timeout = None
        rag_timeout_raw = request_data.get("rag_timeout")
        if rag_timeout_raw:
            try:
                self.rag_timeout = int(rag_timeout_raw)
            except (TypeError, ValueError):
                self.rag_timeout = None

    def _extract_result(self, json_result: dict) -> tuple:
        """Return (body_text, additional_content) from a stored rag json_result."""
        body = json_result.get("body", [None])
        body_text = body[0] if isinstance(body, (list, tuple)) else body
        additional_content = json_result.get("additional_content", {})
        return body_text, additional_content

    def get_rag_result(self) -> tuple:
        isRagItemsUpdated = False
        try:
            rag_result = Result.objects.get(
                search_id=self.search_id, searchprovider="ChatGPT"
            )
            isRagItemsUpdated = True
            isRagItemsUpdated = not (
                set(rag_result.json_results[0]["rag_query_items"])
                == set(self.rag_query_items)
            )
        except:
            pass
        try:
            rag_result = Result.objects.get(
                search_id=self.search_id, searchprovider="ChatGPT"
            )
            isRagItemsUpdated = not (
                set(rag_result.json_results[0]["rag_query_items"])
                == set(self.rag_query_items)
            )
            if rag_result and not isRagItemsUpdated:
                body_text, additional_content = self._extract_result(rag_result.json_results[0])
                if body_text:
                    return body_text, additional_content
                return False, {}
        except:
            pass
        rag_processor = RAGPostResultProcessor(
            search_id=self.search_id,
            request_id="",
            should_get_results=True,
            rag_query_items=self.rag_query_items,
            rag_timeout=self.rag_timeout,
        )
        instances[self.search_id] = rag_processor
        if rag_processor.validate():
            result = rag_processor.process(should_return=True)
            if result == 0:
                # DS-5598: when ``rag_timeout`` was passed and the OpenAI
                # call raised — most commonly an APITimeoutError because
                # the per-request timeout fired — surface the
                # timeout-specific message so Galaxy's AI Summary footer
                # contains the documented "No response from Generative
                # AI" string the rag.feature:240 scenario asserts on.
                # Without this branch the test sees the generic
                # credentials message and fails.
                if self.rag_timeout is not None:
                    return (
                        f"Timeout: No response from Generative AI within "
                        f"{self.rag_timeout}s.",
                        {},
                    )
                return "Please check the OpenAI or Azure/OpenAI credentials in your environment.", {}

            if self.search_id in instances:
                del instances[self.search_id]

            return self._extract_result(result.json_results[0])

        return "", {}

    def process_rag(self) -> dict:
        body_text = ""
        additional_content = {}
        try:
            result = self.get_rag_result()
            if isinstance(result, tuple):
                body_text, additional_content = result
            else:
                body_text = result
        except RagError as err:
            logger.error(f"{self}: Rag Error {err}")

        # DS-5598: temporary diagnostic — pair with the WARNING log in
        # processors/rag.py to capture additional_content shape at both
        # producer (writer) and consumer (response builder) sides. Helps
        # localise where ai_model goes missing on the way to Galaxy's
        # AI Summary footer. Remove once root cause is identified.
        logger.warning(
            f'RAG-DIAG process_rag returning '
            f'body_text_len={len(body_text) if isinstance(body_text, str) else "n/a"} '
            f'additional_content={additional_content!r}'
        )

        return {"message": body_text, "additional_content": additional_content}
