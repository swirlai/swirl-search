"""
Basic analytics helpers for the SWIRL admin analytics page.

Three metrics only:
  1. searches_by_day   — daily search volume for the last 30 days
  2. top_providers     — most-used SearchProviders (by appearance in
                         Search.searchprovider_list) in the same window
  3. futile_searches   — searches that completed but returned no results

Cross-DB portable: everything goes through the Django ORM or Python-side
iteration. No raw SQL, no JSON functions that differ between SQLite and
Postgres.
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Any

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone


WINDOW_DAYS = 30

# Statuses that count as "completed but empty" (futile)
FUTILE_STATUSES = {'FULL_RESULTS_READY', 'PARTIAL_RESULTS_READY',
                   'FULL_UPDATE_READY',  'PARTIAL_UPDATE_READY'}


def _window():
    """Return (since, until) for the default 30-day window."""
    until = timezone.now()
    since = until - timedelta(days=WINDOW_DAYS)
    return since, until


def searches_by_day(since=None, until=None) -> list[dict[str, Any]]:
    """
    Return a list of {'day': date, 'count': int} dicts, one per day in the
    window that had at least one search, ordered oldest-first.
    """
    from swirl.models import Search
    if since is None or until is None:
        since, until = _window()
    rows = (
        Search.objects
        .filter(date_created__range=(since, until))
        .annotate(day=TruncDate('date_created'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    return list(rows)


def top_providers(since=None, until=None, limit: int = 10) -> list[tuple[str, int]]:
    """
    Return [(provider_name, count), ...] sorted descending.

    searchprovider_list is a JSONField storing provider IDs (integers or
    strings). We aggregate in Python to stay portable across SQLite/Postgres.
    """
    from swirl.models import Search, SearchProvider
    if since is None or until is None:
        since, until = _window()

    id_to_name: dict[int, str] = dict(SearchProvider.objects.values_list('id', 'name'))
    counter: Counter[int] = Counter()

    qs = (
        Search.objects
        .filter(date_created__range=(since, until))
        .values_list('searchprovider_list', flat=True)
    )
    for sp_list in qs.iterator(chunk_size=2000):
        if not sp_list:
            continue
        for sp_id in sp_list:
            try:
                counter[int(sp_id)] += 1
            except (TypeError, ValueError):
                pass

    return [
        (id_to_name.get(sp_id, f'provider#{sp_id}'), count)
        for sp_id, count in counter.most_common(limit)
    ]


def futile_searches(since=None, until=None, limit: int = 20) -> list[dict[str, Any]]:
    """
    Return searches that completed (FULL/PARTIAL_RESULTS_READY) but for which
    all associated Result rows have retrieved=0, meaning no content came back.

    Returns a list of dicts: [{'query': str, 'owner': str, 'date': datetime}, ...]
    """
    from swirl.models import Result, Search
    if since is None or until is None:
        since, until = _window()

    # Gather search IDs that returned at least one result row with retrieved > 0
    nonempty_search_ids = set(
        Result.objects
        .filter(search_id__date_created__range=(since, until), retrieved__gt=0)
        .values_list('search_id_id', flat=True)
        .distinct()
    )

    futile_qs = (
        Search.objects
        .filter(date_created__range=(since, until), status__in=FUTILE_STATUSES)
        .exclude(id__in=nonempty_search_ids)
        .select_related('owner')
        .order_by('-date_created')[:limit]
    )

    return [
        {
            'query': s.query_string,
            'owner': s.owner.username if s.owner else '—',
            'date':  s.date_created,
            'status': s.status,
        }
        for s in futile_qs
    ]
