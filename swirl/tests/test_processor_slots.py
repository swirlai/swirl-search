"""
A search names its processors: in stored configuration and, for the pre-query
slot, in the request. Each slot resolves a name only to a processor class of
its own kind.
"""

import pytest
from django.contrib.auth.models import User

from swirl.models import Result, Search
from swirl.processors import alloc_processor
from swirl.processors.processor import PostResultProcessor, QueryProcessor, ResultProcessor
from swirl.processors.transform_query_processor_utils import (
    get_pre_query_processor_or_transform, get_query_processor_or_transform)


class TestAllocProcessor:

    def test_a_processor_name_resolves_to_its_class(self):
        assert alloc_processor('AdaptiveQueryProcessor').__name__ == 'AdaptiveQueryProcessor'

    @pytest.mark.parametrize('name, kind', [
        ('AdaptiveQueryProcessor', QueryProcessor),
        ('MappingResultProcessor', ResultProcessor),
        ('CosineRelevancyPostResultProcessor', PostResultProcessor),
    ])
    def test_a_processor_of_the_right_kind_is_accepted(self, name, kind):
        assert issubclass(alloc_processor(name, kind=kind), kind)

    @pytest.mark.parametrize('name, kind', [
        ('DropIrrelevantPostResultProcessor', QueryProcessor),
        ('CosineRelevancyPostResultProcessor', ResultProcessor),
        ('AdaptiveQueryProcessor', PostResultProcessor),
        ('MappingResultProcessor', QueryProcessor),
    ])
    def test_a_processor_of_another_kind_is_refused_like_an_unknown_name(self, name, kind):
        with pytest.raises(KeyError):
            alloc_processor(name, kind=kind)

    @pytest.mark.parametrize('name', ['Search', 'SearchProvider', 'logger', 'alloc_processor', 'Processor0'])
    def test_a_name_that_is_not_a_processor_is_refused(self, name):
        with pytest.raises(KeyError):
            alloc_processor(name)

    def test_a_blank_name_still_returns_nothing(self):
        assert alloc_processor('') is None


@pytest.mark.django_db
class TestPreQuerySlot:

    @pytest.fixture
    def stored(self):
        """A finished search of one user, with one stored result item."""
        owner = User.objects.create_user('slot_owner', 'slot_owner@example.com', 'not-a-real-password')
        search = Search.objects.create(owner=owner, query_string='x', status='FULL_RESULTS_READY')
        return Result.objects.create(
            owner=owner, search_id=search, provider_id=1, searchprovider='p',
            query_string_to_provider='x', query_to_provider='x', status='READY',
            retrieved=1, found=1, time=0.0,
            json_results=[{'title': 't', 'body': 'b', 'swirl_score': 1}])

    def test_a_post_result_processor_named_in_the_pre_query_slot_is_refused(self, stored):
        caller = User.objects.create_user('slot_caller', 'slot_caller@example.com', 'not-a-real-password')

        with pytest.raises(KeyError):
            get_pre_query_processor_or_transform(
                'DropIrrelevantPostResultProcessor', str(stored.search_id_id), ['x'], caller)

        assert len(Result.objects.get(pk=stored.pk).json_results) == 1

    def test_the_provider_query_slot_refuses_it_too(self, stored):
        with pytest.raises(KeyError):
            get_query_processor_or_transform(
                'DropIrrelevantPostResultProcessor', str(stored.search_id_id), '', ['x'], None)

    def test_a_query_processor_still_runs_in_the_pre_query_slot(self):
        processor = get_pre_query_processor_or_transform('AdaptiveQueryProcessor', 'some words', [], None)

        assert isinstance(processor, QueryProcessor)
