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
