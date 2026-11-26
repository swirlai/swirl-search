"""
The expirer deletes searches whose retention period has passed. It runs over
every user's searches, so one search it cannot handle must not stop the rest.
"""

from datetime import timedelta
from unittest import mock

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from swirl import expirer as expirer_module
from swirl.expirer import expirer
from swirl.models import Search


@pytest.fixture
def owner(db):
    return User.objects.create_user('expiry_owner', 'expiry_owner@example.com', 'not-a-real-password')


def search_aged(owner, retention, **age):
    search = Search.objects.create(owner=owner, query_string='q', retention=retention, status='FULL_RESULTS_READY')
    Search.objects.filter(pk=search.pk).update(date_updated=timezone.now() - timedelta(**age))
    return search


def exists(search):
    return Search.objects.filter(pk=search.pk).exists()


@pytest.mark.parametrize('retention, too_young, old_enough', [
    (1, {'minutes': 50}, {'minutes': 70}),
    (2, {'hours': 23}, {'hours': 25}),
    (3, {'days': 29}, {'days': 31}),
])
def test_each_retention_period_is_applied(owner, retention, too_young, old_enough):
    kept = search_aged(owner, retention, **too_young)
    due = search_aged(owner, retention, **old_enough)

    assert expirer() is True

    assert exists(kept)
    assert not exists(due)


def test_a_search_that_never_expires_is_kept(owner):
    kept = search_aged(owner, 0, days=400)

    expirer()

    assert exists(kept)


def test_a_one_month_search_does_not_stop_expiry_of_other_users_searches(owner):
    other = User.objects.create_user('expiry_other', 'expiry_other@example.com', 'not-a-real-password')
    search_aged(other, 3, minutes=1)
    due = search_aged(owner, 1, hours=2)

    assert expirer() is True

    assert not exists(due)


def test_an_unknown_retention_value_is_left_alone(owner):
    odd = search_aged(owner, 9, days=400)
    due = search_aged(owner, 1, hours=2)

    assert expirer() is True

    assert exists(odd)
    assert not exists(due)


def test_a_search_that_cannot_be_processed_does_not_stop_the_run(owner):
    first = search_aged(owner, 1, hours=3)
    second = search_aged(owner, 1, hours=2)
    real = expirer_module.expire_if_due
    failing = {first.pk, second.pk} - {min(first.pk, second.pk)}

    def sometimes_fails(search):
        if search.pk in failing:
            raise RuntimeError('cannot process this one')
        return real(search)

    with mock.patch.object(expirer_module, 'expire_if_due', side_effect=sometimes_fails):
        assert expirer() is True

    assert sum(exists(s) for s in (first, second)) == 1
