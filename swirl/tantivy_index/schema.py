'''
Tantivy schema and analyzers for the SWIRL Backstage index.

TECH_DESIGN_swirl_for_backstage.md section 3.1. One deviation from the design
table, recorded by gate zero in reboot-design/gauntlet-results.md: Tantivy text
fields are always indexed, so ``document_json``, ``title`` and ``location``
cannot be "stored, not indexed". They use the ``raw`` tokenizer with
``index_option='basic'``, which costs one non positional term per document and
is never queried.

No Django imports here on purpose: the gate-zero gauntlet in
DevUtils/backstage-gauntlet.py imports this module standalone.
'''

from __future__ import annotations

import hashlib
import json
import re

from swirl.tantivy_index.tuning import DEFAULT_TUNING, Tuning

try:
    from tantivy import Filter, Index, SchemaBuilder, TextAnalyzerBuilder, Tokenizer
    TANTIVY_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised by the skipif in the tests
    TANTIVY_AVAILABLE = False

#: The fields the query parser searches by default, in boost order.
SEARCH_FIELDS = ['title_exact', 'title_ngram', 'text']

#: The fields carried back out of the index for display and for the connector.
STORED_FIELDS = ['doc_id', 'type', 'title', 'location', 'document_json']

#: The Backstage SearchDocument contract: these three are mandatory and are not
#: turned into ``attrs`` tokens.
REQUIRED_DOCUMENT_FIELDS = ('title', 'text', 'location')

#: Analyzer names as registered on the Index.
ANALYZER_EXACT = 'swirl_exact'
ANALYZER_NGRAM = 'swirl_ngram'
ANALYZER_TEXT = 'swirl_text'


def build_schema():
    '''Build the Tantivy schema exactly as TECH_DESIGN section 3.1 specifies.'''
    builder = SchemaBuilder()
    builder.add_text_field(
        'title_exact', stored=False, tokenizer_name=ANALYZER_EXACT,
        index_option='position')
    builder.add_text_field(
        'title_ngram', stored=False, tokenizer_name=ANALYZER_NGRAM,
        index_option='position')
    builder.add_text_field(
        'text', stored=False, tokenizer_name=ANALYZER_TEXT,
        index_option='position')
    builder.add_text_field(
        'attrs', stored=False, tokenizer_name='raw', index_option='basic')
    builder.add_text_field(
        'doc_id', stored=True, tokenizer_name='raw', index_option='basic')
    builder.add_text_field(
        'type', stored=True, tokenizer_name='raw', index_option='basic')
    builder.add_text_field(
        'title', stored=True, tokenizer_name='raw', index_option='basic')
    builder.add_text_field(
        'location', stored=True, tokenizer_name='raw', index_option='basic')
    builder.add_text_field(
        'document_json', stored=True, tokenizer_name='raw', index_option='basic')
    return builder.build()


def build_analyzers(tuning: Tuning = DEFAULT_TUNING) -> dict:
    '''Return the three named analyzers keyed by their registered name.'''
    exact = (
        TextAnalyzerBuilder(Tokenizer.simple())
        .filter(Filter.lowercase())
        .filter(Filter.ascii_fold())
        .filter(Filter.remove_long(tuning.remove_long))
        .filter(Filter.stemmer(tuning.stemmer))
        .build()
    )
    ngram = (
        TextAnalyzerBuilder(Tokenizer.ngram(tuning.ngram_min, tuning.ngram_max, False))
        .filter(Filter.lowercase())
        .filter(Filter.ascii_fold())
        .build()
    )
    text_builder = (
        TextAnalyzerBuilder(Tokenizer.simple())
        .filter(Filter.lowercase())
        .filter(Filter.ascii_fold())
        .filter(Filter.remove_long(tuning.remove_long))
        .filter(Filter.stopword(tuning.stopwords_language))
    )
    if tuning.extra_stopwords:
        text_builder = text_builder.filter(
            Filter.custom_stopword(list(tuning.extra_stopwords)))
    text = text_builder.filter(Filter.stemmer(tuning.stemmer)).build()
    return {ANALYZER_EXACT: exact, ANALYZER_NGRAM: ngram, ANALYZER_TEXT: text}


def open_index(path=None, tuning: Tuning = DEFAULT_TUNING):
    '''Create or open the index and register the analyzers.

    The analyzers must be registered before any document is added, and again
    on every process that opens the index for reading.
    '''
    schema = build_schema()
    index = Index(schema, path=path) if path else Index(schema)
    register_analyzers(index, tuning)
    return index


def register_analyzers(index, tuning: Tuning = DEFAULT_TUNING):
    for name, analyzer in build_analyzers(tuning).items():
        index.register_tokenizer(name, analyzer)
    return index


########################################
# Documents


def validate_document(document, position=0):
    '''Raise ValueError when the document is not a Backstage SearchDocument.

    The Backstage contract is title, text and location, all strings. ``text``
    may be empty, since the catalog collator emits an empty description for
    entities that have none, but it must be present.
    '''
    if not isinstance(document, dict):
        raise ValueError(
            'document at index {} is not an object'.format(position))
    for name in REQUIRED_DOCUMENT_FIELDS:
        if name not in document:
            raise ValueError(
                'document at index {} is missing the required field '
                '"{}"'.format(position, name))
        if not isinstance(document[name], str):
            raise ValueError(
                'document at index {} has a non string "{}"'.format(position, name))
    if not document['title'].strip():
        raise ValueError(
            'document at index {} has an empty "title"'.format(position))
    if not document['location'].strip():
        raise ValueError(
            'document at index {} has an empty "location"'.format(position))
    return document


def document_attrs(document) -> list:
    '''One lowercased ``key=value`` token per scalar top level attribute.

    ``title``, ``text`` and ``location`` are excluded: they are the Backstage
    SearchDocument contract fields and are indexed in their own fields. Nested
    objects and lists are skipped, and so are empty values.
    '''
    attrs = []
    for key in sorted(document.keys(), key=lambda name: str(name).lower()):
        if key in REQUIRED_DOCUMENT_FIELDS:
            continue
        value = document[key]
        if value is None or isinstance(value, (dict, list, tuple, set)):
            continue
        if isinstance(value, bool):
            token = 'true' if value else 'false'
        elif isinstance(value, (int, float)):
            token = str(value)
        elif isinstance(value, str):
            token = value.strip().lower()
        else:
            continue
        if not token:
            continue
        attrs.append('{}={}'.format(str(key).strip().lower(), token))
    return attrs


def document_id(document) -> str:
    '''The Backstage ``location`` when present, else a sha256 of the document.'''
    location = (document or {}).get('location')
    if location:
        return str(location)
    payload = json.dumps(document or {}, sort_keys=True, default=str).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


########################################
# Query building

_QUERY_SPECIALS = re.compile(r'([+\-&|!(){}\[\]^"~*?:\\/])')


def escape_term(term: str) -> str:
    '''Escape the Tantivy query parser metacharacters in raw user input.'''
    return _QUERY_SPECIALS.sub(r'\\\1', term or '')
