"""BackstageQueryProcessor: the query cleaning on the Backstage provider path.

The defect this fixes was found re-running the gate-zero gauntlet against the
released image. AdaptiveQueryProcessor runs clean_string(), which keeps `-` but
turns `.` into a space, so the provider was asked for `foo-bar com`; the bare
token `com` then matched inside every `recommendation-*` title through the ngram
field and swamped the one exact hit.

BackstageQueryProcessor inherits everything else from AdaptiveQueryProcessor and
replaces only the cleaning step. Galaxy is untouched: only
SearchProviders/backstage.json names the new processor, and the tests below
assert that AdaptiveQueryProcessor still cleans exactly as it did.

Run with: pytest swirl/tests/test_backstage_query_processor.py -v
"""

import json
import os

import pytest

from swirl.processors import alloc_processor
from swirl.processors.adaptive import AdaptiveQueryProcessor
from swirl.processors.backstage_query import (
    BackstageQueryProcessor,
    clean_string_keep_identifiers,
)
from swirl.processors.utils import clean_string

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TAGS = ["backstage", "backstage-index"]


def process(query, tags=TAGS):
    return BackstageQueryProcessor(query, "", list(tags)).process()


def adaptive(query, tags=TAGS):
    return AdaptiveQueryProcessor(query, "", list(tags)).process()


# ---------------------------------------------------------------------------
# The regression
# ---------------------------------------------------------------------------

def test_a_dotted_hostname_keeps_its_dot():
    assert process("foo-bar.com") == "foo-bar.com"


def test_the_old_processor_is_what_broke_it():
    """Pin the behaviour being worked around, so the fix has a reason on file."""
    assert adaptive("foo-bar.com") == "foo-bar com"


def test_the_processor_is_allocatable_by_name():
    """swirl/processors/__init__.py resolves processors out of globals()."""
    assert alloc_processor("BackstageQueryProcessor") is BackstageQueryProcessor


def test_the_shipped_provider_names_it():
    with open(os.path.join(REPO_ROOT, "SearchProviders", "backstage.json"),
              encoding="utf-8") as handle:
        entry = json.load(handle)
    assert entry["query_processors"] == ["BackstageQueryProcessor"]


def test_the_preloaded_copy_names_it_too():
    with open(os.path.join(REPO_ROOT, "SearchProviders", "preloaded.json"),
              encoding="utf-8") as handle:
        entries = json.load(handle)
    by_name = {entry["name"]: entry for entry in entries}
    assert by_name["Backstage Index - SWIRL"]["query_processors"] == [
        "BackstageQueryProcessor"]


# ---------------------------------------------------------------------------
# What the cleaner keeps and what it drops
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("query,expected", [
    ("foo-bar.com", "foo-bar.com"),
    ("tech-radar", "tech-radar"),
    ("my_service", "my_service"),
    ("component/petstore", "component/petstore"),
    ("component:default/petstore", "component:default/petstore"),
    ("backstage.io/techdocs-ref", "backstage.io/techdocs-ref"),
    ("wayback search", "wayback search"),
])
def test_identifier_punctuation_survives(query, expected):
    assert clean_string_keep_identifiers(query) == expected


@pytest.mark.parametrize("query,expected", [
    ("my_service.", "my_service"),
    ("/petstore", "petstore"),
    ("petstore,", "petstore"),
    ("Hello, World!", "Hello World"),
    ("what is a petstore?", "what is a petstore"),
])
def test_edge_punctuation_and_sentence_punctuation_go(query, expected):
    assert clean_string_keep_identifiers(query) == expected


def test_a_dropped_character_does_not_split_the_token():
    """The whole point: clean_string() replaces with a space, this does not."""
    assert clean_string_keep_identifiers("foo,bar") == "foobar"
    assert clean_string("foo|bar").strip() == "foo bar"


def test_a_leading_minus_is_kept_for_the_inherited_not_syntax():
    """AdaptiveQueryProcessor reads a leading `-` as "not this term"."""
    assert clean_string_keep_identifiers("petstore -webhook") == "petstore -webhook"


def test_a_lone_minus_is_dropped():
    assert clean_string_keep_identifiers("petstore - webhook") == "petstore webhook"


def test_empty_and_none_are_safe():
    assert clean_string_keep_identifiers("") == ""
    assert clean_string_keep_identifiers(None) == ""


# ---------------------------------------------------------------------------
# Everything inherited still works
# ---------------------------------------------------------------------------

def test_the_tag_syntax_is_still_adapted():
    """`backstage:` is one of the provider's tags, so the value is taken."""
    assert process("backstage: foo-bar.com") == "foo-bar.com"


@pytest.mark.parametrize("query", [
    "github: petstore",
    "backstage: petstore",
    "petstore",
    "wayback search",
])
def test_the_tag_handling_is_the_inherited_one(query):
    """Only the cleaning step is overridden; nothing else about the tag syntax."""
    assert process(query) == adaptive(query)


def test_a_plain_multi_word_query_is_unchanged():
    assert process("wayback search") == "wayback search"


def test_a_not_term_is_removed_when_the_provider_cannot_express_it():
    """No query_mappings, so the inherited processor drops the notted part."""
    assert process("petstore -webhook") == "petstore"


# ---------------------------------------------------------------------------
# Galaxy is untouched
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("query", [
    "foo-bar.com",
    "wayback search",
    "Hello, World!",
    "what is a petstore?",
    "petstore -webhook",
])
def test_the_adaptive_processor_still_cleans_with_clean_string(query):
    """The refactor added a hook; it must not have moved AdaptiveQueryProcessor."""
    assert AdaptiveQueryProcessor(query, "", []).clean(query) == clean_string(query)
