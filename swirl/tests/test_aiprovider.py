"""
Unit tests for the AIProvider model, serializers, REST API, and AIProviderFactory.

Run with:  pytest swirl/tests/test_aiprovider.py -v
"""

import pytest
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

from rest_framework.test import APIClient

from swirl.models import AIProvider
from swirl.serializers import AIProviderSerializer, AIProviderNoCredentialsSerializer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _aiprovider_perms():
    ct = ContentType.objects.get_for_model(AIProvider)
    return list(Permission.objects.filter(content_type=ct))


def _give_all_perms(user):
    """Add all AIProvider permissions then return a fresh DB instance to clear
    Django's per-object permission cache."""
    for perm in _aiprovider_perms():
        user.user_permissions.add(perm)
    return User.objects.get(pk=user.pk)


# ---------------------------------------------------------------------------
# Shared fixtures (used by both TestCase classes and @pytest.mark.django_db fns)
# ---------------------------------------------------------------------------

@pytest.fixture
def superuser(db):
    try:
        return User.objects.get(username='aip_admin')
    except ObjectDoesNotExist:
        return User.objects.create_user(
            username='aip_admin', password='password',
            is_staff=True, is_superuser=True,
        )


@pytest.fixture
def regular_user(db):
    """Non-superuser with all AIProvider permissions (re-fetched to clear perm cache)."""
    try:
        u = User.objects.get(username='aip_user')
    except ObjectDoesNotExist:
        u = User.objects.create_user(username='aip_user', password='password')
    return _give_all_perms(u)


@pytest.fixture
def other_user(db):
    """Another permissioned non-superuser — different owner than openai_provider."""
    try:
        u = User.objects.get(username='aip_other')
    except ObjectDoesNotExist:
        u = User.objects.create_user(username='aip_other', password='password')
    return _give_all_perms(u)


@pytest.fixture
def openai_provider(db, superuser):
    return AIProvider.objects.create(
        name='OpenAI GPT-4o',
        owner=superuser,
        shared=True,
        active=True,
        api_key='sk-test-key',
        model='gpt-4o',
        config={'family': 'openai'},
        tags=['chat', 'rag', 'query', 'connector'],
        defaults=['chat', 'rag', 'query', 'connector'],
    )


@pytest.fixture
def anthropic_provider(db, superuser):
    return AIProvider.objects.create(
        name='Anthropic Claude',
        owner=superuser,
        shared=True,
        active=True,
        api_key='sk-ant-key',
        model='anthropic/claude-3-5-sonnet-20241022',
        config={'family': 'anthropic', 'max_tokens': 170000},
        tags=['chat', 'rag', 'query', 'connector'],
        defaults=[],
    )


@pytest.fixture
def spacy_provider(db, superuser):
    return AIProvider.objects.create(
        name='spaCy',
        owner=superuser,
        shared=True,
        active=True,
        api_key='',
        model='',
        config={},
        tags=['reader'],
        defaults=['reader'],
    )


@pytest.fixture
def inactive_provider(db, superuser):
    return AIProvider.objects.create(
        name='Inactive Model',
        owner=superuser,
        shared=True,
        active=False,
        api_key='sk-inactive',
        model='gpt-3.5-turbo',
        config={},
        tags=['chat'],
        defaults=['chat'],
    )


# ===========================================================================
# MODEL TESTS
# ===========================================================================

@pytest.mark.django_db
class AIProviderModelTests(TestCase):

    @pytest.fixture(autouse=True)
    def _inject(self, superuser):
        self.superuser = superuser

    def _make(self, **kwargs):
        defaults = dict(
            name='Test Provider',
            owner=self.superuser,
            active=True,
            api_key='sk-test',
            model='gpt-4o',
            config={},
            tags=['chat'],
            defaults=['chat'],
        )
        defaults.update(kwargs)
        return AIProvider.objects.create(**defaults)

    def test_str_returns_name(self):
        p = self._make(name='My Provider')
        assert str(p) == 'My Provider'

    def test_shared_defaults_to_true(self):
        p = self._make()
        assert p.shared is True

    def test_active_defaults_to_true(self):
        p = self._make()
        assert p.active is True

    def test_tags_and_defaults_stored_as_lists(self):
        p = self._make(tags=['chat', 'rag'], defaults=['rag'])
        assert p.tags == ['chat', 'rag']
        assert p.defaults == ['rag']

    def test_get_family_from_config(self):
        p = self._make(config={'family': 'anthropic'})
        assert p.get_family() == 'anthropic'

    def test_get_family_lowercased(self):
        p = self._make(config={'family': 'OpenAI'})
        assert p.get_family() == 'openai'

    def test_get_family_falls_back_to_name_when_config_missing(self):
        p = self._make(name='SomeBrand', config={})
        assert p.get_family() == 'somebrand'

    def test_config_default_is_empty_dict(self):
        p = self._make(config={})
        assert p.config == {}

    def test_prompt_overrides_default_is_empty_dict(self):
        p = self._make()
        assert p.prompt_overrides == {}

    def test_date_fields_set_on_create(self):
        p = self._make()
        assert p.date_created is not None
        assert p.date_updated is not None

    def test_empty_api_key_allowed(self):
        p = self._make(api_key='')
        assert p.api_key == ''

    def test_empty_model_allowed(self):
        p = self._make(model='')
        assert p.model == ''


# ===========================================================================
# SERIALIZER TESTS
# ===========================================================================

@pytest.mark.django_db
class AIProviderSerializerTests(TestCase):

    @pytest.fixture(autouse=True)
    def _inject(self, superuser, openai_provider):
        self.superuser = superuser
        self.provider = openai_provider

    def test_full_serializer_includes_api_key(self):
        data = AIProviderSerializer(self.provider).data
        assert 'api_key' in data

    def test_no_credentials_serializer_omits_api_key(self):
        data = AIProviderNoCredentialsSerializer(self.provider).data
        assert 'api_key' not in data

    def test_no_credentials_serializer_includes_core_fields(self):
        data = AIProviderNoCredentialsSerializer(self.provider).data
        for field in ('id', 'name', 'owner', 'active', 'model', 'config', 'tags', 'defaults'):
            assert field in data, f"expected field '{field}' missing"

    def test_create_via_serializer(self):
        payload = {
            'name': 'New Provider',
            'active': True,
            'api_key': 'sk-new',
            'model': 'gpt-4o-mini',
            'config': {},
            'tags': ['chat'],
            'defaults': [],
        }
        s = AIProviderSerializer(data=payload)
        assert s.is_valid(), s.errors
        obj = s.save(owner=self.superuser)
        assert obj.pk is not None
        assert obj.model == 'gpt-4o-mini'

    def test_update_blank_api_key_preserves_existing_value(self):
        original_key = self.provider.api_key
        s = AIProviderSerializer(
            instance=self.provider,
            data={
                'name': self.provider.name, 'active': True,
                'api_key': '',  # intentionally blank
                'model': 'gpt-4o', 'config': {}, 'tags': ['chat'], 'defaults': [],
            },
            partial=True,
        )
        assert s.is_valid(), s.errors
        updated = s.save(owner=self.superuser)
        assert updated.api_key == original_key

    def test_update_new_api_key_replaces_existing(self):
        s = AIProviderSerializer(
            instance=self.provider,
            data={
                'name': self.provider.name, 'active': True,
                'api_key': 'sk-replacement',
                'model': 'gpt-4o', 'config': {}, 'tags': ['chat'], 'defaults': [],
            },
            partial=True,
        )
        assert s.is_valid(), s.errors
        updated = s.save(owner=self.superuser)
        assert updated.api_key == 'sk-replacement'

    def test_missing_name_fails_validation(self):
        """name is a required CharField with no default."""
        payload = {'model': 'gpt-4o', 'api_key': '', 'config': {}, 'defaults': [], 'tags': ['chat']}
        s = AIProviderSerializer(data=payload)
        assert not s.is_valid()
        assert 'name' in s.errors


# ===========================================================================
# API / VIEWSET TESTS
# ===========================================================================

@pytest.mark.django_db
class AIProviderAPITests(TestCase):

    LIST_URL = '/swirl/aiproviders/'

    @pytest.fixture(autouse=True)
    def _inject(self, superuser, regular_user, other_user, openai_provider):
        self._client = APIClient()
        self._superuser = superuser
        self._regular_user = regular_user   # fresh DB instance, perms assigned
        self._other_user = other_user       # fresh DB instance, perms assigned
        self._provider = openai_provider
        self._detail_url = f'/swirl/aiproviders/{openai_provider.pk}/'

    # --- list ---

    def test_list_requires_authentication(self):
        resp = self._client.get(self.LIST_URL)
        assert resp.status_code in (401, 403)

    def test_list_superuser_sees_api_key(self):
        self._client.force_authenticate(user=self._superuser)
        resp = self._client.get(self.LIST_URL)
        assert resp.status_code == 200
        results = resp.json()
        if isinstance(results, dict):
            results = results.get('results', results.get('data', []))
        assert any('api_key' in r for r in results)

    def test_list_regular_user_no_api_key(self):
        self._client.force_authenticate(user=self._regular_user)
        resp = self._client.get(self.LIST_URL)
        assert resp.status_code == 200
        results = resp.json()
        if isinstance(results, dict):
            results = results.get('results', results.get('data', []))
        assert all('api_key' not in r for r in results)

    # --- create ---

    def test_create_by_superuser_succeeds(self):
        self._client.force_authenticate(user=self._superuser)
        payload = {
            'name': 'Created Provider',
            'active': True,
            'api_key': 'sk-create',
            'model': 'gpt-4o-mini',
            'config': {},
            'tags': ['chat'],
            'defaults': [],
        }
        resp = self._client.post(self.LIST_URL, payload, format='json')
        assert resp.status_code == 201
        assert resp.json()['name'] == 'Created Provider'

    def test_create_anonymous_forbidden(self):
        payload = {'name': 'X', 'model': 'y', 'tags': ['chat'], 'defaults': [], 'config': {}}
        resp = self._client.post(self.LIST_URL, payload, format='json')
        assert resp.status_code in (401, 403)

    def test_create_superuser_auto_sets_shared_true(self):
        self._client.force_authenticate(user=self._superuser)
        payload = {
            'name': 'Auto Shared',
            'active': True,
            'api_key': 'sk-x',
            'model': 'gpt-4o',
            'config': {},
            'tags': ['chat'],
            'defaults': [],
            'shared': False,  # viewset should override to True for superusers
        }
        resp = self._client.post(self.LIST_URL, payload, format='json')
        assert resp.status_code == 201
        assert AIProvider.objects.get(name='Auto Shared').shared is True

    # --- retrieve ---

    def test_retrieve_owner_gets_api_key(self):
        self._client.force_authenticate(user=self._superuser)
        resp = self._client.get(self._detail_url)
        assert resp.status_code == 200
        assert 'api_key' in resp.json()

    def test_retrieve_non_owner_no_api_key(self):
        self._client.force_authenticate(user=self._regular_user)
        resp = self._client.get(self._detail_url)
        assert resp.status_code == 200
        assert 'api_key' not in resp.json()

    def test_retrieve_nonexistent_returns_404(self):
        self._client.force_authenticate(user=self._superuser)
        resp = self._client.get('/swirl/aiproviders/99999/')
        assert resp.status_code == 404

    # --- update ---

    def test_update_by_owner_succeeds(self):
        self._client.force_authenticate(user=self._superuser)
        resp = self._client.patch(
            self._detail_url,
            {'model': 'gpt-4o-updated', 'tags': ['chat'], 'defaults': [], 'config': {}},
            format='json',
        )
        assert resp.status_code == 200
        self._provider.refresh_from_db()
        assert self._provider.model == 'gpt-4o-updated'

    def test_update_by_non_owner_returns_403(self):
        # other_user has the permission but doesn't own openai_provider
        self._client.force_authenticate(user=self._other_user)
        resp = self._client.patch(
            self._detail_url,
            {'model': 'hack'},
            format='json',
        )
        # Viewset checks owner filter; non-owner gets 404
        assert resp.status_code in (403, 404)

    def test_patch_blank_api_key_preserves_stored_value(self):
        self._client.force_authenticate(user=self._superuser)
        original_key = self._provider.api_key
        resp = self._client.patch(
            self._detail_url,
            {'api_key': '', 'tags': ['chat'], 'defaults': [], 'config': {}},
            format='json',
        )
        assert resp.status_code == 200
        self._provider.refresh_from_db()
        assert self._provider.api_key == original_key

    # --- destroy ---

    def test_destroy_by_owner_succeeds(self):
        self._client.force_authenticate(user=self._superuser)
        resp = self._client.delete(self._detail_url)
        assert resp.status_code == 204
        assert not AIProvider.objects.filter(pk=self._provider.pk).exists()

    def test_destroy_by_non_owner_blocked(self):
        self._client.force_authenticate(user=self._other_user)
        resp = self._client.delete(self._detail_url)
        assert resp.status_code in (403, 404)
        assert AIProvider.objects.filter(pk=self._provider.pk).exists()


# ===========================================================================
# AIProviderFactory TESTS
#
# Use @pytest.mark.django_db (function scope) so each test gets its own
# rolled-back transaction — avoids fixture accumulation issues inside TestCase.
# ===========================================================================

def _make_provider(owner, **kwargs):
    """Helper: build an AIProvider with sensible defaults."""
    defaults = dict(
        owner=owner, shared=True, active=True, api_key='sk-x',
        model='gpt-4o', config={'family': 'openai'},
        tags=['chat'], defaults=['chat'],
    )
    defaults.update(kwargs)
    return AIProvider.objects.create(**defaults)


def _factory():
    from swirl.ai_provider import AIProviderFactory
    return AIProviderFactory()


@pytest.mark.django_db
def test_factory_returns_none_when_no_active_providers(superuser):
    _make_provider(superuser, active=False)
    assert _factory().alloc_ai_provider('chat', options={'unit_test': True}) is None


@pytest.mark.django_db
def test_factory_returns_none_for_unknown_tag(superuser):
    _make_provider(superuser)
    assert _factory().alloc_ai_provider('nonexistent_tag', options={'unit_test': True}) is None


@pytest.mark.django_db
def test_factory_inactive_provider_not_selected(superuser):
    _make_provider(superuser, active=False, tags=['chat'], defaults=['chat'])
    assert _factory().alloc_ai_provider('chat', options={'unit_test': True}) is None


@pytest.mark.django_db
def test_factory_default_candidate_selected_over_tag_only(superuser):
    """Provider with 'chat' in defaults beats one with 'chat' in tags only."""
    default_p = _make_provider(
        superuser, name='Default', model='gpt-4o',
        config={'family': 'openai'}, tags=['chat'], defaults=['chat'],
    )
    _make_provider(
        superuser, name='TagOnly', model='gpt-4o-mini',
        config={'family': 'openai'}, tags=['chat'], defaults=[],
    )
    with patch('swirl.ai_provider.litellm'):
        factory = _factory()
        factory.alloc_ai_provider('chat', options={'unit_test': True})
    assert factory.provider.name == 'Default'


@pytest.mark.django_db
def test_factory_tag_only_selected_when_no_default(superuser):
    """When no default exists for a tag, a tag-only candidate is used."""
    _make_provider(
        superuser, name='TagOnly', model='gpt-4o-mini',
        config={'family': 'openai'}, tags=['chat'], defaults=[],
    )
    with patch('swirl.ai_provider.litellm'):
        factory = _factory()
        result = factory.alloc_ai_provider('chat', options={'unit_test': True})
    assert result is not None
    assert factory.provider.name == 'TagOnly'


@pytest.mark.django_db
def test_factory_provider_id_override_selects_specific_provider(superuser):
    default_p = _make_provider(
        superuser, name='Default', model='gpt-4o',
        config={'family': 'openai'}, tags=['chat'], defaults=['chat'],
    )
    other_p = _make_provider(
        superuser, name='Anthropic', model='anthropic/claude-3-5-sonnet',
        config={'family': 'anthropic'}, tags=['chat'], defaults=[],
    )
    with patch('swirl.ai_provider.litellm'):
        factory = _factory()
        factory.alloc_ai_provider(
            'chat', options={'unit_test': True}, provider_id=other_p.pk,
        )
    assert factory.provider.name == 'Anthropic'


@pytest.mark.django_db
def test_factory_provider_id_ignored_when_tag_missing(superuser):
    """provider_id for a provider lacking the tag falls back to the default."""
    default_p = _make_provider(
        superuser, name='Default', model='gpt-4o',
        config={'family': 'openai'}, tags=['chat'], defaults=['chat'],
    )
    reader_p = _make_provider(
        superuser, name='spaCy', model='',
        config={}, tags=['reader'], defaults=['reader'],
    )
    with patch('swirl.ai_provider.litellm'):
        factory = _factory()
        factory.alloc_ai_provider(
            'chat', options={'unit_test': True}, provider_id=reader_p.pk,
        )
    assert factory.provider.name == 'Default'


@pytest.mark.django_db
def test_factory_spacy_selected_for_reader_tag(superuser):
    from swirl.ai_provider import LLMWrapper
    _make_provider(
        superuser, name='spaCy', api_key='', model='',
        config={}, tags=['reader'], defaults=['reader'],
    )
    with patch('swirl.ai_provider.get_spacy_nlp', return_value=MagicMock()):
        factory = _factory()
        result = factory.alloc_ai_provider('reader', options={'unit_test': True})
    assert isinstance(result, LLMWrapper)
    assert factory.provider.name == 'spaCy'


@pytest.mark.django_db
def test_factory_fallback_list_contains_same_family_provider(superuser):
    _make_provider(
        superuser, name='OpenAI Primary', model='gpt-4o',
        config={'family': 'openai'}, tags=['chat'], defaults=['chat'],
    )
    _make_provider(
        superuser, name='OpenAI Fallback', model='gpt-4o-mini',
        config={'family': 'openai'}, tags=['chat'], defaults=[],
    )
    with patch('swirl.ai_provider.litellm'):
        factory = _factory()
        factory.alloc_ai_provider('chat', options={'unit_test': True})
    assert any(f.get('model') == 'gpt-4o-mini' for f in factory.fallback_list)


@pytest.mark.django_db
def test_factory_fallback_excludes_different_family(superuser):
    _make_provider(
        superuser, name='OpenAI', model='gpt-4o',
        config={'family': 'openai'}, tags=['chat'], defaults=['chat'],
    )
    _make_provider(
        superuser, name='Anthropic', model='anthropic/claude-3-5-sonnet',
        config={'family': 'anthropic'}, tags=['chat'], defaults=[],
    )
    with patch('swirl.ai_provider.litellm'):
        factory = _factory()
        factory.alloc_ai_provider('chat', options={'unit_test': True})
    assert not any(f.get('model') == 'anthropic/claude-3-5-sonnet' for f in factory.fallback_list)


@pytest.mark.django_db
def test_factory_cross_family_fallback_includes_other_families(superuser):
    _make_provider(
        superuser, name='OpenAI', model='gpt-4o',
        config={'family': 'openai', 'cross_family_fallback': True},
        tags=['chat'], defaults=['chat'],
    )
    _make_provider(
        superuser, name='Anthropic', model='anthropic/claude-3-5-sonnet',
        config={'family': 'anthropic'}, tags=['chat'], defaults=[],
    )
    with patch('swirl.ai_provider.litellm'):
        factory = _factory()
        factory.alloc_ai_provider('chat', options={'unit_test': True})
    assert any(f.get('model') == 'anthropic/claude-3-5-sonnet' for f in factory.fallback_list)


@pytest.mark.django_db
def test_factory_primary_not_in_fallback_list(superuser):
    primary = _make_provider(
        superuser, name='OpenAI Primary', api_key='sk-primary', model='gpt-4o',
        config={'family': 'openai'}, tags=['chat'], defaults=['chat'],
    )
    _make_provider(
        superuser, name='OpenAI Fallback', api_key='sk-fallback', model='gpt-4o-mini',
        config={'family': 'openai'}, tags=['chat'], defaults=[],
    )
    with patch('swirl.ai_provider.litellm'):
        factory = _factory()
        factory.alloc_ai_provider('chat', options={'unit_test': True})
    # Primary's api_key must not appear in the fallback list
    assert not any(f.get('api_key') == 'sk-primary' for f in factory.fallback_list)


@pytest.mark.django_db
def test_factory_shared_provider_visible_to_any_owner(superuser):
    _make_provider(superuser, shared=True, tags=['chat'], defaults=['chat'])
    any_user = User.objects.create_user(username='stranger', password='pw')
    with patch('swirl.ai_provider.litellm'):
        result = _factory().alloc_ai_provider('chat', owner=any_user)
    assert result is not None


@pytest.mark.django_db
def test_factory_private_provider_not_visible_to_other_owner(superuser):
    _make_provider(superuser, shared=False, tags=['chat'], defaults=['chat'])
    other = User.objects.create_user(username='outsider', password='pw')
    result = _factory().alloc_ai_provider('chat', owner=other)
    assert result is None


@pytest.mark.django_db
def test_factory_returns_llm_wrapper_instance(superuser):
    from swirl.ai_provider import LLMWrapper
    _make_provider(superuser, tags=['chat'], defaults=['chat'])
    with patch('swirl.ai_provider.litellm'):
        result = _factory().alloc_ai_provider('chat', options={'unit_test': True})
    assert isinstance(result, LLMWrapper)


@pytest.mark.django_db
def test_factory_llm_wrapper_get_provider_returns_selected(superuser):
    _make_provider(superuser, name='My Model', tags=['chat'], defaults=['chat'])
    with patch('swirl.ai_provider.litellm'):
        factory = _factory()
        result = factory.alloc_ai_provider('chat', options={'unit_test': True})
    assert result.get_provider().name == 'My Model'


# ===========================================================================
# LLMWrapper.get_encoding_model tests
#
# Regression coverage for DS-5598: rag.py calls self.client.get_encoding_model()
# during background_process(). Before the fix this raised AttributeError on
# LLMWrapper, breaking /api/swirl/sapi/detail-search-rag/ with a 500.
# ===========================================================================

def _alloc_wrapper(superuser, model):
    _make_provider(superuser, name=f'Provider-{model}', model=model,
                   tags=['rag'], defaults=['rag'])
    with patch('swirl.ai_provider.litellm'):
        return _factory().alloc_ai_provider('rag', options={'unit_test': True})


@pytest.mark.django_db
def test_llmwrapper_get_encoding_model_known_openai_model(superuser):
    wrapper = _alloc_wrapper(superuser, 'gpt-4o')
    assert wrapper.get_encoding_model() == 'gpt-4o'


@pytest.mark.django_db
def test_llmwrapper_get_encoding_model_strips_known_provider_prefix(superuser):
    wrapper = _alloc_wrapper(superuser, 'azure/gpt-4o')
    assert wrapper.get_encoding_model() == 'gpt-4o'


@pytest.mark.django_db
def test_llmwrapper_get_encoding_model_falls_back_for_unknown_model(superuser):
    wrapper = _alloc_wrapper(superuser, 'anthropic/claude-3-5-sonnet-20241022')
    assert wrapper.get_encoding_model() == 'gpt-4o'


@pytest.mark.django_db
def test_llmwrapper_get_encoding_model_falls_back_for_arbitrary_deployment(superuser):
    wrapper = _alloc_wrapper(superuser, 'azure/my-custom-deployment')
    assert wrapper.get_encoding_model() == 'gpt-4o'


@pytest.mark.django_db
def test_llmwrapper_get_encoding_model_handles_empty_model(superuser):
    _make_provider(superuser, name='NoModel', model='', config={'family': 'openai'},
                   tags=['rag'], defaults=['rag'])
    with patch('swirl.ai_provider.litellm'):
        wrapper = _factory().alloc_ai_provider('rag', options={'unit_test': True})
    assert wrapper.get_encoding_model() == 'gpt-4o'
