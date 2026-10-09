"""
Regression tests for StackNMixer with no results, or more providers than results_requested.

Run with:  pytest swirl/tests/test_stack_mixer.py -v
"""

from swirl.mixers.stack import StackNMixer


def _make_mixer(results_requested, providers, per_provider):
    mixer = StackNMixer.__new__(StackNMixer)
    mixer.results_requested = results_requested
    mixer.results_needed = results_requested
    mixer.stack = 0
    mixer.all_results = [
        {'searchprovider': f'P{p}', 'searchprovider_rank': r + 1, 'swirl_score': 100 - p - r}
        for p in range(providers) for r in range(per_provider)
    ]
    return mixer


def test_stack_n_mixer_no_results():
    """No results must give an empty page, not ZeroDivisionError."""
    mixer = _make_mixer(10, 0, 0)
    mixer.order()
    assert mixer.mixed_results == []


def test_stack_n_mixer_more_providers_than_results_requested():
    """5 providers with results_requested=3 must still fill the page."""
    mixer = _make_mixer(3, 5, 4)
    mixer.order()
    assert len(mixer.mixed_results) == 3
