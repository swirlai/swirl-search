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
        logger.info(f"{self}: init search rag {request_data}")
        self.search_id = request_data.get("search_id", None)

        # Parse query parameters
        self.rag_query_items = []
        rag_query_items = request_data.get("rag_items", [""])

        if rag_query_items:
            self.rag_query_items = rag_query_items.split(",")

    def get_rag_result(self) -> tuple[str, dict[str, str]]:
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
                if rag_result.json_results[0]["body"][0]:
                    return rag_result.json_results[0]["body"][0]
                return False
        except:
            pass
        rag_processor = RAGPostResultProcessor(
            search_id=self.search_id,
            request_id="",
            should_get_results=True,
            rag_query_items=self.rag_query_items,
        )
        instances[self.search_id] = rag_processor
        if rag_processor.validate():
            result = rag_processor.process(should_return=True)
            try:
                if self.search_id in instances:
                    del instances[self.search_id]
                return result.json_results[0]["body"][0]
            except:
                if self.search_id in instances:
                    del instances[self.search_id]
                return False

    def process_rag(self) -> dict[str, str]:
        result = ""
        try:
            result = self.get_rag_result()
        except RagError as err:
            logger.error(f"{self}: Rag Error {err}")

        return {"message": result}
