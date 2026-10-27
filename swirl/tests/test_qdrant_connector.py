"""
QdrantDB connector: the client call and the response mapping.

qdrant-client removed ``QdrantClient.search`` after 1.15; the connector uses
``query_points`` (present since 1.10), which returns a QueryResponse whose
``.points`` carry id / score / payload. These tests stub the client, so they
pin the call shape and the mapping without a Qdrant server.
"""
from types import SimpleNamespace

import pytest

from swirl.connectors import qdrant as qdrant_module


class _Point:
    def __init__(self, id, score, payload):
        self.id, self.score, self.payload = id, score, payload


class _FakeClient:
    """Has query_points and deliberately NO search(), like qdrant-client 1.16+."""
    instances = []

    def __init__(self, url, api_key):
        self.url, self.api_key = url, api_key
        self.calls = []
        _FakeClient.instances.append(self)

    def query_points(self, collection_name, **kwargs):
        self.calls.append((collection_name, kwargs))
        return SimpleNamespace(points=[
            _Point("a1", 0.91, {"title": "first", "url": "https://x/1"}),
            _Point(7, 0.42, {"title": "second", "url": "https://x/2"}),
        ])


def _connector(monkeypatch, vector):
    monkeypatch.setattr(qdrant_module, "QdrantClient", _FakeClient)
    _FakeClient.instances.clear()
    c = qdrant_module.QdrantDB.__new__(qdrant_module.QdrantDB)
    c.provider = SimpleNamespace(
        credentials="key-123", url="http://qdrant:6333-docs", results_per_query=5, name="Qdrant test",
    )
    c.search_id, c.provider_id = 1, 5          # for Connector.__str__ in log lines
    c.vector_to_provider = vector
    c.query_string_to_provider = "q"
    c.status = "PENDING"
    c.found = c.retrieved = 0
    c.response = None
    c.log = []
    c.error = lambda msg: c.log.append(("error", msg))
    c.message = lambda msg: c.log.append(("message", msg))
    return c


def test_execute_search_uses_query_points_and_maps_points(monkeypatch):
    c = _connector(monkeypatch, [0.1, 0.2, 0.3])

    c.execute_search()

    client = _FakeClient.instances[0]
    assert (client.url, client.api_key) == ("http://qdrant:6333", "key-123")
    collection, kwargs = client.calls[0]
    assert collection == "docs"
    assert kwargs == {"query": [0.1, 0.2, 0.3], "limit": 5, "with_payload": True, "with_vectors": False}

    assert c.found == 2 and c.retrieved == 2
    assert c.response == [
        {"title": "first", "url": "https://x/1", "id": "a1", "similarity": 0.91},
        {"title": "second", "url": "https://x/2", "id": "7", "similarity": 0.42},
    ]
    assert c.log == []


def test_execute_search_without_vector_errors_out(monkeypatch):
    c = _connector(monkeypatch, None)

    c.execute_search()

    assert c.status == "ERR"
    assert _FakeClient.instances == []
    assert c.log and c.log[0][0] == "error"


def test_execute_search_client_failure_is_reported(monkeypatch):
    c = _connector(monkeypatch, [0.5])

    def boom(self, *a, **k):
        raise RuntimeError("connection refused")
    monkeypatch.setattr(_FakeClient, "query_points", boom)

    c.execute_search()

    assert c.status == "ERR"
    assert "connection refused" in c.log[0][1]
