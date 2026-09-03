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
    #: BM25 parameters. Accepted and stored, but tantivy-py exposes no way to
    #: set them (see ``bm25_supported``), so the config endpoint says so in its
    #: response rather than pretending they took effect.
    bm25_k1: float = 1.2
    bm25_b: float = 0.75

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
        '''Build a Tuning from a partial dict in either accepted shape.

        Two shapes are accepted: SWIRL's own flat snake_case names, and the
        nested camelCase block the Backstage engine module sends verbatim from
        app-config (``fieldBoosts.titleExact``, ``ngram.min``,
        ``fuzzy.enabled``, ``bm25.k1``, ``highlight.maxChars`` and friends).
        The two may be mixed in one call.

        Unknown keys are rejected rather than dropped: silently ignoring them
        is how a whole documented tuning block used to do nothing at all.
        Raises ValueError, which the config endpoint turns into a 400, when a
        key is unknown, or a known key carries a value of the wrong type or an
        out-of-range value.
        '''
        flat, _accepted, unknown = normalize(data)
        if unknown:
            raise ValueError(
                'unknown tuning key(s): {}. Known keys are the SWIRL names '
                '({}) and the nested Backstage names ({}).'.format(
                    ', '.join(unknown),
                    ', '.join(sorted(f.name for f in fields(cls))),
                    ', '.join(sorted(NESTED_KEYS))))
        tuning = cls(**flat)
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
        if self.bm25_k1 < 0:
            raise ValueError('bm25_k1 must not be negative')
        if self.bm25_b < 0 or self.bm25_b > 1:
            raise ValueError('bm25_b must be between 0 and 1')
        return self


_FLOATS = {'title_exact_boost', 'title_ngram_boost', 'text_boost',
           'phrase_boost_multiplier', 'bm25_k1', 'bm25_b'}
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


########################################
# The two accepted key shapes
#
# SWIRL's own flat snake_case names, and the nested camelCase block the
# Backstage engine module sends verbatim out of app-config
# (TECH_DESIGN_swirl_for_backstage.md section 2.2). The engine used to send the
# documented nested shape and SWIRL used to drop every key of it on the floor,
# so an operator's whole tuning block did nothing.

#: Nested camelCase path -> SWIRL field. ``stopwords`` is deliberately absent:
#: it maps to two different fields depending on the value, see _NESTED_SPECIAL.
NESTED_KEY_MAP = {
    'fieldBoosts.titleExact': 'title_exact_boost',
    'fieldBoosts.titleNgram': 'title_ngram_boost',
    'fieldBoosts.text': 'text_boost',
    'fieldBoosts.phraseMultiplier': 'phrase_boost_multiplier',
    'ngram.min': 'ngram_min',
    'ngram.max': 'ngram_max',
    'stemmer': 'stemmer',
    'fuzzy.enabled': 'fuzzy_enabled',
    'fuzzy.distance': 'fuzzy_distance',
    'bm25.k1': 'bm25_k1',
    'bm25.b': 'bm25_b',
    'highlight.enabled': 'highlight',
    'highlight.maxChars': 'snippet_chars',
    'removeLong': 'remove_long',
}

#: Top level nested keys that carry an object, so that a scalar in their place
#: is a clear error rather than an unknown key.
NESTED_OBJECTS = ('fieldBoosts', 'ngram', 'fuzzy', 'bm25', 'highlight')

#: Every nested path the config endpoint accepts, for the error message.
NESTED_KEYS = tuple(sorted(NESTED_KEY_MAP)) + ('stopwords',)

#: What the config endpoint reports when BM25 parameters were accepted and
#: stored but the installed tantivy cannot apply them.
BM25_NOT_APPLIED = 'not applied by this engine version'


def bm25_supported() -> bool:
    '''Whether the installed tantivy exposes BM25 k1 and b.

    tantivy-py 0.26 does not: neither Index, Schema, SchemaBuilder nor Searcher
    carries anything to set them, and the Rust crate's ``Bm25Weight`` is not
    bound. The probe is written against the objects rather than a version
    number so that a later binding is picked up on its own.
    '''
    try:
        import tantivy
    except ImportError:
        return False
    for holder in ('Index', 'Schema', 'SchemaBuilder', 'Searcher'):
        target = getattr(tantivy, holder, None)
        if target is None:
            continue
        names = {name.lower() for name in dir(target)}
        if 'bm25' in names or {'k1', 'b'} <= names:
            return True
    return bool(getattr(tantivy, 'Bm25Weight', None))


def normalize(data):
    '''Fold either accepted shape into SWIRL's flat field names.

    Returns ``(flat, accepted_keys, unknown_keys)``. ``accepted_keys`` names the
    keys as they were sent, dotted for the nested shape, so a caller can log
    exactly what SWIRL took. ``unknown_keys`` is what the caller should be told
    about instead of having it dropped.
    '''
    if data is None:
        return {}, [], []
    if not isinstance(data, dict):
        raise ValueError('tuning must be a JSON object')

    known = {f.name for f in fields(Tuning)}
    flat = {}
    accepted = []
    unknown = []

    def take(field, value, sent_as):
        flat[field] = _coerce(field, value)
        accepted.append(sent_as)

    for key, value in data.items():
        # A nested block wins over a flat field of the same name: `highlight`
        # is a bool in SWIRL's own shape and an object in the Backstage one.
        if key in NESTED_OBJECTS and isinstance(value, dict):
            for inner, inner_value in value.items():
                path = '{}.{}'.format(key, inner)
                if path in NESTED_KEY_MAP:
                    take(NESTED_KEY_MAP[path], inner_value, path)
                else:
                    unknown.append(path)
            continue
        if key in known:
            take(key, value, key)
            continue
        if key == 'stopwords':
            # The Backstage block types this as a list of extra stopwords; a
            # bare string names a language, which is SWIRL's own knob.
            if isinstance(value, str):
                take('stopwords_language', value, 'stopwords')
            else:
                take('extra_stopwords', value, 'stopwords')
            continue
        if key in NESTED_KEY_MAP and not isinstance(value, dict):
            take(NESTED_KEY_MAP[key], value, key)
            continue
        if key in NESTED_OBJECTS:
            raise ValueError('{} must be a JSON object'.format(key))
        unknown.append(key)

    return flat, accepted, unknown


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
