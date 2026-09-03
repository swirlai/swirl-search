"""
WP00 gate zero relevance assertions, run in process.

This test imports the schema builder and the gauntlet cases from
``DevUtils/backstage-gauntlet.py`` and replays them against an in-memory
fixture that mirrors the Backstage example catalog, so the gate-zero result is
protected by the normal test suite and does not depend on a checkout of
``backstage`` being present.

The whole module is skipped when tantivy is not importable.
"""

import importlib.util
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GAUNTLET_PATH = os.path.join(REPO_ROOT, "DevUtils", "backstage-gauntlet.py")

tantivy = pytest.importorskip("tantivy", reason="tantivy is not installed")


def _load_gauntlet():
    """Load the hyphenated script as a module."""
    spec = importlib.util.spec_from_file_location(
        "swirl_backstage_gauntlet", GAUNTLET_PATH
    )
    module = importlib.util.module_from_spec(spec)
    # dataclasses needs the module registered before the class bodies execute.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gauntlet = _load_gauntlet()

pytestmark = pytest.mark.skipif(
    not gauntlet.TANTIVY_AVAILABLE, reason="tantivy is not installed"
)


# ---------------------------------------------------------------------------
# In-memory fixture: a faithful subset of the Backstage example catalog
# (packages/catalog-model/examples), in the raw entity shape the collator sees.
# ---------------------------------------------------------------------------

EXAMPLE_ENTITIES = [
    {
        "kind": "Component",
        "metadata": {"name": "petstore", "description":
                     "The Petstore is an example API used to show features of "
                     "the OpenAPI spec."},
        "spec": {"type": "service", "lifecycle": "experimental", "owner": "team-c"},
    },
    {
        "kind": "API",
        "metadata": {"name": "petstore", "description": "The Petstore API"},
        "spec": {"type": "openapi", "lifecycle": "experimental", "owner": "team-c"},
    },
    {
        "kind": "API",
        "metadata": {"name": "petstore-webhook",
                     "description": "The Petstore webhook API"},
        "spec": {"type": "asyncapi", "lifecycle": "experimental", "owner": "team-c"},
    },
    {
        "kind": "Component",
        "metadata": {"name": "wayback-search",
                     "description": "Search of the wayback machine"},
        "spec": {"type": "service", "lifecycle": "production", "owner": "team-a"},
    },
    {
        "kind": "API",
        "metadata": {"name": "wayback-search",
                     "description": "Search API of the wayback machine"},
        "spec": {"type": "openapi", "lifecycle": "production", "owner": "team-a"},
    },
    {
        "kind": "Component",
        "metadata": {"name": "wayback-archive",
                     "description": "Archive of the wayback machine"},
        "spec": {"type": "service", "lifecycle": "production", "owner": "team-b"},
    },
    {
        "kind": "Component",
        "metadata": {"name": "wayback-archive-storage",
                     "description": "Storage of the wayback machine archive"},
        "spec": {"type": "service", "lifecycle": "experimental", "owner": "team-b"},
    },
    {
        "kind": "Component",
        "metadata": {"name": "wayback-archive-ingestion",
                     "description": "Ingestion of the wayback machine archive"},
        "spec": {"type": "service", "lifecycle": "experimental", "owner": "team-b"},
    },
    {
        "kind": "Component",
        "metadata": {"name": "searcher",
                     "description": "Searches the artist database"},
        "spec": {"type": "service", "lifecycle": "experimental", "owner": "team-a"},
    },
    {
        "kind": "Component",
        "metadata": {"name": "www-artist",
                     "description": "Artist website used by the web front end"},
        "spec": {"type": "website", "lifecycle": "experimental", "owner": "team-a"},
    },
    {
        "kind": "Resource",
        "metadata": {"name": "artists-db",
                     "description": "Stores artist details"},
        "spec": {"type": "database", "lifecycle": "experimental", "owner": "team-a"},
    },
    {
        "kind": "Component",
        "metadata": {
            "name": "techdocs-entity-documented-component",
            "title": "Example Entity Documented By TechDocs Entity Annotation",
            "description": "A Service with TechDocs documentation via the "
                           "backstage.io/techdocs-entity annotation.",
        },
        "spec": {"type": "service", "lifecycle": "experimental", "owner": "user:guest"},
    },
    {"kind": "Group", "metadata": {"name": "team-a", "description": "Team A"},
     "spec": {"type": "team"}},
    {"kind": "Group", "metadata": {"name": "team-b", "description": "Team B"},
     "spec": {"type": "team"}},
    {"kind": "Group", "metadata": {"name": "team-c", "description": "Team C"},
     "spec": {"type": "team"}},
    {"kind": "Group", "metadata": {"name": "team-d", "description": "Team D"},
     "spec": {"type": "team"}},
]

#: How many synthetic entities the fixture adds so that every gauntlet case is
#: applicable. Small enough that the test stays fast.
SYNTHETIC_COUNT = 300


@pytest.fixture(scope="module")
def corpus():
    documents = [
        gauntlet.entity_to_document(entity) for entity in EXAMPLE_ENTITIES
    ]
    documents = [document for document in documents if document]
    documents.extend(gauntlet.generate_synthetic(SYNTHETIC_COUNT))
    return documents


@pytest.fixture(scope="module")
def index(corpus, tmp_path_factory):
    path = str(tmp_path_factory.mktemp("tantivy-gauntlet"))
    return gauntlet.build_corpus_index(corpus, path)


# ---------------------------------------------------------------------------
# Schema and analyzers
# ---------------------------------------------------------------------------


def test_schema_has_the_design_fields():
    schema = gauntlet.build_schema()
    assert schema is not None
    # The schema is opaque from Python, so assert through a round trip instead.
    index = gauntlet.open_index(None)
    gauntlet.index_documents(
        index,
        [
            {
                "title": "tech-radar",
                "text": "Technology radar",
                "location": "/catalog/default/component/tech-radar",
                "type": gauntlet.BACKSTAGE_DOC_TYPE,
                "kind": "Component",
                "namespace": "default",
                "lifecycle": "production",
                "owner": "team-a",
                "componentType": "service",
            }
        ],
    )
    hits = gauntlet.search(index, "tech-radar", limit=5)
    assert hits, "the round-tripped document was not found"
    hit = hits[0]
    assert hit["title"] == "tech-radar"
    assert hit["location"] == "/catalog/default/component/tech-radar"
    assert hit["type"] == gauntlet.BACKSTAGE_DOC_TYPE
    assert hit["document"]["owner"] == "team-a"


def test_stemmer_filter_is_active():
    analyzer = gauntlet.build_analyzers()["swirl_exact"]
    assert analyzer.analyze("Services") == ["servic"]
    assert analyzer.analyze("Archiving") == ["archiv"]


def test_ngram_tokenizer_produces_infix_grams():
    analyzer = gauntlet.build_analyzers()["swirl_ngram"]
    grams = analyzer.analyze("petstore")
    assert "store" in grams
    assert "pet" in grams


def test_text_analyzer_removes_stopwords():
    analyzer = gauntlet.build_analyzers()["swirl_text"]
    tokens = analyzer.analyze("Search of the wayback machine")
    assert "the" not in tokens
    assert "of" not in tokens
    assert "wayback" in tokens


def test_document_attrs_are_key_equals_value():
    document = {
        "kind": "Component",
        "namespace": "default",
        "lifecycle": "Production",
        "owner": "team-a",
        "componentType": "service",
    }
    assert gauntlet.document_attrs(document) == [
        "kind=component",
        "namespace=default",
        "lifecycle=production",
        "owner=team-a",
        "type=service",
    ]


def test_fuzzy_fields_are_honoured_by_parse_query(index):
    strict = gauntlet.search(index, "petsotre", limit=5, fuzzy=False)
    assert not any(hit["title"] == "petstore" for hit in strict)
    fuzzy = gauntlet.search(index, "petsotre", limit=5, fuzzy=True)
    assert any(hit["title"] == "petstore" for hit in fuzzy)


# ---------------------------------------------------------------------------
# The gauntlet itself
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case", gauntlet.GAUNTLET_CASES, ids=[c.name for c in gauntlet.GAUNTLET_CASES]
)
def test_gauntlet_case(index, corpus, case):
    rows = gauntlet.run_gauntlet(index, corpus, cases=[case])
    row = rows[0]
    assert row["status"] != "N/A", (
        "case {} is not applicable to the fixture: {}".format(case.name, row["detail"])
    )
    assert row["status"] == "PASS", "{}: {} (top 5: {})".format(
        case.name, row["detail"], [hit["title"] for hit in row["hits"]]
    )


def test_full_gauntlet_passes(index, corpus):
    rows = gauntlet.assert_gauntlet(index, corpus)
    assert len(rows) == len(gauntlet.GAUNTLET_CASES)
    assert all(row["status"] == "PASS" for row in rows)
