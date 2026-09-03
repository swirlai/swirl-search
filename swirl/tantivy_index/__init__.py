'''
SWIRL Tantivy index package.

Implements TECH_DESIGN_swirl_for_backstage.md section 3.1: the schema, the
tuning surface, the generation directory layout and the index manager that the
Backstage ingest API (section 3.2) and the TantivyIndex connector (3.4) use.

Nothing in ``schema.py`` or ``tuning.py`` imports Django, so the gate-zero
gauntlet in ``DevUtils/backstage-gauntlet.py`` can import them standalone.
'''

from swirl.tantivy_index.tuning import Tuning, DEFAULT_TUNING
from swirl.tantivy_index.schema import (
    SEARCH_FIELDS,
    STORED_FIELDS,
    build_analyzers,
    build_schema,
    document_attrs,
    document_id,
    escape_term,
    open_index,
    validate_document,
)

__all__ = [
    'Tuning',
    'DEFAULT_TUNING',
    'SEARCH_FIELDS',
    'STORED_FIELDS',
    'build_analyzers',
    'build_schema',
    'document_attrs',
    'document_id',
    'escape_term',
    'open_index',
    'validate_document',
]
