"""
Unit tests for swirl/tantivy_index/schema.py and tuning.py (WP01).

Design: TECH_DESIGN_swirl_for_backstage.md section 3.1. The gate-zero relevance
assertions live in test_tantivy_search_relevance.py; this file covers the
schema round trip, the analyzers, the attrs rule, the document contract and the
tuning file.

Run with: pytest swirl/tests/test_tantivy_schema.py -v
"""

import json
import os

import pytest

tantivy = pytest.importorskip("tantivy", reason="tantivy is not installed")

from swirl.tantivy_index import schema as schema_module          # noqa: E402
from swirl.tantivy_index.schema import (                          # noqa: E402
    ANALYZER_EXACT,
    ANALYZER_NGRAM,
    ANALYZER_TEXT,
    SEARCH_FIELDS,
    build_analyzers,
    build_schema,
    document_attrs,
    document_id,
    escape_term,
    open_index,
    validate_document,
)
from swirl.tantivy_index.tuning import (                          # noqa: E402
    DEFAULT_TUNING,
    Tuning,
    load_tuning,
    save_tuning,
    tuning_path,
)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def test_build_schema_round_trips_every_stored_field():
    index = open_index(None)
    writer = index.writer(15_000_000)
    writer.add_document(tantivy.Document(
        title_exact="tech-radar",
        title_ngram="tech-radar",
        text="Technology radar rendering the adoption rings.",
        attrs=["kind=component", "lifecycle=production"],
        doc_id="/catalog/default/component/tech-radar",
        type="software-catalog",
        title="tech-radar",
        location="/catalog/default/component/tech-radar",
        document_json=json.dumps({"title": "tech-radar", "owner": "team-a"}),
    ))
    writer.commit()
    writer.wait_merging_threads()
    index.reload()

    searcher = index.searcher()
    query = index.parse_query("radar", default_field_names=list(SEARCH_FIELDS))
    hits = searcher.search(query, 5).hits
    assert hits, "the round-tripped document was not found"
    stored = searcher.doc(hits[0][1])
    assert stored.get_first("title") == "tech-radar"
    assert stored.get_first("type") == "software-catalog"
    assert stored.get_first("location") == "/catalog/default/component/tech-radar"
    assert stored.get_first("doc_id") == "/catalog/default/component/tech-radar"
    assert json.loads(stored.get_first("document_json"))["owner"] == "team-a"


def test_search_fields_are_the_three_boosted_fields():
    assert SEARCH_FIELDS == ["title_exact", "title_ngram", "text"]
    assert set(DEFAULT_TUNING.field_boosts) == set(SEARCH_FIELDS)
    assert DEFAULT_TUNING.field_boosts["title_exact"] == 3.0


def test_document_json_is_stored_but_never_matches_a_word_query():
    """The recorded deviation: document_json is indexed with the raw tokenizer.

    A word inside the JSON must not make the document match a normal query.
    """
    index = open_index(None)
    writer = index.writer(15_000_000)
    writer.add_document(tantivy.Document(
        title_exact="alpha",
        title_ngram="alpha",
        text="",
        attrs=[],
        doc_id="alpha",
        type="t",
        title="alpha",
        location="/alpha",
        document_json=json.dumps({"title": "alpha", "secretword": "zebracrossing"}),
    ))
    writer.commit()
    writer.wait_merging_threads()
    index.reload()
    searcher = index.searcher()
    query = index.parse_query("zebracrossing", default_field_names=list(SEARCH_FIELDS))
    assert searcher.search(query, 5).hits == []


# ---------------------------------------------------------------------------
# Analyzers
# ---------------------------------------------------------------------------

def test_analyzers_are_named_as_the_schema_expects():
    analyzers = build_analyzers()
    assert set(analyzers) == {ANALYZER_EXACT, ANALYZER_NGRAM, ANALYZER_TEXT}


def test_exact_analyzer_stems_and_folds():
    exact = build_analyzers()[ANALYZER_EXACT]
    assert exact.analyze("Services") == ["servic"]
    assert exact.analyze("Café") == ["cafe"]


def test_ngram_analyzer_produces_infix_grams():
    grams = build_analyzers()[ANALYZER_NGRAM].analyze("petstore")
    assert "store" in grams
    assert "etst" in grams


def test_ngram_analyzer_honours_the_minimum():
    """The default minimum is 4 since fix pass 2; see Tuning's docstring."""
    grams = build_analyzers()[ANALYZER_NGRAM].analyze("petstore")
    assert "pet" not in grams
    assert min(len(gram) for gram in grams) == Tuning().ngram_min


def test_ngram_analyzer_still_follows_a_lowered_minimum():
    """The operator knob still works: ngram.min 3 restores the old grams."""
    grams = build_analyzers(Tuning(ngram_min=3))[ANALYZER_NGRAM].analyze("petstore")
    assert "pet" in grams


def test_text_analyzer_drops_stopwords():
    tokens = build_analyzers()[ANALYZER_TEXT].analyze("Search of the wayback machine")
    assert "the" not in tokens
    assert "of" not in tokens
    assert "wayback" in tokens


def test_extra_stopwords_are_applied():
    tuning = Tuning(extra_stopwords=["wayback"])
    tokens = build_analyzers(tuning)[ANALYZER_TEXT].analyze("the wayback machine")
    assert "wayback" not in tokens
    assert "machin" in tokens


def test_ngram_bounds_come_from_tuning():
    grams = build_analyzers(Tuning(ngram_min=4, ngram_max=4))[ANALYZER_NGRAM].analyze(
        "petstore")
    assert all(len(gram) == 4 for gram in grams)


# ---------------------------------------------------------------------------
# attrs
# ---------------------------------------------------------------------------

def test_attrs_are_lowercased_key_equals_value_for_every_scalar():
    document = {
        "title": "Petstore",
        "text": "The Petstore API",
        "location": "/catalog/default/api/petstore",
        "Kind": "API",
        "namespace": "Default",
        "lifecycle": "Production",
        "owner": "Team-C",
        "componentType": "openapi",
    }
    assert document_attrs(document) == [
        "componenttype=openapi",
        "kind=api",
        "lifecycle=production",
        "namespace=default",
        "owner=team-c",
    ]


def test_attrs_exclude_the_contract_fields():
    attrs = document_attrs({
        "title": "a", "text": "b", "location": "/c", "kind": "Component"})
    assert attrs == ["kind=component"]


def test_attrs_cover_numbers_and_booleans_and_skip_containers():
    attrs = document_attrs({
        "title": "a", "text": "b", "location": "/c",
        "rank": 3, "score": 1.5, "archived": False,
        "tags": ["one", "two"],
        "authorization": {"resourceRef": "component:default/x"},
        "empty": "", "missing": None,
    })
    assert "rank=3" in attrs
    assert "score=1.5" in attrs
    assert "archived=false" in attrs
    assert not any(token.startswith("tags=") for token in attrs)
    assert not any(token.startswith("authorization=") for token in attrs)
    assert not any(token.startswith("empty=") for token in attrs)
    assert not any(token.startswith("missing=") for token in attrs)


def test_attrs_filter_selects_only_matching_documents():
    index = open_index(None)
    writer = index.writer(15_000_000)
    for name, lifecycle in (("alpha", "production"), ("beta", "experimental")):
        writer.add_document(tantivy.Document(
            title_exact=name, title_ngram=name, text="a shared service",
            attrs=document_attrs({
                "title": name, "text": "", "location": "/" + name,
                "kind": "Component", "lifecycle": lifecycle}),
            doc_id="/" + name, type="software-catalog", title=name,
            location="/" + name, document_json=json.dumps({"title": name}),
        ))
    writer.commit()
    writer.wait_merging_threads()
    index.reload()

    searcher = index.searcher()
    parsed = index.parse_query("service", default_field_names=list(SEARCH_FIELDS))
    filtered = tantivy.Query.boolean_query([
        (tantivy.Occur.Must, parsed),
        (tantivy.Occur.Must, tantivy.Query.term_query(
            index.schema, "attrs", "lifecycle=production", "basic")),
    ])
    titles = [searcher.doc(address).get_first("title")
              for _score, address in searcher.search(filtered, 10).hits]
    assert titles == ["alpha"]


# ---------------------------------------------------------------------------
# doc_id, document validation and query escaping
# ---------------------------------------------------------------------------

def test_document_id_prefers_location():
    assert document_id({"location": "/catalog/x"}) == "/catalog/x"


def test_document_id_falls_back_to_a_stable_sha256():
    document = {"title": "a", "text": "b"}
    first = document_id(document)
    assert len(first) == 64
    assert first == document_id({"text": "b", "title": "a"})
    assert first != document_id({"title": "a", "text": "c"})


@pytest.mark.parametrize("bad,fragment", [
    ({"text": "t", "location": "/l"}, 'missing the required field "title"'),
    ({"title": "t", "location": "/l"}, 'missing the required field "text"'),
    ({"title": "t", "text": "t"}, 'missing the required field "location"'),
    ({"title": 7, "text": "t", "location": "/l"}, 'non string "title"'),
    ({"title": " ", "text": "t", "location": "/l"}, 'empty "title"'),
    ({"title": "t", "text": "t", "location": "  "}, 'empty "location"'),
    ("not an object", "is not an object"),
])
def test_validate_document_rejects_bad_documents(bad, fragment):
    with pytest.raises(ValueError) as excinfo:
        validate_document(bad, position=4)
    assert fragment in str(excinfo.value)
    assert "index 4" in str(excinfo.value)


def test_validate_document_accepts_an_empty_text():
    document = {"title": "t", "text": "", "location": "/l"}
    assert validate_document(document) is document


def test_escape_term_escapes_the_parser_metacharacters():
    assert escape_term("foo-bar.com") == "foo\\-bar.com"
    assert escape_term('a:b"c') == 'a\\:b\\"c'
    assert escape_term("") == ""
    assert escape_term(None) == ""


# ---------------------------------------------------------------------------
# Tuning
# ---------------------------------------------------------------------------

def test_tuning_defaults_match_the_design():
    tuning = Tuning()
    assert tuning.title_exact_boost == 3.0
    assert tuning.ngram_min == 4
    assert tuning.ngram_max == 8
    assert tuning.stemmer == "english"
    assert tuning.fuzzy_enabled is False
    assert tuning.fuzzy_distance == 1


def test_tuning_from_dict_rejects_unknown_keys():
    """Contract change: unknown keys used to be dropped in silence, which is
    how the whole documented Backstage tuning block could be configured and do
    nothing at all. They are now named in the error the endpoint returns.
    """
    with pytest.raises(ValueError) as err:
        Tuning.from_dict({"text_boost": 2, "nonsense": True})
    assert "nonsense" in str(err.value)
    assert "text_boost" not in str(err.value).split("Known keys")[0]


def test_tuning_from_dict_accepts_the_nested_backstage_shape():
    """The block the engine module sends verbatim out of app-config."""
    tuning = Tuning.from_dict({
        "fieldBoosts": {"titleExact": 5, "titleNgram": 2, "text": 1.5},
        "ngram": {"min": 2, "max": 6},
        "stemmer": "porter",
        "stopwords": ["Platform"],
        "fuzzy": {"enabled": True, "distance": 2},
        "bm25": {"k1": 1.4, "b": 0.5},
        "highlight": {"enabled": False, "maxChars": 150},
    })
    assert tuning.title_exact_boost == 5.0
    assert tuning.title_ngram_boost == 2.0
    assert tuning.text_boost == 1.5
    assert tuning.ngram_min == 2
    assert tuning.ngram_max == 6
    assert tuning.stemmer == "porter"
    assert tuning.extra_stopwords == ["platform"]
    assert tuning.fuzzy_enabled is True
    assert tuning.fuzzy_distance == 2
    assert tuning.bm25_k1 == 1.4
    assert tuning.bm25_b == 0.5
    assert tuning.highlight is False
    assert tuning.snippet_chars == 150


def test_tuning_from_dict_still_accepts_the_flat_swirl_shape():
    tuning = Tuning.from_dict({"fuzzy_enabled": True, "ngram_min": 4,
                               "snippet_chars": 111})
    assert tuning.fuzzy_enabled is True
    assert tuning.ngram_min == 4
    assert tuning.snippet_chars == 111


def test_tuning_from_dict_accepts_both_shapes_in_one_call():
    tuning = Tuning.from_dict({"text_boost": 2, "fuzzy": {"enabled": True}})
    assert tuning.text_boost == 2.0
    assert tuning.fuzzy_enabled is True


def test_highlight_is_a_bool_flat_and_an_object_nested():
    """`highlight` is a SWIRL bool and a Backstage block; both have to work."""
    assert Tuning.from_dict({"highlight": False}).highlight is False
    assert Tuning.from_dict({"highlight": {"enabled": False}}).highlight is False


def test_normalize_reports_the_keys_it_took_and_the_ones_it_did_not():
    from swirl.tantivy_index.tuning import normalize

    flat, accepted, unknown = normalize(
        {"text_boost": 2, "fuzzy": {"enabled": True, "bogus": 1}, "nope": 1})
    assert flat == {"text_boost": 2.0, "fuzzy_enabled": True}
    assert accepted == ["text_boost", "fuzzy.enabled"]
    assert unknown == ["fuzzy.bogus", "nope"]


def test_bm25_is_not_applied_by_this_tantivy():
    """If a later tantivy-py binds BM25, this is the test that says so."""
    from swirl.tantivy_index.tuning import bm25_supported

    assert bm25_supported() is False


@pytest.mark.parametrize("payload", [
    {"ngram_min": 0},
    {"ngram_min": 5, "ngram_max": 4},
    {"ngram_max": 99},
    {"fuzzy_distance": 3},
    {"remove_long": 2},
    {"text_boost": -1},
    {"stemmer": ""},
    {"fuzzy_enabled": "yes"},
    {"ngram_min": "three"},
    {"extra_stopwords": "the"},
    {"extra_stopwords": [1, 2]},
    {"bm25": {"k1": -1}},
    {"bm25": {"b": 2}},
    {"ngram": 5},
    {"fieldBoosts": "high"},
])
def test_tuning_from_dict_rejects_bad_values(payload):
    with pytest.raises(ValueError):
        Tuning.from_dict(payload)


def test_tuning_round_trips_through_the_data_dir(tmp_path):
    data_dir = str(tmp_path / "tantivy")
    assert load_tuning(data_dir).to_dict() == Tuning().to_dict()
    saved = save_tuning(data_dir, Tuning(text_boost=2.5, extra_stopwords=["Foo"]))
    assert os.path.exists(tuning_path(data_dir))
    reloaded = load_tuning(data_dir)
    assert reloaded.text_boost == 2.5
    assert reloaded.extra_stopwords == ["foo"]
    assert reloaded.to_dict() == saved.to_dict()


def test_load_tuning_falls_back_when_the_file_is_corrupt(tmp_path):
    data_dir = str(tmp_path / "tantivy")
    os.makedirs(data_dir)
    with open(tuning_path(data_dir), "w", encoding="utf-8") as handle:
        handle.write("{not json")
    assert load_tuning(data_dir).to_dict() == Tuning().to_dict()


def test_schema_module_imports_no_django():
    """The gauntlet imports this module standalone, so keep it Django free."""
    source = open(schema_module.__file__, encoding="utf-8").read()
    assert "import django" not in source
    assert "from django" not in source
