"""
A processor entry of the form "<name>.<type>" names a stored QueryTransform.
The lookup gives a user the transforms the API would list for them: their own
and shared ones. A SearchProvider's entry may also name a transform that
belongs to the provider's owner.
"""

import pytest
from django.contrib.auth.models import Permission, User

from swirl.models import QueryTransform
from swirl.processors.transform_query_processor_utils import (
    get_pre_query_processor_or_transform,
    get_query_processor_or_transform,
)

RULES = 'alpha; beta'


def user(name):
    account = User.objects.create_user(name, f'{name}@example.com', 'not-a-real-password')
    account.user_permissions.set(Permission.objects.filter(
        content_type__app_label='swirl', codename='view_querytransform'))
    return User.objects.get(pk=account.pk)


def transform(name, owner, shared=False):
    return QueryTransform.objects.create(
        name=name, owner=owner, shared=shared, qrx_type='rewrite', config_content=RULES)


@pytest.mark.django_db
class TestSearchLevelLookup:

    def test_own_transform_is_found(self):
        alice = user('lookup_alice')
        transform('mine', alice)

        assert get_pre_query_processor_or_transform('mine.rewrite', 'alpha', None, alice) is not None

    def test_shared_transform_is_found(self):
        alice, bob = user('lookup_alice'), user('lookup_bob')
        transform('common', alice, shared=True)

        assert get_pre_query_processor_or_transform('common.rewrite', 'alpha', None, bob) is not None

    def test_another_users_private_transform_is_not_found(self):
        alice, bob = user('lookup_alice'), user('lookup_bob')
        transform('private', alice)

        with pytest.raises(Exception):
            get_pre_query_processor_or_transform('private.rewrite', 'alpha', None, bob)


@pytest.mark.django_db
class TestProviderLevelLookup:

    def test_provider_owners_private_transform_is_found(self):
        alice, bob = user('lookup_alice'), user('lookup_bob')
        transform('providers', alice)

        found = get_query_processor_or_transform(
            'providers.rewrite', 'alpha', None, None, bob, provider_owner=alice)

        assert found is not None

    def test_a_third_users_private_transform_is_not_found(self):
        alice, bob, carol = user('lookup_alice'), user('lookup_bob'), user('lookup_carol')
        transform('thirdparty', carol)

        with pytest.raises(Exception):
            get_query_processor_or_transform(
                'thirdparty.rewrite', 'alpha', None, None, bob, provider_owner=alice)
