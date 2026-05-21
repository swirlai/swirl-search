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


# ---------------------------------------------------------------------------
# SearchRag.get_rag_result — cache decision (regression for 4.5.0.5)
#
# 4.5.0.4 shipped a cache check that compared the stored Result's
# rag_query_items to the CURRENT request's rag_query_items via set equality.
# When the detail-search-rag URL omitted ?rag_items=…, self.rag_query_items
# was [] — and set(stored_non_empty) == set([]) is False, so the cache check
# treated every such fetch as a miss. RAGPostResultProcessor.__init__ then
# deleted the cached Result and regenerated, producing a different LLM
# completion. The user saw the auto-RAG summary appear, then swap to a
# different summary seconds later.
#
# These tests cover the corrected cache logic in
# swirl/views_helpers/search_rag.py:62-83. They monkeypatch Result.objects.get
# instead of touching the DB — the rag_processor branch (DB write +
# OpenAI call) is verified by test_search_rag_integration.py.
# ---------------------------------------------------------------------------

class _FakeResult:
    """Stand-in for a stored ChatGPT Result row."""

    def __init__(self, rag_query_items, body="cached rag body", additional_content=None):
        self.json_results = [{
            "rag_query_items": rag_query_items,
            "body": [body],
            "additional_content": additional_content or {},
        }]
        self.deleted = False

    def delete(self):
        self.deleted = True


def _patch_result_get(monkeypatch, fake):
    """Make Result.objects.get(...) return ``fake`` (or raise DoesNotExist if None)."""
    from swirl.models import Result

    def _fake_get(*args, **kwargs):
        if fake is None:
            raise Result.DoesNotExist
        return fake

    monkeypatch.setattr(Result.objects, "get", _fake_get)


def test_get_rag_result_serves_cache_when_request_omits_rag_items(monkeypatch):
    """REGRESSION 4.5.0.5: an empty self.rag_query_items must serve the
    stored Result rather than trigger a regenerate. This is the path
    Galaxy hits when DetailSearchRagView fetches the auto-RAG output."""
    cached = _FakeResult(rag_query_items=["item-a", "item-b"], body="auto-RAG body")
    _patch_result_get(monkeypatch, cached)

    sr = _make_search_rag()  # no rag_items in request
    body_text, additional_content = sr.get_rag_result()

    assert body_text == "auto-RAG body"
    assert additional_content == {}
    assert cached.deleted is False, (
        "Cached Result must not be deleted when the request omits rag_items"
    )


def test_get_rag_result_serves_cache_when_request_items_match_stored(monkeypatch):
    cached = _FakeResult(rag_query_items=["item-a", "item-b"])
    _patch_result_get(monkeypatch, cached)

    sr = _make_search_rag(rag_items="item-b,item-a")  # same set, different order
    body_text, _ = sr.get_rag_result()

    assert body_text == "cached rag body"
    assert cached.deleted is False


def test_get_rag_result_regenerates_when_request_items_differ_from_stored(monkeypatch):
    """When the caller explicitly requested DIFFERENT rag_items, the cache
    must miss. We don't exercise the RAGPostResultProcessor branch here
    (that's the integration test's job) — just confirm we fall through
    past the cache return."""
    cached = _FakeResult(rag_query_items=["item-a", "item-b"])
    _patch_result_get(monkeypatch, cached)

    # Short-circuit the processor branch so the test doesn't need an
    # AIProvider / OpenAI client. validate() returning False makes
    # get_rag_result fall through to the final "", {} return.
    monkeypatch.setattr(
        "swirl.views_helpers.search_rag.RAGPostResultProcessor",
        lambda **kwargs: type("StubProc", (), {"validate": lambda self: False})(),
    )

    sr = _make_search_rag(rag_items="item-c")  # disjoint set → cache miss
    body_text, additional_content = sr.get_rag_result()

    # Cache-miss path returned the empty fall-through, which is what we want
    # to assert: the cache check did NOT return early with the stored body.
    assert body_text == ""
    assert additional_content == {}
