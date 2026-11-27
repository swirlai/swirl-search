"""
A scoped GitHub provider searches the repository, organisation or user its
template names. A search term cannot name another one: repo:, org: and user:
qualifiers are taken out of the term. Providers without a scope rule, and
providers flagged scope_unrestricted, get the term as typed.
"""

import time
from types import SimpleNamespace
from urllib.parse import unquote_plus

import pytest
from django.contrib.auth.models import User

from swirl.connectors.requestsget import RequestsGet
from swirl.models import Search, SearchProvider
from swirl.scope import remove_scope_qualifiers

SCOPED = '{url}?q={query_string}+repo:example-org/example-repo'


def provider(tags=('GitHub',), config=None):
    return SimpleNamespace(tags=list(tags), config=config or {}, query_template=SCOPED, query_template_json={})


@pytest.mark.parametrize('term,expected', [
    ('timeout org:other-org', 'timeout'),
    ('repo:other-org/other-repo timeout', 'timeout'),
    ('timeout user:someone retry', 'timeout retry'),
    ('timeout ORG:other-org', 'timeout'),
    ('timeout -repo:example-org/example-repo', 'timeout'),
])
def test_scope_qualifiers_are_removed_on_a_scoped_provider(term, expected):
    cleaned, removed = remove_scope_qualifiers(provider(), term)

    assert cleaned == expected
    assert len(removed) == 1


@pytest.mark.parametrize('term', [
    'timeout is:open label:bug',
    'language:python retry',
    'author:someone fix',
    'reorg: the plan',
    'what does superuser:x mean',
    'plain words',
])
def test_other_terms_are_unchanged(term):
    assert remove_scope_qualifiers(provider(), term) == (term, [])


def test_a_provider_without_a_scope_rule_gets_the_term_as_typed():
    term = 'timeout org:other-org'

    assert remove_scope_qualifiers(provider(tags=('Web', 'Dev')), term) == (term, [])


def test_an_unrestricted_provider_gets_the_term_as_typed():
    term = 'timeout org:other-org'
    unrestricted = provider(config={'swirl': {'scope_unrestricted': True}})

    assert remove_scope_qualifiers(unrestricted, term) == (term, [])


def sent_query(tags, config, term):
    owner = User.objects.create_superuser(f'gh_owner_{abs(hash((tags, term)))}', 'gh_owner@example.com', 'not-a-real-password')
    source = SearchProvider.objects.create(
        owner=owner, name='code', shared=True, active=True, connector='RequestsGet',
        url='https://api.github.example.invalid/search/code', query_template=SCOPED,
        query_mappings='', tags=list(tags), config=config)
    search = Search.objects.create(owner=owner, query_string=term, query_string_processed=term,
                                   searchprovider_list=[source.id])
    connector = RequestsGet(source.id, search.id, False, '')
    connector.start_time = time.time()
    connector.query_string_to_provider = term
    connector.construct_query()
    return unquote_plus(connector.query_to_provider)


@pytest.mark.django_db
def test_request_to_a_scoped_github_source_keeps_only_the_operators_scope():
    sent = sent_query(('GitHub', 'Code'), {}, 'timeout org:other-org')

    assert sent.endswith('?q=timeout+repo:example-org/example-repo') or sent.endswith('?q=timeout repo:example-org/example-repo')
    assert 'other-org' not in sent


@pytest.mark.django_db
def test_request_to_an_untagged_source_is_unchanged():
    sent = sent_query(('Code',), {}, 'timeout org:other-org')

    assert 'org:other-org' in sent
