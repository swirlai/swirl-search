"""
Tests for scope restriction on SearchProviders (WP05).

A source whose tag carries a rule in swirl/scope.py cannot be activated until
its query carries a scope restriction, in the model, through the REST
serializer and in the admin form. The config.swirl.scope_unrestricted bypass
allows activation, warns on federate and labels the results.
"""

import json

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from swirl.admin import SearchProviderAdminForm
from swirl.models import SearchProvider
from swirl.scope import (
    SCOPE_RULES,
    check_scope,
    is_scope_unrestricted,
    mark_shared_visibility,
    scope_rules_for,
    warn_if_unrestricted,
)
from swirl.serializers import SearchProviderSerializer

UNRESTRICTED = {'swirl': {'scope_unrestricted': True}}


@pytest.fixture
def owner(db):
    user, _ = User.objects.get_or_create(username='scope_owner')
    return user


def _provider(owner, **kwargs):
    """An unsaved provider with sensible defaults for the rule under test."""
    fields = {
        'name': 'Code - GitHub',
        'owner': owner,
        'active': True,
        'connector': 'RequestsGet',
        'url': 'https://api.github.com/search/code',
        'query_template': '{url}?q={query_string}',
        'tags': ['GitHub', 'Code', 'Dev'],
    }
    fields.update(kwargs)
    return SearchProvider(**fields)


# ---------------------------------------------------------------------------
# The rule table itself
# ---------------------------------------------------------------------------

def test_rules_cover_the_four_designed_tags():
    assert set(SCOPE_RULES) == {'github', 'confluence', 'jira', 'gitlab'}


def test_tag_matching_is_case_insensitive(owner):
    provider = _provider(owner, tags=['GitHub'])
    assert [tag for tag, _ in scope_rules_for(provider)] == ['GitHub']


def test_a_provider_with_no_ruled_tag_is_never_checked(owner):
    provider = _provider(owner, name='Web - Google PSE', tags=['Google', 'Web'])
    assert scope_rules_for(provider) == []
    assert check_scope(provider) is None


# ---------------------------------------------------------------------------
# check_scope
# ---------------------------------------------------------------------------

def test_inactive_provider_without_scope_is_allowed(owner):
    assert check_scope(_provider(owner, active=False)) is None


def test_active_github_without_scope_is_rejected(owner):
    error = check_scope(_provider(owner))
    assert error is not None
    assert 'scope restriction' in error


@pytest.mark.parametrize('scope', ['repo:acme/widgets', 'org:acme', 'user:sid'])
def test_active_github_with_a_scope_is_allowed(owner, scope):
    provider = _provider(owner, query_template='{url}?q={query_string}+' + scope)
    assert check_scope(provider) is None


def test_confluence_needs_a_space(owner):
    unscoped = _provider(
        owner, name='Docs - Confluence', tags=['Confluence'],
        query_template="{url}&cql=text~'{query_string}'",
    )
    assert check_scope(unscoped) is not None

    scoped = _provider(
        owner, name='Docs - Confluence', tags=['Confluence'],
        query_template="{url}&cql=text~'{query_string}'+and+space='ENG'",
    )
    assert check_scope(scoped) is None


def test_jira_needs_a_project(owner):
    unscoped = _provider(
        owner, name='Issues - Jira', tags=['Jira'],
        query_template="{url}&jql=text~'{query_string}'",
    )
    assert check_scope(unscoped) is not None

    scoped = _provider(
        owner, name='Issues - Jira', tags=['Jira'],
        query_template="{url}&jql=project=ENG and text~'{query_string}'",
    )
    assert check_scope(scoped) is None


def test_the_scope_may_live_in_query_template_json(owner):
    provider = _provider(
        owner,
        query_template='',
        query_template_json={'q': '{query_string} repo:acme/widgets'},
    )
    assert check_scope(provider) is None


def test_the_bypass_flag_allows_activation(owner):
    provider = _provider(owner, config=UNRESTRICTED)
    assert is_scope_unrestricted(provider) is True
    assert check_scope(provider) is None


def test_a_config_without_the_flag_does_not_bypass(owner):
    assert check_scope(_provider(owner, config={'swirl': {}})) is not None
    assert check_scope(_provider(owner, config={'other': True})) is not None


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_model_clean_rejects_activation_without_a_scope(owner):
    with pytest.raises(DjangoValidationError) as excinfo:
        _provider(owner).full_clean()
    assert 'query_template' in excinfo.value.message_dict


@pytest.mark.django_db
def test_model_clean_accepts_a_scoped_provider(owner):
    _provider(owner, query_template='{url}?q={query_string}+repo:acme/widgets').full_clean()


@pytest.mark.django_db
def test_model_clean_accepts_the_bypass(owner):
    _provider(owner, config=UNRESTRICTED).full_clean()


# ---------------------------------------------------------------------------
# REST serializer
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_serializer_rejects_activation_without_a_scope(owner):
    serializer = SearchProviderSerializer(data={
        'name': 'Code - GitHub',
        'active': True,
        'connector': 'RequestsGet',
        'url': 'https://api.github.com/search/code',
        'query_template': '{url}?q={query_string}',
        'tags': ['GitHub'],
    })
    assert serializer.is_valid() is False
    assert 'query_template' in serializer.errors


@pytest.mark.django_db
def test_serializer_accepts_a_scoped_provider(owner):
    serializer = SearchProviderSerializer(data={
        'name': 'Code - GitHub',
        'active': True,
        'connector': 'RequestsGet',
        'url': 'https://api.github.com/search/code',
        'query_template': '{url}?q={query_string}+repo:acme/widgets',
        'tags': ['GitHub'],
    })
    assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
def test_serializer_accepts_the_bypass(owner):
    serializer = SearchProviderSerializer(data={
        'name': 'Code - GitHub',
        'active': True,
        'connector': 'RequestsGet',
        'url': 'https://api.github.com/search/code',
        'query_template': '{url}?q={query_string}',
        'tags': ['GitHub'],
        'config': UNRESTRICTED,
    })
    assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
def test_serializer_judges_a_patch_against_the_stored_template(owner):
    """Flipping only `active` on a stored unscoped provider is still rejected."""
    stored = _provider(owner, active=False)
    stored.save()

    serializer = SearchProviderSerializer(stored, data={'active': True}, partial=True)
    assert serializer.is_valid() is False
    assert 'query_template' in serializer.errors


# ---------------------------------------------------------------------------
# Admin form
# ---------------------------------------------------------------------------

def _admin_form_data(**overrides):
    data = {
        'name': 'Code - GitHub',
        'active': True,
        'shared': False,
        'default': False,
        'connector': 'RequestsGet',
        'url': 'https://api.github.com/search/code',
        'query_template': '{url}?q={query_string}',
        'query_template_json': '{}',
        'post_query_template': '{}',
        'http_request_headers': '{}',
        'page_fetch_config_json': '{}',
        'query_processors': '["AdaptiveQueryProcessor"]',
        'result_processors': '["MappingResultProcessor"]',
        'query_mappings': '',
        'response_mappings': '',
        'result_mappings': '',
        'result_grouping_field': '',
        'results_per_query': 10,
        'credentials': '',
        'eval_credentials': '',
        'authenticator': '',
        'tags': '["GitHub"]',
        'config': '{}',
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_admin_form_rejects_activation_without_a_scope(owner):
    form = SearchProviderAdminForm(data=_admin_form_data(owner=owner.pk))
    assert form.is_valid() is False
    assert 'query_template' in form.errors


@pytest.mark.django_db
def test_admin_form_accepts_a_scoped_provider(owner):
    form = SearchProviderAdminForm(data=_admin_form_data(
        owner=owner.pk,
        query_template='{url}?q={query_string}+repo:acme/widgets',
    ))
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_admin_form_accepts_the_bypass(owner):
    form = SearchProviderAdminForm(data=_admin_form_data(
        owner=owner.pk, config=json.dumps(UNRESTRICTED),
    ))
    assert form.is_valid(), form.errors


# ---------------------------------------------------------------------------
# Bypass side effects: the warning and the result label
# ---------------------------------------------------------------------------

def test_bypass_warns_once_per_federate(owner, caplog):
    provider = _provider(owner, config=UNRESTRICTED)
    with caplog.at_level('WARNING', logger='swirl.scope'):
        assert warn_if_unrestricted(provider) is True
    assert 'without a scope restriction' in caplog.text


def test_no_warning_for_a_scoped_provider(owner, caplog):
    provider = _provider(owner, query_template='{url}?q={query_string}+repo:acme/widgets')
    with caplog.at_level('WARNING', logger='swirl.scope'):
        assert warn_if_unrestricted(provider) is False
    assert caplog.text == ''


def test_no_warning_for_a_provider_with_no_rule(owner):
    provider = _provider(owner, tags=['Google'], config=UNRESTRICTED)
    assert warn_if_unrestricted(provider) is False


def test_results_from_an_unrestricted_provider_are_labelled(owner):
    provider = _provider(owner, config=UNRESTRICTED)
    results = [{'title': 'a'}, {'title': 'b', 'payload': {'k': 'v'}}]

    assert mark_shared_visibility(provider, results) == 2
    assert results[0]['payload']['shared_visibility'] == 'unrestricted'
    assert results[1]['payload'] == {'k': 'v', 'shared_visibility': 'unrestricted'}


def test_results_from_a_scoped_provider_are_not_labelled(owner):
    provider = _provider(owner, query_template='{url}?q={query_string}+repo:acme/widgets')
    results = [{'title': 'a'}]

    assert mark_shared_visibility(provider, results) == 0
    assert 'payload' not in results[0]


# ---------------------------------------------------------------------------
# The shipped fixtures still load
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_every_preloaded_provider_passes_the_rule(owner):
    """No shipped provider is blocked by its own rule when loaded as shipped."""
    with open('SearchProviders/preloaded.json') as handle:
        preloaded = json.load(handle)

    blocked = []
    for entry in preloaded:
        provider = SearchProvider(
            owner=owner,
            name=entry.get('name', ''),
            active=entry.get('active', False),
            query_template=entry.get('query_template', ''),
            query_template_json=entry.get('query_template_json') or {},
            tags=entry.get('tags', []),
            config=entry.get('config') or {},
        )
        if check_scope(provider):
            blocked.append(entry.get('name'))

    assert blocked == []


@pytest.mark.django_db
def test_preloaded_github_and_confluence_ship_with_placeholder_scopes(owner):
    with open('SearchProviders/preloaded.json') as handle:
        preloaded = json.load(handle)

    by_name = {entry['name']: entry for entry in preloaded}
    for name in ('Code - GitHub', 'Issues - GitHub', 'PRs - GitHub', 'Commits - GitHub'):
        assert 'repo:<your-org>/<your-repo>' in by_name[name]['query_template'], name
    assert "space='<YOUR-SPACE-KEY>'" in by_name['Docs - Atlassian Confluence']['query_template']


# ---------------------------------------------------------------------------
# The federated providers the Backstage engine fans out to
#
# The engine's default federated.providerTags is ["backstage"], so a provider
# has to carry that tag to take part in the swirl-federated lane. These five
# are the ones a Backstage evaluator is most likely to want, and they ship
# inactive with a placeholder scope, exactly as before.
# ---------------------------------------------------------------------------

BACKSTAGE_FEDERATED = ('Code - GitHub', 'Issues - GitHub', 'PRs - GitHub',
                       'Commits - GitHub', 'Docs - Atlassian Confluence')

PROVIDER_FILES = ('SearchProviders/preloaded.json',
                  'SearchProviders/github.json',
                  'SearchProviders/atlassian.json')


@pytest.mark.parametrize('path', PROVIDER_FILES)
def test_the_backstage_tag_is_on_the_github_and_confluence_providers(path):
    with open(path) as handle:
        entries = json.load(handle)

    by_name = {entry['name']: entry for entry in entries}
    wanted = [name for name in BACKSTAGE_FEDERATED if name in by_name]
    assert wanted, path
    for name in wanted:
        assert 'backstage' in by_name[name]['tags'], (path, name)


@pytest.mark.parametrize('path', PROVIDER_FILES)
def test_the_backstage_tag_did_not_replace_the_tags_that_were_there(path):
    """The tag is added, not swapped in: Galaxy filters on the old ones."""
    expected = {
        'Code - GitHub': {'GitHub', 'Code', 'Dev'},
        'Issues - GitHub': {'GitHub', 'Issues', 'Dev'},
        'PRs - GitHub': {'GitHub', 'PullRequests', 'PRs', 'Dev'},
        'Commits - GitHub': {'GitHub', 'Commits', 'Dev'},
        'Docs - Atlassian Confluence': {'Confluence', 'Atlassian', 'Dev'},
    }
    with open(path) as handle:
        by_name = {entry['name']: entry for entry in json.load(handle)}

    for name, tags in expected.items():
        if name not in by_name:
            continue
        assert tags <= set(by_name[name]['tags']), (path, name)


@pytest.mark.parametrize('path', PROVIDER_FILES)
def test_the_backstage_federated_providers_still_ship_inactive_and_scoped(path):
    """Tagging them must not switch them on, nor drop the placeholder scope."""
    with open(path) as handle:
        by_name = {entry['name']: entry for entry in json.load(handle)}

    for name in BACKSTAGE_FEDERATED:
        if name not in by_name:
            continue
        entry = by_name[name]
        assert entry['active'] is False, (path, name)
        if name.endswith('GitHub'):
            assert 'repo:<your-org>/<your-repo>' in entry['query_template'], name
        else:
            assert "space='<YOUR-SPACE-KEY>'" in entry['query_template'], name


@pytest.mark.django_db
def test_the_backstage_tagged_providers_still_pass_their_own_scope_rule(owner):
    """Adding a tag must not make a shipped provider fail check_scope."""
    with open('SearchProviders/preloaded.json') as handle:
        by_name = {entry['name']: entry for entry in json.load(handle)}

    for name in BACKSTAGE_FEDERATED:
        entry = by_name[name]
        provider = SearchProvider(
            owner=owner,
            name=entry['name'],
            active=entry.get('active', False),
            query_template=entry.get('query_template', ''),
            query_template_json=entry.get('query_template_json') or {},
            tags=entry.get('tags', []),
            config=entry.get('config') or {},
        )
        assert check_scope(provider) is None, name


def test_the_three_provider_files_agree_on_the_backstage_tag():
    """preloaded.json is a copy; the copies must not drift apart."""
    loaded = {}
    for path in PROVIDER_FILES:
        with open(path) as handle:
            for entry in json.load(handle):
                if entry['name'] in BACKSTAGE_FEDERATED:
                    loaded.setdefault(entry['name'], []).append(
                        (path, tuple(sorted(entry['tags']))))

    for name, seen in loaded.items():
        tag_sets = {tags for _path, tags in seen}
        assert len(tag_sets) == 1, (name, seen)
