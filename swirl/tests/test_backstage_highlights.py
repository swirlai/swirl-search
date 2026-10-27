"""
Regression tests for the highlight markers on the Backstage search path.

Defect: federated results reached Backstage with SWIRL's literal `<em>` markers
inside `document.title` and `document.text`, while `highlight.fields` stayed
empty. Backstage renders the document text as plain text, so the markers showed
up on screen. SWIRL's relevancy processor writes the marked-up text back over
`title` and `body`, which is what Galaxy wants; the engine module only reads
`title_hit_highlights` and `body_hit_highlights`, and for a federated result
those were empty.

swirl/views.py now moves the marked-up value into the hit highlight list and
leaves the plain field clean, on the Backstage path only. Galaxy is untouched.

Run with: pytest swirl/tests/test_backstage_highlights.py -v
"""

import pytest
from django.conf import settings
from django.test import RequestFactory

from swirl.views import (
    is_backstage_request,
    move_highlights_out_of_the_plain_fields,
)

START = settings.SWIRL_HIGHLIGHT_START_CHAR
END = settings.SWIRL_HIGHLIGHT_END_CHAR


def marked(text, term):
    return text.replace(term, "{}{}{}".format(START, term, END))


def envelope(*rows):
    return {"info": {}, "results": list(rows)}


def federated_row():
    """What a RequestsGet provider looks like after the relevancy processor.

    No hit highlights of its own: the mapping had none to map, so the marked-up
    plain fields were the only marked text in the whole result.
    """
    return {
        "title": marked("The petstore service", "petstore"),
        "body": marked("A petstore for demonstrations.", "petstore"),
        "url": "https://example.invalid/petstore",
        "searchprovider": "Stub - E2E",
        "title_hit_highlights": [],
        "body_hit_highlights": [],
    }


def indexed_row():
    """A Tantivy hit: the connector supplied its own highlights."""
    return {
        "title": marked("petstore", "petstore"),
        "body": marked("The petstore component of the platform.", "petstore"),
        "url": "/catalog/default/component/petstore",
        "searchprovider": "Backstage Index - SWIRL",
        "title_hit_highlights": [marked("petstore", "petstore")],
        "body_hit_highlights": [marked("The petstore component.", "petstore")],
        "payload": {"backstage": {"type": "software-catalog", "document": {}}},
    }


def backstage_request(**params):
    params.setdefault("backstage_types", "software-catalog")
    return RequestFactory().get("/swirl/search/", params)


def galaxy_request():
    return RequestFactory().get("/swirl/search/", {"qs": "petstore"})


# ---------------------------------------------------------------------------
# Which requests are on the Backstage path
# ---------------------------------------------------------------------------

def test_backstage_types_marks_the_request():
    assert is_backstage_request(backstage_request()) is True


def test_backstage_filters_marks_the_request():
    request = RequestFactory().get("/swirl/search/",
                                   {"backstage_filters": '{"kind":"Component"}'})
    assert is_backstage_request(request) is True


def test_a_backstage_principal_marks_the_request():
    """Page N has no backstage_types on it, only the plugin token."""
    from swirl.backstage_bearer import BackstagePrincipal

    request = RequestFactory().get("/swirl/results/", {"search_id": "1"})
    assert is_backstage_request(request) is False
    request.backstage_principal = BackstagePrincipal("search", "user:default/ada")
    assert is_backstage_request(request) is True


def test_a_galaxy_request_is_not_a_backstage_request():
    assert is_backstage_request(galaxy_request()) is False
    assert is_backstage_request(None) is False


# ---------------------------------------------------------------------------
# The federated path, which is where this was seen
# ---------------------------------------------------------------------------

def test_a_federated_result_gets_clean_fields_and_populated_highlights():
    results = envelope(federated_row())

    changed = move_highlights_out_of_the_plain_fields(results, backstage_request())

    row = results["results"][0]
    assert changed == 2
    assert row["title"] == "The petstore service"
    assert row["body"] == "A petstore for demonstrations."
    assert START not in row["title"] and START not in row["body"]
    # The marked-up text is not lost, it moved.
    assert row["title_hit_highlights"] == [marked("The petstore service",
                                                  "petstore")]
    assert row["body_hit_highlights"] == [
        marked("A petstore for demonstrations.", "petstore")]


def test_an_indexed_result_keeps_the_highlights_the_connector_supplied():
    results = envelope(indexed_row())

    move_highlights_out_of_the_plain_fields(results, backstage_request())

    row = results["results"][0]
    assert row["title"] == "petstore"
    assert row["body"] == "The petstore component of the platform."
    # The connector's own highlight, not the whole marked-up body.
    assert row["body_hit_highlights"] == [marked("The petstore component.",
                                                 "petstore")]


def test_both_result_kinds_in_one_response():
    results = envelope(indexed_row(), federated_row())

    move_highlights_out_of_the_plain_fields(results, backstage_request())

    for row in results["results"]:
        assert START not in row["title"], row
        assert START not in row["body"], row
        assert END not in row["title"], row
        assert END not in row["body"], row
        assert any(row["title_hit_highlights"])
        assert any(row["body_hit_highlights"])


def test_a_result_with_no_markers_is_left_alone():
    row = {"title": "petstore", "body": "no hits here",
           "title_hit_highlights": [], "body_hit_highlights": []}
    results = envelope(dict(row))

    assert move_highlights_out_of_the_plain_fields(
        results, backstage_request()) == 0
    assert results["results"][0] == row


# ---------------------------------------------------------------------------
# Galaxy keeps the behaviour it has
# ---------------------------------------------------------------------------

def test_galaxy_still_gets_the_markers_in_title_and_body():
    """Galaxy renders the markers; nothing here may change that."""
    before = federated_row()
    results = envelope(dict(before))

    assert move_highlights_out_of_the_plain_fields(results, galaxy_request()) == 0
    assert results["results"][0] == before


def test_no_request_means_no_change():
    before = federated_row()
    results = envelope(dict(before))

    assert move_highlights_out_of_the_plain_fields(results, None) == 0
    assert results["results"][0] == before


# ---------------------------------------------------------------------------
# Shapes that must not raise
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("results", [
    None, [], "nonsense", {}, {"results": None}, {"results": "nope"},
    {"results": [None, 3, "x"]},
])
def test_odd_envelopes_do_not_raise(results):
    assert move_highlights_out_of_the_plain_fields(
        results, backstage_request()) == 0
