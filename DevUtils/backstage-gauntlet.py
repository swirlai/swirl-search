#!/usr/bin/env python3
"""
WP00 gate zero: the SWIRL for Backstage relevance gauntlet.

Standalone proof that the Tantivy schema in TECH_DESIGN_swirl_for_backstage.md
section 3.1 fixes the Backstage search relevance complaints. No SWIRL code, no
plugin code, no Django. Only tantivy-py, PyYAML, requests and psutil.

The schema builder, the corpus loaders and the gauntlet cases are importable so
that swirl/tests/test_tantivy_search_relevance.py can run the same assertions.

Usage:
    python DevUtils/backstage-gauntlet.py --synthetic 5000
    python DevUtils/backstage-gauntlet.py --synthetic 0        # example catalog only
    python DevUtils/backstage-gauntlet.py --measure
    python DevUtils/backstage-gauntlet.py --lunr               # compare with Backstage Lunr

Exit code is non-zero when any gauntlet assertion fails.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import resource
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# The schema, the analyzers and the tuning surface live in SWIRL itself as of
# WP01. This script imports them so the gate-zero numbers are measured against
# the shipped code and not against a copy. swirl.tantivy_index.schema and
# swirl.tantivy_index.tuning import no Django, so this stays standalone.
from swirl.tantivy_index.schema import (  # noqa: E402
    SEARCH_FIELDS,
    build_analyzers,
    build_schema,
    document_id,
    escape_term,
    open_index,
)
from swirl.tantivy_index.tuning import DEFAULT_TUNING, Tuning  # noqa: E402

try:
    import tantivy
    from tantivy import Document, Occur, Query

    TANTIVY_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised by the skipif in the test
    TANTIVY_AVAILABLE = False

DEFAULT_EXAMPLES_DIR = os.path.expanduser(
    "~/Code/backstage/packages/catalog-model/examples"
)
DEFAULT_EXTRA_CATALOG_FILES = [
    os.path.expanduser(
        "~/Code/backstage/plugins/techdocs-backend/examples/"
        "documented-component/catalog-info.yaml"
    ),
    os.path.expanduser(
        "~/Code/backstage/plugins/scaffolder-backend/"
        "sample-templates/all-templates.yaml"
    ),
]
DEFAULT_LUNR_BASE_URL = "http://localhost:7007"
BACKSTAGE_DOC_TYPE = "software-catalog"

# ---------------------------------------------------------------------------
# Tuning, schema and analyzers now live in swirl/tantivy_index (WP01) and are
# imported above: Tuning, DEFAULT_TUNING, SEARCH_FIELDS, build_schema,
# build_analyzers, open_index, escape_term and document_id. TECH_DESIGN 2.2
# and 3.1.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Corpus: Backstage example catalog plus synthetic entities
# ---------------------------------------------------------------------------

INDEXED_ATTRS = ("kind", "namespace", "lifecycle", "owner", "type")


def entity_to_document(entity: dict) -> dict | None:
    """Mirror Backstage's DefaultCatalogCollatorEntityTransformer.

    title = metadata.title or metadata.name
    text  = metadata.description or ''
    location = /catalog/<namespace>/<kind>/<name>, lowercased
    plus the kind, namespace, lifecycle, owner and type attributes.
    """
    if not isinstance(entity, dict):
        return None
    kind = entity.get("kind")
    metadata = entity.get("metadata") or {}
    name = metadata.get("name")
    if not kind or not name:
        return None
    spec = entity.get("spec") or {}
    namespace = metadata.get("namespace") or "default"
    spec_type = spec.get("type")
    location = "/catalog/{}/{}/{}".format(namespace, kind, name).lower()
    return {
        "title": metadata.get("title") or name,
        "text": metadata.get("description") or "",
        "location": location,
        "type": BACKSTAGE_DOC_TYPE,
        "kind": kind,
        "namespace": namespace,
        "lifecycle": str(spec.get("lifecycle") or ""),
        "owner": str(spec.get("owner") or ""),
        "componentType": str(spec_type) if spec_type else "other",
    }


def load_example_catalog(
    examples_dir: str = DEFAULT_EXAMPLES_DIR,
    extra_files: Iterable[str] = (),
) -> list[dict]:
    """Load every YAML entity under the Backstage example catalog directory."""
    import yaml

    paths: list[str] = []
    for root, _dirs, files in os.walk(examples_dir):
        for filename in sorted(files):
            if filename.endswith((".yaml", ".yml")):
                paths.append(os.path.join(root, filename))
    paths.extend(p for p in extra_files if os.path.exists(p))

    documents: list[dict] = []
    seen: set[str] = set()
    for path in sorted(paths):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                entities = list(yaml.safe_load_all(handle))
        except Exception as exc:  # pragma: no cover - malformed fixture
            print("warning: could not parse {}: {}".format(path, exc), file=sys.stderr)
            continue
        for entity in entities:
            document = entity_to_document(entity)
            if document and document["location"] not in seen:
                seen.add(document["location"])
                documents.append(document)
    return documents


_SYNTH_PREFIXES = [
    "payment", "user", "order", "billing", "identity", "inventory", "shipping",
    "notification", "catalog", "search", "auth", "session", "profile", "invoice",
    "checkout", "fraud", "pricing", "recommendation", "analytics", "telemetry",
    "audit", "reporting", "settlement", "ledger", "wallet", "subscription",
    "onboarding", "kyc", "risk", "loyalty", "content", "media", "asset",
    "document", "workflow", "scheduler", "dispatch", "routing", "geo", "map",
]
_SYNTH_MIDDLES = [
    "gateway", "profile", "history", "batch", "stream", "sync", "cache", "proxy",
    "adapter", "aggregator", "orchestrator", "publisher", "consumer", "indexer",
    "exporter", "importer", "validator", "resolver", "collector", "reconciler",
]
_SYNTH_SUFFIXES = ["api", "service", "worker", "job", "ui", "lib", "db", "queue"]
_SYNTH_KINDS = ["Component", "API", "Resource", "System", "Domain"]
_SYNTH_LIFECYCLES = ["production", "experimental", "deprecated"]
_SYNTH_OWNERS = ["team-a", "team-b", "team-c", "team-d", "infrastructure", "backstage"]
_SYNTH_TYPES = ["service", "website", "library", "openapi", "grpc", "database"]

#: Entities planted so the gauntlet has something specific to find.
PLANTED_ENTITIES = [
    {
        "name": "abacus",
        "title": None,
        "description": "Counting and reconciliation engine for the ledger domain.",
    },
    {
        "name": "foo-bar-dot-com",
        "title": "foo-bar.com",
        "description": "Marketing site entity with a dotted hostname as its title.",
    },
    {
        "name": "petstore",
        "title": None,
        "description": "Example pet inventory API used in onboarding material.",
    },
    {
        "name": "tech-radar",
        "title": None,
        "description": "Technology radar rendering the adoption rings.",
    },
    {
        "name": "wayback-search",
        "title": None,
        "description": "Search of the wayback machine archive.",
    },
]


def generate_synthetic(count: int, seed: int = 20260903) -> list[dict]:
    """Generate `count` synthetic catalog documents, planted names included.

    The planted entities and the 20 "team" plus 20 "tech" entities are always
    produced when `count` is large enough to hold them.
    """
    if count <= 0:
        return []
    rng = random.Random(seed)
    documents: list[dict] = []
    used_names: set[str] = set()

    def emit(name: str, title: str | None, description: str, kind: str = "Component",
             lifecycle: str | None = None, owner: str | None = None,
             spec_type: str | None = None) -> None:
        if name in used_names:
            return
        used_names.add(name)
        documents.append(
            {
                "title": title or name,
                "text": description,
                "location": "/catalog/synthetic/{}/{}".format(kind, name).lower(),
                "type": BACKSTAGE_DOC_TYPE,
                "kind": kind,
                "namespace": "synthetic",
                "lifecycle": lifecycle or rng.choice(_SYNTH_LIFECYCLES),
                "owner": owner or rng.choice(_SYNTH_OWNERS),
                "componentType": spec_type or rng.choice(_SYNTH_TYPES),
            }
        )

    for planted in PLANTED_ENTITIES:
        emit(
            planted["name"],
            planted["title"],
            planted["description"],
            lifecycle="production",
            owner="team-a",
            spec_type="service",
        )

    # 20 entities whose name or description contains "team", none of which
    # mention "tech". These are the decoys the "tech" case must not surface.
    for i in range(20):
        if i % 2 == 0:
            emit(
                "team-{}-portal".format(chr(ord("a") + i // 2)),
                None,
                "Portal owned by the platform group.",
                kind="Component",
            )
        else:
            emit(
                "roster-service-{}".format(i),
                None,
                "Roster of every team member on call for this squad.",
                kind="Component",
            )

    # 20 entities containing "tech".
    for i in range(20):
        if i % 2 == 0:
            emit(
                "tech-{}-service".format(_SYNTH_MIDDLES[i % len(_SYNTH_MIDDLES)]),
                None,
                "Technology platform component number {}.".format(i),
                kind="Component",
            )
        else:
            emit(
                "platform-registry-{}".format(i),
                None,
                "Records the tech stack chosen for each application.",
                kind="Component",
            )

    attempts = 0
    while len(documents) < count and attempts < count * 40:
        attempts += 1
        prefix = rng.choice(_SYNTH_PREFIXES)
        middle = rng.choice(_SYNTH_MIDDLES)
        suffix = rng.choice(_SYNTH_SUFFIXES)
        if rng.random() < 0.4:
            name = "{}-{}".format(prefix, suffix)
        else:
            name = "{}-{}-{}".format(prefix, middle, suffix)
        if name in used_names:
            name = "{}-{}".format(name, len(documents))
        emit(
            name,
            None,
            "The {} {} that handles {} traffic for the {} domain.".format(
                prefix, middle, suffix, prefix
            ),
            kind=rng.choice(_SYNTH_KINDS),
        )
    return documents[:count] if count < len(documents) else documents


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------


def document_attrs(document: dict) -> list[str]:
    """One lowercased `key=value` token per collator attribute.

    The gate-zero corpus carries the exact attribute set the Backstage catalog
    collator emits, with spec.type under the key `componentType`, so this maps
    that set explicitly. The ingest API uses the general rule in
    swirl.tantivy_index.schema.document_attrs instead: every scalar top level
    attribute other than title, text and location.
    """
    attrs = []
    for key in INDEXED_ATTRS:
        source_key = "componentType" if key == "type" else key
        value = document.get(source_key)
        if value:
            attrs.append("{}={}".format(key, str(value).lower()))
    return attrs


def index_documents(index, documents: list[dict], heap_mb: int = 128) -> int:
    """Write the documents into the index and commit."""
    writer = index.writer(heap_mb * 1024 * 1024)
    for document in documents:
        title = document.get("title") or ""
        writer.add_document(
            Document(
                title_exact=title,
                title_ngram=title,
                text=document.get("text") or "",
                attrs=document_attrs(document),
                doc_id=document_id(document),
                type=document.get("type") or BACKSTAGE_DOC_TYPE,
                title=title,
                location=document.get("location") or "",
                document_json=json.dumps(document, sort_keys=True),
            )
        )
    writer.commit()
    writer.wait_merging_threads()
    index.reload()
    return len(documents)


def build_corpus_index(
    documents: list[dict],
    path: str | None = None,
    tuning: Tuning = DEFAULT_TUNING,
    heap_mb: int = 128,
):
    index = open_index(path, tuning)
    index_documents(index, documents, heap_mb=heap_mb)
    return index


# ---------------------------------------------------------------------------
# Query building (TECH_DESIGN 3.1 manager.search)
# ---------------------------------------------------------------------------

def build_query(
    index,
    term: str,
    filters: dict[str, Any] | None = None,
    fuzzy: bool = False,
    tuning: Tuning = DEFAULT_TUNING,
):
    """Build the query the design describes: parsed multi-field query, an
    optional phrase boost on title_exact for multi-word input, and an AND of
    attrs term queries for each filter."""
    schema = index.schema
    fuzzy_fields: dict[str, tuple[bool, int, bool]] = {}
    if fuzzy:
        fuzzy_fields = {"title_exact": (False, tuning.fuzzy_distance, True)}
    parsed = index.parse_query(
        escape_term(term),
        default_field_names=list(SEARCH_FIELDS),
        field_boosts=dict(tuning.field_boosts),
        fuzzy_fields=fuzzy_fields,
    )

    subqueries: list[tuple[Any, Any]] = [(Occur.Must, parsed)]

    exact_analyzer = build_analyzers(tuning)["swirl_exact"]
    tokens = exact_analyzer.analyze(term)
    if len(tokens) > 1:
        phrase = Query.phrase_query(schema, "title_exact", list(tokens))
        subqueries.append(
            (Occur.Should, Query.boost_query(phrase, tuning.title_exact_boost * 2.0))
        )

    for key, value in (filters or {}).items():
        values = value if isinstance(value, (list, tuple, set)) else [value]
        clauses = [
            (
                Occur.Should,
                Query.term_query(
                    schema, "attrs", "{}={}".format(key, str(v).lower()), "basic"
                ),
            )
            for v in values
        ]
        subqueries.append((Occur.Must, Query.boolean_query(clauses)))

    return Query.boolean_query(subqueries)


def search(
    index,
    term: str,
    limit: int = 10,
    filters: dict[str, Any] | None = None,
    fuzzy: bool = False,
    tuning: Tuning = DEFAULT_TUNING,
) -> list[dict]:
    """Return a list of hit dicts with title, score, location, doc_id and type."""
    query = build_query(index, term, filters=filters, fuzzy=fuzzy, tuning=tuning)
    searcher = index.searcher()
    result = searcher.search(query, limit)
    hits = []
    for score, address in result.hits:
        stored = searcher.doc(address)
        payload = stored.get_first("document_json")
        hits.append(
            {
                "title": stored.get_first("title") or "",
                "score": float(score),
                "location": stored.get_first("location") or "",
                "doc_id": stored.get_first("doc_id") or "",
                "type": stored.get_first("type") or "",
                "document": json.loads(payload) if payload else {},
            }
        )
    return hits


# ---------------------------------------------------------------------------
# Gauntlet cases
# ---------------------------------------------------------------------------


@dataclass
class GauntletCase:
    name: str
    term: str
    expectation: str
    check: Callable[[list[dict]], tuple[bool, str]]
    requires: tuple[str, ...] = ()
    fuzzy: bool = False
    filters: dict[str, Any] | None = None
    limit: int = 5
    #: Optional corpus predicate. When it returns a reason string the case is
    #: reported as not comparable instead of failing.
    requires_corpus: Callable[[list[dict]], str | None] | None = None


def _titles(hits: list[dict]) -> list[str]:
    return [hit["title"] for hit in hits]


def _rank_of(hits: list[dict], title: str) -> int | None:
    for position, hit in enumerate(hits, start=1):
        if hit["title"] == title:
            return position
    return None


def _is_team_only(title: str, text: str = "") -> bool:
    blob = "{} {}".format(title, text).lower()
    return "team" in blob and "tech" not in blob


def _check_tech(hits: list[dict]) -> tuple[bool, str]:
    titles = _titles(hits)
    if not titles:
        return False, "no hits"
    tech_ranks = [
        position
        for position, title in enumerate(titles, start=1)
        if title.lower().startswith("tech")
    ]
    if not tech_ranks:
        return False, "no title starting with 'tech' in the top {}".format(len(titles))
    team_ranks = [
        position
        for position, hit in enumerate(hits, start=1)
        if _is_team_only(hit["title"], hit["document"].get("text", ""))
    ]
    if team_ranks:
        return False, "team-only entity at rank {}".format(team_ranks[0])
    return True, "tech-prefixed title at rank {}, no team-only entity in top 5".format(
        tech_ranks[0]
    )


def _top_n(title: str, n: int) -> Callable[[list[dict]], tuple[bool, str]]:
    def check(hits: list[dict]) -> tuple[bool, str]:
        rank = _rank_of(hits, title)
        if rank is None:
            return False, "'{}' absent from the top {}".format(title, len(hits))
        if rank > n:
            return False, "'{}' at rank {}, needed top {}".format(title, rank, n)
        return True, "'{}' at rank {}".format(title, rank)

    return check


def _check_mes(hits: list[dict]) -> tuple[bool, str]:
    bad = [
        hit["title"]
        for hit in hits[:5]
        if "web" in hit["title"].lower() or "used" in hit["title"].lower()
    ]
    if bad:
        return False, "substring garbage in the top 5: {}".format(bad)
    return True, "top 5 free of 'web' and 'used' ({} hits)".format(len(hits))


def _check_filter(hits: list[dict]) -> tuple[bool, str]:
    if not hits:
        return False, "no hits, cannot prove the filter"
    offenders = [
        hit["title"]
        for hit in hits
        if str(hit["document"].get("kind", "")).lower() != "component"
        or str(hit["document"].get("lifecycle", "")).lower() != "production"
    ]
    if offenders:
        return False, "filter leaked: {}".format(offenders[:3])
    return True, "all {} hits are kind=component and lifecycle=production".format(
        len(hits)
    )


def _needs_filterable_service(documents: list[dict]) -> str | None:
    """The filter case only means something when the corpus holds at least one
    kind=component, lifecycle=production document that the term 'service' can
    reach through title or text."""
    for document in documents:
        blob = "{} {}".format(document.get("title", ""), document.get("text", "")).lower()
        if (
            "service" in blob
            and str(document.get("kind", "")).lower() == "component"
            and str(document.get("lifecycle", "")).lower() == "production"
        ):
            return None
    return (
        "no kind=component, lifecycle=production document matches the term "
        "'service' in this corpus"
    )


GAUNTLET_CASES: list[GauntletCase] = [
    GauntletCase(
        name="tech-not-team",
        term="tech",
        expectation="a title starting with 'tech' ranks above any team-only "
        "entity, and no team-only entity in the top 5",
        check=_check_tech,
        requires=("tech-radar",),
    ),
    GauntletCase(
        name="abac-prefix",
        term="abac",
        expectation="abacus in the top 3",
        check=_top_n("abacus", 3),
        requires=("abacus",),
    ),
    GauntletCase(
        name="dotted-hostname",
        term="foo-bar.com",
        expectation="foo-bar.com at rank 1",
        check=_top_n("foo-bar.com", 1),
        requires=("foo-bar.com",),
    ),
    GauntletCase(
        name="infix-store",
        term="store",
        expectation="petstore in the top 3",
        check=_top_n("petstore", 3),
        requires=("petstore",),
    ),
    GauntletCase(
        name="mes-no-garbage",
        term="mes",
        expectation="nothing containing 'web' or 'used' in the top 5",
        check=_check_mes,
    ),
    GauntletCase(
        name="wayback",
        term="wayback",
        expectation="wayback-search in the top 3",
        check=_top_n("wayback-search", 3),
        requires=("wayback-search",),
    ),
    GauntletCase(
        name="fuzzy-typo",
        term="petsotre",
        expectation="petstore in the top 3 with fuzzy on",
        check=_top_n("petstore", 3),
        requires=("petstore",),
        fuzzy=True,
    ),
    GauntletCase(
        name="phrase-multiword",
        term="wayback search",
        expectation="wayback-search at rank 1",
        check=_top_n("wayback-search", 1),
        requires=("wayback-search",),
    ),
    GauntletCase(
        name="attrs-filter",
        term="service",
        expectation="only kind=component and lifecycle=production documents",
        check=_check_filter,
        filters={"kind": "component", "lifecycle": "production"},
        limit=25,
        requires_corpus=_needs_filterable_service,
    ),
]


def corpus_titles(documents: list[dict]) -> set[str]:
    return {document.get("title") or "" for document in documents}


def run_gauntlet(
    index,
    documents: list[dict],
    cases: list[GauntletCase] | None = None,
    tuning: Tuning = DEFAULT_TUNING,
) -> list[dict]:
    """Run every case and return one result row per case."""
    cases = cases if cases is not None else GAUNTLET_CASES
    available = corpus_titles(documents)
    results = []
    for case in cases:
        missing = [title for title in case.requires if title not in available]
        reason = None
        if missing:
            reason = "not comparable, corpus has no {}".format(", ".join(missing))
        elif case.requires_corpus is not None:
            corpus_reason = case.requires_corpus(documents)
            if corpus_reason:
                reason = "not comparable, {}".format(corpus_reason)
        if reason:
            results.append(
                {
                    "case": case.name,
                    "query": case.term,
                    "expected": case.expectation,
                    "hits": [],
                    "status": "N/A",
                    "detail": reason,
                }
            )
            continue
        hits = search(
            index,
            case.term,
            limit=case.limit,
            filters=case.filters,
            fuzzy=case.fuzzy,
            tuning=tuning,
        )
        passed, detail = case.check(hits)
        results.append(
            {
                "case": case.name,
                "query": case.term,
                "expected": case.expectation,
                "hits": hits[:5],
                "status": "PASS" if passed else "FAIL",
                "detail": detail,
            }
        )
    return results


def assert_gauntlet(index, documents: list[dict], tuning: Tuning = DEFAULT_TUNING):
    """Raise AssertionError on the first failing case. Used by the unit test."""
    results = run_gauntlet(index, documents, tuning=tuning)
    failures = [row for row in results if row["status"] == "FAIL"]
    if failures:
        lines = [
            "{}: {} ({})".format(
                row["case"], row["detail"], ", ".join(_titles(row["hits"]))
            )
            for row in failures
        ]
        raise AssertionError("gauntlet failures:\n  " + "\n  ".join(lines))
    return results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def format_table(results: list[dict], title: str = "") -> str:
    lines = []
    if title:
        lines.append("")
        lines.append("=" * 100)
        lines.append(title)
        lines.append("=" * 100)
    for row in results:
        lines.append("")
        lines.append(
            "[{}] {}  query: {!r}".format(row["status"], row["case"], row["query"])
        )
        lines.append("  expected: {}".format(row["expected"]))
        lines.append("  result:   {}".format(row["detail"]))
        if row["hits"]:
            for position, hit in enumerate(row["hits"], start=1):
                lines.append(
                    "    {}. {:<44} {:.4f}".format(
                        position, hit["title"][:44], hit["score"]
                    )
                )
        elif row["status"] != "N/A":
            lines.append("    (no hits)")
    counts = {"PASS": 0, "FAIL": 0, "N/A": 0}
    for row in results:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines.append("")
    lines.append(
        "  totals: {} pass, {} fail, {} not applicable".format(
            counts["PASS"], counts["FAIL"], counts["N/A"]
        )
    )
    return "\n".join(lines)


def markdown_table(results: list[dict]) -> str:
    lines = [
        "| Query | Expected | Top 5 (title, score) | Result |",
        "|---|---|---|---|",
    ]
    for row in results:
        top = (
            "<br>".join(
                "{}. {} ({:.3f})".format(i, h["title"], h["score"])
                for i, h in enumerate(row["hits"], start=1)
            )
            or "-"
        )
        lines.append(
            "| `{}` | {} | {} | **{}** {} |".format(
                row["query"], row["expected"], top, row["status"], row["detail"]
            )
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------


def directory_size_mb(path: str) -> float:
    total = 0
    for root, _dirs, files in os.walk(path):
        for filename in files:
            try:
                total += os.path.getsize(os.path.join(root, filename))
            except OSError:
                pass
    return total / (1024 * 1024)


def peak_rss_mb() -> float:
    """Peak resident set size of this process, in MB."""
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports kilobytes, macOS reports bytes.
    return usage / (1024 * 1024) if sys.platform == "darwin" else usage / 1024


def current_rss_mb() -> float:
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:
        return float("nan")


def measure(count: int, workdir: str, tuning: Tuning = DEFAULT_TUNING,
            iterations: int = 100) -> dict:
    """Index `count` synthetic entities and report size, memory and latency."""
    path = os.path.join(workdir, "measure-{}".format(count))
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)

    documents = generate_synthetic(count)
    index = open_index(path, tuning)
    started = time.perf_counter()
    index_documents(index, documents)
    index_seconds = time.perf_counter() - started
    rss_after_index = current_rss_mb()

    terms = [(case.term, case.fuzzy, case.filters) for case in GAUNTLET_CASES]
    query_started = time.perf_counter()
    for _ in range(iterations):
        for term, fuzzy, filters in terms:
            search(index, term, limit=10, filters=filters, fuzzy=fuzzy, tuning=tuning)
    query_seconds = time.perf_counter() - query_started
    total_queries = iterations * len(terms)

    return {
        "entities": len(documents),
        "index_mb": round(directory_size_mb(path), 2),
        "index_seconds": round(index_seconds, 2),
        "docs_per_second": round(len(documents) / index_seconds, 1),
        "rss_after_index_mb": round(rss_after_index, 1),
        "peak_rss_mb": round(peak_rss_mb(), 1),
        "queries": total_queries,
        "mean_query_ms": round(query_seconds * 1000 / total_queries, 3),
        "path": path,
    }


# ---------------------------------------------------------------------------
# Lunr comparison against a running Backstage
# ---------------------------------------------------------------------------


def lunr_token(base_url: str = DEFAULT_LUNR_BASE_URL) -> str:
    import requests

    response = requests.post(
        "{}/api/auth/guest/refresh".format(base_url),
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["backstageIdentity"]["token"]


def lunr_search(term: str, token: str, base_url: str = DEFAULT_LUNR_BASE_URL,
                page_limit: int = 25) -> list[dict]:
    import requests

    response = requests.get(
        "{}/api/search/query".format(base_url),
        params={"term": term, "pageLimit": page_limit},
        headers={"Authorization": "Bearer {}".format(token)},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return [
        {
            "title": result["document"].get("title", ""),
            "score": 0.0,
            "location": result["document"].get("location", ""),
            "doc_id": result["document"].get("location", ""),
            "type": result.get("type", ""),
            "document": result["document"],
        }
        for result in payload.get("results", [])
    ]


def run_lunr_gauntlet(documents: list[dict], base_url: str = DEFAULT_LUNR_BASE_URL
                      ) -> list[dict]:
    """Run the gauntlet cases against Backstage's Lunr engine.

    Lunr has no attrs filter surface, so the filter case is reported as not
    applicable rather than failed.
    """
    token = lunr_token(base_url)
    available = corpus_titles(documents)
    results = []
    for case in GAUNTLET_CASES:
        if case.name == "attrs-filter":
            results.append(
                {
                    "case": case.name,
                    "query": case.term,
                    "expected": case.expectation,
                    "hits": [],
                    "status": "N/A",
                    "detail": "Lunr exposes no attribute filter through the query API",
                }
            )
            continue
        missing = [title for title in case.requires if title not in available]
        if missing:
            results.append(
                {
                    "case": case.name,
                    "query": case.term,
                    "expected": case.expectation,
                    "hits": [],
                    "status": "N/A",
                    "detail": "not comparable, catalog has no {}".format(
                        ", ".join(missing)
                    ),
                }
            )
            continue
        hits = lunr_search(case.term, token, base_url)[: case.limit]
        passed, detail = case.check(hits)
        results.append(
            {
                "case": case.name,
                "query": case.term,
                "expected": case.expectation,
                "hits": hits[:5],
                "status": "PASS" if passed else "FAIL",
                "detail": detail,
            }
        )
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", type=int, default=5000,
                        help="number of synthetic entities to add (default 5000)")
    parser.add_argument("--examples-dir", default=DEFAULT_EXAMPLES_DIR,
                        help="Backstage catalog-model examples directory")
    parser.add_argument("--index-dir", default=None,
                        help="where to write the index (default: a temp dir)")
    parser.add_argument("--measure", action="store_true",
                        help="run the 5k and 50k size, memory and latency measurements")
    parser.add_argument("--measure-only", type=int, default=None, metavar="N",
                        help="measure a single corpus size in this process and exit, "
                             "so peak RSS is not carried over from an earlier size")
    parser.add_argument("--lunr", action="store_true",
                        help="also run the gauntlet against a running Backstage")
    parser.add_argument("--lunr-base-url", default=DEFAULT_LUNR_BASE_URL)
    parser.add_argument("--example-only", action="store_true",
                        help="index only the example catalog, for the Lunr comparison")
    parser.add_argument("--markdown", action="store_true",
                        help="also print the results as a markdown table")
    parser.add_argument("--iterations", type=int, default=100,
                        help="query latency iterations for --measure (default 100)")
    args = parser.parse_args(argv)

    if not TANTIVY_AVAILABLE:
        print("tantivy is not installed: pip install tantivy", file=sys.stderr)
        return 2

    print("tantivy: {}".format(tantivy.__version__))
    workdir = args.index_dir or tempfile.mkdtemp(prefix="backstage-gauntlet-")
    os.makedirs(workdir, exist_ok=True)
    failed = False

    if args.measure_only:
        stats = measure(args.measure_only, workdir, iterations=args.iterations)
        print(json.dumps(stats, indent=2))
        return 0

    example_documents = load_example_catalog(
        args.examples_dir, DEFAULT_EXTRA_CATALOG_FILES
    )
    print("example catalog documents: {}".format(len(example_documents)))

    # Pass 1: example catalog only, the like-for-like corpus for Lunr.
    example_path = os.path.join(workdir, "example-only")
    if os.path.exists(example_path):
        shutil.rmtree(example_path)
    os.makedirs(example_path)
    example_index = build_corpus_index(example_documents, example_path)
    example_results = run_gauntlet(example_index, example_documents)
    print(format_table(example_results, "TANTIVY, Backstage example catalog only"))
    failed |= any(row["status"] == "FAIL" for row in example_results)
    if args.markdown:
        print("\n" + markdown_table(example_results))

    # Pass 2: example catalog plus synthetic entities.
    if not args.example_only and args.synthetic > 0:
        combined = example_documents + generate_synthetic(args.synthetic)
        combined_path = os.path.join(workdir, "example-plus-synthetic")
        if os.path.exists(combined_path):
            shutil.rmtree(combined_path)
        os.makedirs(combined_path)
        combined_index = build_corpus_index(combined, combined_path)
        combined_results = run_gauntlet(combined_index, combined)
        print(
            format_table(
                combined_results,
                "TANTIVY, example catalog plus {} synthetic entities "
                "({} documents, {:.2f} MB)".format(
                    args.synthetic, len(combined), directory_size_mb(combined_path)
                ),
            )
        )
        failed |= any(row["status"] == "FAIL" for row in combined_results)
        if args.markdown:
            print("\n" + markdown_table(combined_results))

    # Lunr comparison.
    if args.lunr:
        try:
            lunr_results = run_lunr_gauntlet(example_documents, args.lunr_base_url)
            print(
                format_table(
                    lunr_results,
                    "LUNR, running Backstage at {} (example catalog only)".format(
                        args.lunr_base_url
                    ),
                )
            )
            if args.markdown:
                print("\n" + markdown_table(lunr_results))
            wrong = [r["case"] for r in lunr_results if r["status"] == "FAIL"]
            print("\n  Lunr gets these cases wrong: {}".format(wrong or "none"))
        except Exception as exc:
            print("\n  Lunr comparison unavailable: {}".format(exc), file=sys.stderr)

    # Measurements.
    if args.measure:
        print("\n" + "=" * 100)
        print("MEASUREMENTS")
        print("=" * 100)
        for count in (5000, 50000):
            stats = measure(count, workdir, iterations=args.iterations)
            print(
                "\n{} entities: index {} MB, indexed in {} s ({} docs/s), "
                "RSS after index {} MB, peak RSS {} MB, mean query {} ms "
                "over {} queries".format(
                    stats["entities"], stats["index_mb"], stats["index_seconds"],
                    stats["docs_per_second"], stats["rss_after_index_mb"],
                    stats["peak_rss_mb"], stats["mean_query_ms"], stats["queries"],
                )
            )

    print("\nindex working directory: {}".format(workdir))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
