"""
Jira and Confluence templates put the search term inside a quoted literal.
A quote in the term must stay part of that literal.
"""

import pytest

from swirl.connectors.requests import escape_term_for_quoted_literal

JIRA = "https://jira.example.com/rest/api/3/search?jql=project=ENG and text~'{query_string}'"
CONFLUENCE = "https://wiki.example.com/rest/api/search?cql=text~'{query_string}'+and+space='ENG'"
JIRA_DOUBLE = 'https://jira.example.com/rest/api/3/search?jql=text~"{query_string}"'
OTHER = "https://api.example.com/search?q={query_string}"
OTHER_QUOTED = "https://api.example.com/search?filter=name eq '{query_string}'"


@pytest.mark.parametrize('template', [JIRA, CONFLUENCE])
def test_single_quote_in_the_term_is_escaped(template):
    escaped = escape_term_for_quoted_literal(template, "x' or project=OTHER or text~'y")

    assert escaped == "x\\' or project=OTHER or text~\\'y"


def test_double_quote_is_escaped_when_the_template_uses_double_quotes():
    assert escape_term_for_quoted_literal(JIRA_DOUBLE, 'a" or b') == 'a\\" or b'
    assert escape_term_for_quoted_literal(JIRA_DOUBLE, "it's") == "it's"


def test_backslash_cannot_cancel_the_escape():
    assert escape_term_for_quoted_literal(JIRA, "x\\' or y") == "x\\\\\\' or y"


def test_plain_terms_are_unchanged():
    assert escape_term_for_quoted_literal(JIRA, 'release notes 2.1') == 'release notes 2.1'


@pytest.mark.parametrize('template', [OTHER, OTHER_QUOTED])
def test_other_templates_get_the_term_unchanged(template):
    assert escape_term_for_quoted_literal(template, "it's \"here\"") == "it's \"here\""


@pytest.mark.django_db
def test_request_to_a_scoped_jira_source_keeps_the_term_in_one_literal():
    import time
    from urllib.parse import unquote_plus

    from django.contrib.auth.models import User

    from swirl.connectors.requestsget import RequestsGet
    from swirl.models import Search, SearchProvider

    owner = User.objects.create_superuser('jira_owner', 'jira_owner@example.com', 'not-a-real-password')
    provider = SearchProvider.objects.create(
        owner=owner, name='scoped jira', shared=True, active=True, connector='RequestsGet',
        url='https://jira.example.invalid/rest/api/3/search',
        query_template="{url}?jql=project=ENG and text~'{query_string}'", query_mappings='')
    term = "x' or project=OTHER or text~'y"
    search = Search.objects.create(owner=owner, query_string=term, query_string_processed=term,
                                   searchprovider_list=[provider.id])
    connector = RequestsGet(provider.id, search.id, False, '')
    connector.start_time = time.time()
    connector.query_string_to_provider = term

    connector.construct_query()

    sent = unquote_plus(connector.query_to_provider)
    assert sent.endswith("jql=project=ENG and text~'x\\' or project=OTHER or text~\\'y'")
