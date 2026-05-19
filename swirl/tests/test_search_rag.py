"""
Unit tests for the SearchRag helper and DetailSearchRagSerializer.

Covers DS-5598 additional_content (RAG citations) plumbing:
- SearchRag._extract_result returns (body_text, additional_content)
- DetailSearchRagSerializer accepts and round-trips additional_content

Run with:  pytest swirl/tests/test_search_rag.py -v
"""

import pytest

from swirl.serializers import DetailSearchRagSerializer
from swirl.views_helpers.search_rag import SearchRag


class _FakeGet:
    def __init__(self, data):
        self._data = data

    def dict(self):
        return dict(self._data)


class _FakeRequest:
    def __init__(self, data=None):
        self.GET = _FakeGet(data or {})


def _make_search_rag(rag_items=None):
    data = {}
    if rag_items is not None:
        data["rag_items"] = rag_items
    return SearchRag(_FakeRequest(data))


# ---------------------------------------------------------------------------
# SearchRag.__init__ — rag_timeout extraction
# ---------------------------------------------------------------------------

def test_rag_timeout_absent_defaults_to_none():
    sr = SearchRag(_FakeRequest({}))
    assert sr.rag_timeout is None


def test_rag_timeout_integer_string_is_parsed():
    sr = SearchRag(_FakeRequest({"rag_timeout": "2"}))
    assert sr.rag_timeout == 2


def test_rag_timeout_non_integer_is_ignored():
    sr = SearchRag(_FakeRequest({"rag_timeout": "not-a-number"}))
    assert sr.rag_timeout is None


# ---------------------------------------------------------------------------
# SearchRag.__init__ — ai_instructions extraction
# ---------------------------------------------------------------------------

def test_ai_instructions_absent_defaults_to_empty_string():
    sr = SearchRag(_FakeRequest({}))
    assert sr.ai_instructions == ""


def test_ai_instructions_is_extracted_from_request():
    sr = SearchRag(_FakeRequest({"ai_instructions": "Respond in bullet points."}))
    assert sr.ai_instructions == "Respond in bullet points."


def test_ai_instructions_is_trimmed():
    sr = SearchRag(_FakeRequest({"ai_instructions": "   keep under 100 words   "}))
    assert sr.ai_instructions == "keep under 100 words"


def test_ai_instructions_capped_at_2000_chars():
    # Defensive bound — keeps a megabyte payload from blowing up the
    # prompt token budget. The actual prompt limit is RAG_MAX_TOKENS;
    # this is just a fast upfront sanity cap.
    sr = SearchRag(_FakeRequest({"ai_instructions": "x" * 5000}))
    assert len(sr.ai_instructions) == 2000


# ---------------------------------------------------------------------------
# RagPrompt — query_instructions weaving
# ---------------------------------------------------------------------------

def test_rag_prompt_without_instructions_omits_clause():
    from swirl.rag_prompt import RagPrompt

    p = RagPrompt(query="diabetes treatments", max_tokens=4000, model="gpt-4")
    assert "user-provided instructions" not in p._prompt_text
    assert "diabetes treatments" in p._prompt_text


def test_rag_prompt_with_instructions_weaves_clause():
    from swirl.rag_prompt import RagPrompt

    p = RagPrompt(
        query="diabetes treatments",
        max_tokens=4000,
        model="gpt-4",
        query_instructions="Respond in markdown bullet points.",
    )
    assert "user-provided instructions" in p._prompt_text
    assert "Respond in markdown bullet points." in p._prompt_text
    # Original query phrasing preserved before the instruction clause.
    assert "Answer this query 'diabetes treatments'" in p._prompt_text


def test_rag_prompt_with_blank_instructions_treated_as_absent():
    # Galaxy's URL param can be present-but-empty (?ai_instructions=).
    # Whitespace-only should also be treated as no instructions.
    from swirl.rag_prompt import RagPrompt

    for blank in ("", "   ", "\n\t"):
        p = RagPrompt(
            query="q", max_tokens=4000, model="gpt-4", query_instructions=blank
        )
        assert "user-provided instructions" not in p._prompt_text


# ---------------------------------------------------------------------------
# SearchRag._extract_result
# ---------------------------------------------------------------------------

def test_extract_result_returns_body_and_additional_content():
    sr = _make_search_rag()
    json_result = {
        "body": ["rag answer text"],
        "additional_content": {"sources": [{"url": "https://example.com"}]},
    }
    body_text, additional_content = sr._extract_result(json_result)
    assert body_text == "rag answer text"
    assert additional_content == {"sources": [{"url": "https://example.com"}]}


def test_extract_result_missing_additional_content_returns_empty_dict():
    sr = _make_search_rag()
    json_result = {"body": ["just the body"]}
    body_text, additional_content = sr._extract_result(json_result)
    assert body_text == "just the body"
    assert additional_content == {}


def test_extract_result_body_as_scalar():
    sr = _make_search_rag()
    json_result = {"body": "scalar body", "additional_content": {"sources": []}}
    body_text, additional_content = sr._extract_result(json_result)
    assert body_text == "scalar body"
    assert additional_content == {"sources": []}


def test_extract_result_body_missing_returns_none():
    sr = _make_search_rag()
    body_text, additional_content = sr._extract_result({})
    assert body_text is None
    assert additional_content == {}


# ---------------------------------------------------------------------------
# DetailSearchRagSerializer
# ---------------------------------------------------------------------------

def test_serializer_accepts_message_and_additional_content():
    serializer = DetailSearchRagSerializer(data={
        "message": "answer",
        "additional_content": {"sources": [{"url": "https://example.com"}]},
    })
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["message"] == "answer"
    assert serializer.validated_data["additional_content"] == {
        "sources": [{"url": "https://example.com"}],
    }


def test_serializer_additional_content_defaults_to_empty_dict():
    serializer = DetailSearchRagSerializer(data={"message": "answer"})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["additional_content"] == {}


def test_serializer_allows_blank_message():
    serializer = DetailSearchRagSerializer(data={"message": ""})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["message"] == ""


def test_serializer_requires_message_key():
    serializer = DetailSearchRagSerializer(data={"additional_content": {}})
    assert not serializer.is_valid()
    assert "message" in serializer.errors
