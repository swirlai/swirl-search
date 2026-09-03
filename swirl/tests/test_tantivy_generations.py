"""
Unit tests for swirl/tantivy_index/generations.py and manager.py (WP01).

Design: TECH_DESIGN_swirl_for_backstage.md section 3.1.

Covers begin, that finalize swaps LIVE atomically and prunes all but the
previous generation, that abort deletes only its own generation and leaves LIVE
alone, the stale-lock TTL, and that a second begin while one is open raises the
error the ingest view turns into HTTP 409.

Run with: pytest swirl/tests/test_tantivy_generations.py -v
"""

import json
import os
import time

import pytest

tantivy = pytest.importorskip("tantivy", reason="tantivy is not installed")

from swirl.tantivy_index import generations as gen        # noqa: E402
from swirl.tantivy_index.manager import TantivyIndexManager  # noqa: E402
from swirl.tantivy_index.tuning import Tuning             # noqa: E402


TYPE = "software-catalog"


def doc(name, **extra):
    payload = {
        "title": name,
        "text": "The {} component of the platform.".format(name),
        "location": "/catalog/default/component/{}".format(name),
        "kind": "Component",
    }
    payload.update(extra)
    return payload


@pytest.fixture
def data_dir(tmp_path):
    return str(tmp_path / "tantivy")


@pytest.fixture
def manager(data_dir):
    return TantivyIndexManager(data_dir=data_dir, writer_heap_mb=15, begin_ttl=3600)


# ---------------------------------------------------------------------------
# Type names
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "software-catalog", "a", "techdocs", "0-9", "x" * 64])
def test_valid_type_names(name):
    assert gen.validate_type_name(name) == name


@pytest.mark.parametrize("name", [
    "", "Software", "soft_ware", "soft.ware", "x" * 65, "../etc", "a/b", None, 7])
def test_invalid_type_names(name):
    with pytest.raises(gen.InvalidTypeName):
        gen.validate_type_name(name)


def test_generation_ids_sort_chronologically():
    first = gen.new_generation_id(1000.5)
    second = gen.new_generation_id(1001.5)
    assert gen.GENERATION_RE.match(first)
    assert first < second


# ---------------------------------------------------------------------------
# begin
# ---------------------------------------------------------------------------

def test_begin_creates_the_generation_directory_and_takes_the_lock(manager, data_dir):
    generation = manager.begin(TYPE, started_by="tester")
    assert os.path.isdir(gen.generation_dir(data_dir, TYPE, generation))
    record = gen.read_open(data_dir, TYPE)
    assert record["generation"] == generation
    assert record["started_by"] == "tester"
    assert manager.open_generation(TYPE) == generation
    assert gen.live_generation(data_dir, TYPE) is None


def test_second_begin_while_one_is_open_raises_generation_open(manager):
    first = manager.begin(TYPE)
    with pytest.raises(gen.GenerationOpen) as excinfo:
        manager.begin(TYPE)
    assert excinfo.value.generation == first
    assert excinfo.value.type_name == TYPE


def test_begin_for_a_different_type_is_allowed(manager):
    manager.begin(TYPE)
    assert manager.begin("techdocs")


def test_begin_takes_over_a_stale_lock(data_dir):
    manager = TantivyIndexManager(data_dir=data_dir, writer_heap_mb=15, begin_ttl=1)
    abandoned = manager.begin(TYPE)
    # Backdate the lock past the TTL rather than sleeping.
    path = gen.open_file(data_dir, TYPE)
    record = json.load(open(path, encoding="utf-8"))
    record["started_at"] = time.time() - 10
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(record, handle)

    fresh = manager.begin(TYPE)
    assert fresh != abandoned
    assert not os.path.isdir(gen.generation_dir(data_dir, TYPE, abandoned))
    assert manager.open_generation(TYPE) == fresh


def test_a_lock_inside_the_ttl_is_not_stale(data_dir):
    manager = TantivyIndexManager(data_dir=data_dir, writer_heap_mb=15, begin_ttl=3600)
    manager.begin(TYPE)
    with pytest.raises(gen.GenerationOpen):
        manager.begin(TYPE)


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

def test_add_writes_documents_and_counts_them(manager, data_dir):
    generation = manager.begin(TYPE)
    assert manager.add(TYPE, generation, [doc("alpha"), doc("beta")]) == 2
    assert manager.add(TYPE, generation, [doc("gamma")]) == 1
    path = gen.generation_dir(data_dir, TYPE, generation)
    assert manager._read_count(path) == 3


def test_add_rejects_a_bad_document_with_its_index_and_writes_nothing(manager, data_dir):
    generation = manager.begin(TYPE)
    with pytest.raises(ValueError) as excinfo:
        manager.add(TYPE, generation, [doc("alpha"), {"title": "no text or location"}])
    assert "index 1" in str(excinfo.value)
    path = gen.generation_dir(data_dir, TYPE, generation)
    assert manager._read_count(path) == 0


def test_add_rejects_an_oversized_batch(manager):
    generation = manager.begin(TYPE)
    with pytest.raises(ValueError) as excinfo:
        manager.add(TYPE, generation, [doc("d{}".format(i)) for i in range(1001)])
    assert "1000" in str(excinfo.value)


def test_add_to_a_generation_that_is_not_open_is_rejected(manager):
    generation = manager.begin(TYPE)
    manager.add(TYPE, generation, [doc("alpha")])
    manager.finalize(TYPE, generation)
    with pytest.raises(gen.GenerationNotFound):
        manager.add(TYPE, generation, [doc("beta")])


def test_add_to_an_unknown_generation_is_rejected(manager):
    manager.begin(TYPE)
    with pytest.raises(gen.GenerationNotFound):
        manager.add(TYPE, "20200101T000000-000000", [doc("alpha")])


# ---------------------------------------------------------------------------
# finalize
# ---------------------------------------------------------------------------

def test_finalize_swaps_live_and_releases_the_lock(manager, data_dir):
    generation = manager.begin(TYPE)
    manager.add(TYPE, generation, [doc("alpha")])
    result = manager.finalize(TYPE, generation)
    assert result["live"] == generation
    assert result["count"] == 1
    assert result["bytes"] > 0
    assert gen.live_generation(data_dir, TYPE) == generation
    assert manager.open_generation(TYPE) is None


def test_finalize_of_zero_documents_is_refused_and_keeps_the_live_generation(
        manager, data_dir):
    first = manager.begin(TYPE)
    manager.add(TYPE, first, [doc("alpha")])
    manager.finalize(TYPE, first)

    second = manager.begin(TYPE)
    with pytest.raises(gen.NoDocuments):
        manager.finalize(TYPE, second)
    assert gen.live_generation(data_dir, TYPE) == first
    # The generation stays open so the caller can add documents or abort.
    assert manager.open_generation(TYPE) == second


def test_finalize_keeps_the_previous_generation_and_prunes_the_rest(manager, data_dir):
    kept = []
    for name in ("one", "two", "three"):
        generation = manager.begin(TYPE)
        manager.add(TYPE, generation, [doc(name)])
        manager.finalize(TYPE, generation)
        kept.append(generation)
    on_disk = gen.generations(data_dir, TYPE)
    assert on_disk == sorted(kept[-2:])
    assert gen.live_generation(data_dir, TYPE) == kept[-1]


def test_live_file_swap_is_atomic(manager, data_dir):
    """LIVE is replaced by rename, so it never contains a partial name."""
    first = manager.begin(TYPE)
    manager.add(TYPE, first, [doc("alpha")])
    manager.finalize(TYPE, first)
    inode_before = os.stat(gen.live_file(data_dir, TYPE)).st_ino

    second = manager.begin(TYPE)
    manager.add(TYPE, second, [doc("beta")])
    manager.finalize(TYPE, second)
    live_file = gen.live_file(data_dir, TYPE)
    assert os.stat(live_file).st_ino != inode_before, "LIVE was written in place"
    assert open(live_file, encoding="utf-8").read().strip() == second
    # No temp files left behind.
    leftovers = [name for name in os.listdir(gen.type_dir(data_dir, TYPE))
                 if name.startswith(".tmp-")]
    assert leftovers == []


# ---------------------------------------------------------------------------
# abort and delete
# ---------------------------------------------------------------------------

def test_abort_deletes_the_generation_and_keeps_live(manager, data_dir):
    first = manager.begin(TYPE)
    manager.add(TYPE, first, [doc("alpha")])
    manager.finalize(TYPE, first)

    second = manager.begin(TYPE)
    manager.add(TYPE, second, [doc("beta")])
    manager.abort(TYPE, second)

    assert not os.path.isdir(gen.generation_dir(data_dir, TYPE, second))
    assert gen.live_generation(data_dir, TYPE) == first
    assert manager.open_generation(TYPE) is None
    # The lock is released, so a new begin succeeds.
    assert manager.begin(TYPE)


def test_abort_refuses_the_live_generation(manager):
    generation = manager.begin(TYPE)
    manager.add(TYPE, generation, [doc("alpha")])
    manager.finalize(TYPE, generation)
    with pytest.raises(gen.TantivyIndexError):
        manager.abort(TYPE, generation)


def test_abort_of_an_unknown_generation_raises(manager):
    manager.begin(TYPE)
    with pytest.raises(gen.GenerationNotFound):
        manager.abort(TYPE, "20200101T000000-000000")


def test_delete_removes_the_type_entirely(manager, data_dir):
    generation = manager.begin(TYPE)
    manager.add(TYPE, generation, [doc("alpha")])
    manager.finalize(TYPE, generation)
    assert manager.delete(TYPE) is True
    assert not os.path.exists(gen.type_dir(data_dir, TYPE))
    assert manager.types() == []
    assert manager.delete(TYPE) is False


# ---------------------------------------------------------------------------
# search and stats
# ---------------------------------------------------------------------------

@pytest.fixture
def loaded(manager):
    generation = manager.begin(TYPE)
    manager.add(TYPE, generation, [
        doc("petstore", lifecycle="production", owner="team-c"),
        doc("petstore-webhook", lifecycle="experimental", owner="team-c"),
        doc("wayback-search", lifecycle="production", owner="team-a"),
    ])
    manager.finalize(TYPE, generation)
    return manager


def test_search_returns_scored_hits(loaded):
    hits = loaded.search(types=[TYPE], term="petstore", limit=5)
    assert hits
    assert hits[0]["title"] == "petstore"
    assert hits[0]["score"] > 0
    assert hits[0]["location"] == "/catalog/default/component/petstore"
    assert hits[0]["type"] == TYPE
    assert hits[0]["document"]["owner"] == "team-c"
    assert hits == sorted(hits, key=lambda hit: hit["score"], reverse=True)


def test_search_over_all_live_types_when_none_are_named(loaded):
    assert loaded.types() == [TYPE]
    assert loaded.search(term="petstore", limit=5)


def test_search_honours_attrs_filters(loaded):
    hits = loaded.search(types=[TYPE], term="component",
                         filters={"lifecycle": "production"}, limit=10)
    assert hits
    assert all(hit["document"]["lifecycle"] == "production" for hit in hits)
    titles = sorted(hit["title"] for hit in hits)
    assert titles == ["petstore", "wayback-search"]


def test_search_honours_a_multi_valued_filter(loaded):
    hits = loaded.search(types=[TYPE], term="component",
                         filters={"owner": ["team-a", "team-c"]}, limit=10)
    assert len(hits) == 3


def test_search_filter_with_no_match_returns_nothing(loaded):
    assert loaded.search(types=[TYPE], term="component",
                         filters={"lifecycle": "retired"}, limit=10) == []


def test_search_paginates_with_offset(loaded):
    page_one = loaded.search(types=[TYPE], term="component", limit=1, offset=0)
    page_two = loaded.search(types=[TYPE], term="component", limit=1, offset=1)
    assert len(page_one) == 1 and len(page_two) == 1
    assert page_one[0]["doc_id"] != page_two[0]["doc_id"]


def test_search_is_fuzzy_only_when_asked(loaded):
    assert not loaded.search(types=[TYPE], term="petsotre", limit=5, fuzzy=False)
    fuzzy = loaded.search(types=[TYPE], term="petsotre", limit=5, fuzzy=True)
    assert any(hit["title"] == "petstore" for hit in fuzzy)


def test_search_of_an_unknown_type_is_empty_not_an_error(loaded):
    assert loaded.search(types=["no-such-type"], term="petstore") == []


def test_search_of_a_bad_type_name_is_skipped(loaded):
    assert loaded.search(types=["Not Valid"], term="petstore") == []


def test_search_merges_hits_across_types(manager):
    for type_name, title in (("software-catalog", "alpha-service"),
                             ("techdocs", "alpha-guide")):
        generation = manager.begin(type_name)
        manager.add(type_name, generation, [doc(title)])
        manager.finalize(type_name, generation)
    hits = manager.search(types=["software-catalog", "techdocs"], term="alpha", limit=10)
    assert sorted(hit["type"] for hit in hits) == ["software-catalog", "techdocs"]


def test_search_sees_a_new_generation_after_finalize(loaded, data_dir):
    assert not loaded.search(types=[TYPE], term="zebracrossing")
    generation = loaded.begin(TYPE)
    loaded.add(TYPE, generation, [doc("zebracrossing")])
    loaded.finalize(TYPE, generation)
    hits = loaded.search(types=[TYPE], term="zebracrossing")
    assert [hit["title"] for hit in hits] == ["zebracrossing"]
    # The old documents are gone: a generation is a full replacement.
    assert not loaded.search(types=[TYPE], term="petstore")


def test_stats_report_the_live_generation(loaded, data_dir):
    stats = loaded.stats(TYPE)
    assert stats["type"] == TYPE
    assert stats["live"] == gen.live_generation(data_dir, TYPE)
    assert stats["doc_count"] == 3
    assert stats["bytes"] > 0
    assert stats["updated"] is not None
    assert stats["open"] is None


def test_stats_of_an_unknown_type_are_empty(manager):
    stats = manager.stats("nothing-here")
    assert stats["live"] is None
    assert stats["doc_count"] == 0
    assert stats["bytes"] == 0


def test_all_stats_lists_every_type_directory(loaded):
    loaded.begin("techdocs")
    rows = {row["type"]: row for row in loaded.all_stats()}
    assert set(rows) == {TYPE, "techdocs"}
    assert rows["techdocs"]["live"] is None
    assert rows["techdocs"]["open"] is not None


def test_types_lists_only_types_with_a_live_generation(manager):
    manager.begin(TYPE)
    assert manager.types() == []


# ---------------------------------------------------------------------------
# Tuning through the manager
# ---------------------------------------------------------------------------

def test_configure_persists_a_partial_tuning_block(manager):
    effective = manager.configure({"text_boost": 2.0})
    assert effective.text_boost == 2.0
    assert effective.title_exact_boost == 3.0
    assert manager.tuning().text_boost == 2.0


def test_configure_rejects_a_bad_tuning_block(manager):
    with pytest.raises(ValueError):
        manager.configure({"ngram_max": 1, "ngram_min": 4})


def test_tuning_is_applied_on_the_next_begin(manager):
    manager.configure({"extra_stopwords": ["platform"]})
    generation = manager.begin(TYPE)
    manager.add(TYPE, generation, [doc("alpha")])
    manager.finalize(TYPE, generation)
    # "platform" appears in every document body but is now a stopword.
    assert manager.search(types=[TYPE], term="platform") == []
    assert manager.search(types=[TYPE], term="alpha")


def test_manager_reads_settings_when_no_data_dir_is_given(settings, tmp_path):
    settings.SWIRL_TANTIVY_DATA_DIR = str(tmp_path / "from-settings")
    settings.SWIRL_TANTIVY_WRITER_HEAP_MB = 17
    settings.SWIRL_TANTIVY_BEGIN_TTL = 42
    manager = TantivyIndexManager()
    assert manager.data_dir == str(tmp_path / "from-settings")
    assert manager.writer_heap_bytes == 17 * 1024 * 1024
    assert manager.begin_ttl == 42


# ---------------------------------------------------------------------------
# Concurrent begin
#
# Defect: begin read the OPEN lock, then created the generation directory, then
# wrote the lock. Two callers in that window both came away believing they
# owned a generation. The lock is now taken with an exclusive create before
# anything else exists, so exactly one caller can win.
# ---------------------------------------------------------------------------

def test_only_one_of_two_simultaneous_begins_wins(data_dir):
    import threading

    barrier = threading.Barrier(2)
    outcomes = []

    def call():
        barrier.wait(timeout=30)
        try:
            outcomes.append(("open", gen.begin(data_dir, TYPE)))
        except gen.GenerationOpen as err:
            outcomes.append(("conflict", err.generation))
        except Exception as err:                     # noqa: BLE001
            outcomes.append(("raised", repr(err)))

    threads = [threading.Thread(target=call) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
        assert not thread.is_alive()

    kinds = sorted(kind for kind, _ in outcomes)
    assert kinds == ["conflict", "open"], outcomes

    winner = [value for kind, value in outcomes if kind == "open"][0]
    # The loser created nothing: one directory, and it is the winner's.
    assert gen.generations(data_dir, TYPE) == [winner]
    assert gen.open_generation(data_dir, TYPE) == winner
    # And the loser was told which generation holds the lock, not a phantom.
    assert [value for kind, value in outcomes if kind == "conflict"] == [winner]


def test_take_open_lock_is_exclusive(data_dir):
    os.makedirs(gen.type_dir(data_dir, TYPE), exist_ok=True)
    assert gen.take_open_lock(data_dir, TYPE, "20260101T000000-000000") is True
    assert gen.take_open_lock(data_dir, TYPE, "20260101T000001-000000") is False
    assert gen.read_open(data_dir, TYPE)["generation"] == "20260101T000000-000000"


# ---------------------------------------------------------------------------
# Rolling a half-done begin back
# ---------------------------------------------------------------------------

def test_rollback_releases_the_lock_and_the_directory(manager, data_dir):
    generation = manager.begin(TYPE)
    assert generation in gen.generations(data_dir, TYPE)

    assert manager.rollback_begin(TYPE, generation) is True

    assert gen.read_open(data_dir, TYPE) is None
    assert gen.generations(data_dir, TYPE) == []
    # The type is not wedged.
    assert manager.begin(TYPE) != generation


def test_rollback_never_touches_the_live_generation(manager, data_dir):
    live = manager.begin(TYPE)
    manager.add(TYPE, live, [doc("petstore")])
    manager.finalize(TYPE, live)

    manager.rollback_begin(TYPE, live)

    assert gen.live_generation(data_dir, TYPE) == live
    assert live in gen.generations(data_dir, TYPE)


def test_rollback_does_not_release_a_lock_someone_else_took(manager, data_dir):
    mine = manager.begin(TYPE)
    manager.rollback_begin(TYPE, mine)
    theirs = manager.begin(TYPE)

    # A late rollback for the generation that is long gone must not unlock the
    # one that replaced it.
    assert manager.rollback_begin(TYPE, mine) is False
    assert gen.open_generation(data_dir, TYPE) == theirs


# ---------------------------------------------------------------------------
# Clearing a stale lock
# ---------------------------------------------------------------------------

def _age_lock(data_dir, type_name, seconds):
    path = gen.open_file(data_dir, type_name)
    with open(path, "r", encoding="utf-8") as handle:
        record = json.load(handle)
    record["started_at"] = time.time() - seconds
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(record, handle)


def test_clear_stale_open_leaves_a_live_lock_alone(manager, data_dir):
    generation = manager.begin(TYPE)
    assert manager.clear_stale_open(TYPE) is False
    assert gen.open_generation(data_dir, TYPE) == generation


def test_clear_stale_open_releases_an_abandoned_lock(manager, data_dir):
    manager.begin(TYPE)
    _age_lock(data_dir, TYPE, manager.begin_ttl + 60)

    assert manager.clear_stale_open(TYPE) is True
    assert gen.read_open(data_dir, TYPE) is None


def test_clear_stale_open_on_a_type_with_no_lock(manager):
    assert manager.clear_stale_open(TYPE) is False


# ---------------------------------------------------------------------------
# The TTL default
# ---------------------------------------------------------------------------

def test_the_default_begin_ttl_is_thirty_minutes():
    """Two hours held a wedged type for most of a working day."""
    assert gen.DEFAULT_BEGIN_TTL == 30 * 60


def test_the_settings_default_matches_the_module_default():
    from django.conf import settings

    assert settings.SWIRL_TANTIVY_BEGIN_TTL == gen.DEFAULT_BEGIN_TTL
