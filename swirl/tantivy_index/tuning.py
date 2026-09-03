'''
Tuning for the SWIRL Tantivy index (TECH_DESIGN section 3.1).

The dataclass has the same shape as the Backstage app-config
``search.swirl.tuning`` block (TECH_DESIGN section 2.2). It is persisted at
``<data_dir>/tuning.json`` and applied on the next ``begin``, because changing
the n-gram bounds or the stemmer requires a reindex.

No Django imports here on purpose: the gate-zero gauntlet imports this module
standalone.
'''

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field, fields

TUNING_FILENAME = 'tuning.json'


@dataclass
class Tuning:
    '''The tuning surface from TECH_DESIGN 2.2, carrying the design defaults.'''

    title_exact_boost: float = 3.0
    title_ngram_boost: float = 1.0
    text_boost: float = 1.0
    phrase_boost_multiplier: float = 2.0
    ngram_min: int = 3
    ngram_max: int = 8
    stemmer: str = 'english'
    stopwords_language: str = 'english'
    extra_stopwords: list = field(default_factory=list)
    fuzzy_enabled: bool = False
    fuzzy_distance: int = 1
    remove_long: int = 64
    highlight: bool = True
    snippet_chars: int = 300

    @property
    def field_boosts(self) -> dict:
        return {
            'title_exact': self.title_exact_boost,
            'title_ngram': self.title_ngram_boost,
            'text': self.text_boost,
        }

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def field_names(cls) -> list:
        return [f.name for f in fields(cls)]

    @classmethod
    def from_dict(cls, data) -> 'Tuning':
        '''Build a Tuning from a partial dict, ignoring unknown keys.

        Raises ValueError when a known key carries a value of the wrong type or
        an out-of-range value, so the config endpoint can answer 400.
        '''
        data = data or {}
        if not isinstance(data, dict):
            raise ValueError('tuning must be a JSON object')
        known = {f.name: f for f in fields(cls)}
        kwargs = {}
        for key, value in data.items():
            if key not in known:
                continue
            kwargs[key] = _coerce(key, value)
        tuning = cls(**kwargs)
        tuning.validate()
        return tuning

    def validate(self):
        if not isinstance(self.extra_stopwords, (list, tuple)):
            raise ValueError('extra_stopwords must be a list of strings')
        normalised = []
        for word in self.extra_stopwords:
            if not isinstance(word, str):
                raise ValueError('extra_stopwords must be a list of strings')
            normalised.append(word.lower())
        self.extra_stopwords = normalised
        if self.ngram_min < 1:
            raise ValueError('ngram_min must be at least 1')
        if self.ngram_max < self.ngram_min:
            raise ValueError('ngram_max must be greater than or equal to ngram_min')
        if self.ngram_max > 32:
            raise ValueError('ngram_max must be 32 or less')
        if self.fuzzy_distance < 0 or self.fuzzy_distance > 2:
            raise ValueError('fuzzy_distance must be 0, 1 or 2')
        if self.remove_long < 8:
            raise ValueError('remove_long must be at least 8')
        if self.snippet_chars < 32:
            raise ValueError('snippet_chars must be at least 32')
        for name in ('title_exact_boost', 'title_ngram_boost', 'text_boost',
                     'phrase_boost_multiplier'):
            if getattr(self, name) < 0:
                raise ValueError('{} must not be negative'.format(name))
        if not isinstance(self.stemmer, str) or not self.stemmer:
            raise ValueError('stemmer must be a non empty string')
        if not isinstance(self.stopwords_language, str) or not self.stopwords_language:
            raise ValueError('stopwords_language must be a non empty string')
        return self


_FLOATS = {'title_exact_boost', 'title_ngram_boost', 'text_boost',
           'phrase_boost_multiplier'}
_INTS = {'ngram_min', 'ngram_max', 'fuzzy_distance', 'remove_long', 'snippet_chars'}
_BOOLS = {'fuzzy_enabled', 'highlight'}


def _coerce(key, value):
    if key in _BOOLS:
        if not isinstance(value, bool):
            raise ValueError('{} must be true or false'.format(key))
        return value
    if key in _INTS:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError('{} must be an integer'.format(key))
        return value
    if key in _FLOATS:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError('{} must be a number'.format(key))
        return float(value)
    if key == 'extra_stopwords':
        if not isinstance(value, (list, tuple)):
            raise ValueError('extra_stopwords must be a list of strings')
        out = []
        for word in value:
            if not isinstance(word, str):
                raise ValueError('extra_stopwords must be a list of strings')
            out.append(word.lower())
        return out
    if not isinstance(value, str):
        raise ValueError('{} must be a string'.format(key))
    return value


DEFAULT_TUNING = Tuning()


def tuning_path(data_dir: str) -> str:
    return os.path.join(data_dir, TUNING_FILENAME)


def load_tuning(data_dir: str) -> Tuning:
    '''Read ``<data_dir>/tuning.json``, falling back to the defaults.'''
    path = tuning_path(data_dir)
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return Tuning.from_dict(json.load(handle))
    except FileNotFoundError:
        return Tuning()
    except (ValueError, OSError):
        return Tuning()


def save_tuning(data_dir: str, tuning: Tuning) -> Tuning:
    '''Write the tuning file atomically and return what was written.'''
    tuning.validate()
    os.makedirs(data_dir, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        'w', encoding='utf-8', dir=data_dir, prefix='.tuning-', suffix='.tmp',
        delete=False)
    try:
        json.dump(tuning.to_dict(), handle, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    os.replace(handle.name, tuning_path(data_dir))
    return tuning
