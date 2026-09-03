'''
The SWIRL Tantivy index manager (TECH_DESIGN section 3.1).

``begin``, ``add``, ``finalize``, ``abort`` are the write side used by the
ingest API in WP02. ``search`` and ``stats`` are the read side used by the
TantivyIndex connector in WP04 and by the health endpoint in WP06.

Writers are opened per ``add`` batch and committed and closed again, so a
second process can pick up an open generation and no Tantivy directory lock
survives a crashed request. The single writer guarantee comes from the OPEN
lock in ``generations.py``, not from a cached writer.

Readers are cached per process, keyed by type, and invalidated on a change to
the LIVE file.
'''

from __future__ import annotations

import json
import logging
import os
import threading

from swirl.tantivy_index import generations as gen
from swirl.tantivy_index.generations import (  # noqa: F401  re-exported for callers
    GenerationNotFound,
    GenerationOpen,
    InvalidTypeName,
    NoDocuments,
    TantivyIndexError,
)
from swirl.tantivy_index.schema import (
    SEARCH_FIELDS,
    document_attrs,
    document_id,
    escape_term,
    open_index,
    register_analyzers,
    validate_document,
)
from swirl.tantivy_index.tuning import DEFAULT_TUNING, Tuning, load_tuning, save_tuning

logger = logging.getLogger(__name__)

try:
    from tantivy import Document, Index, Occur, Query, SnippetGenerator
    TANTIVY_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised by the skipif in the tests
    TANTIVY_AVAILABLE = False

#: Maximum documents accepted in one ``add`` call, per TECH_DESIGN 3.2.
MAX_BATCH = 1000

DEFAULT_DATA_DIRNAME = 'tantivy_data'
DEFAULT_WRITER_HEAP_MB = 128


def _setting(name, default):
    try:
        from django.conf import settings
    except ImportError:  # pragma: no cover - Django is always present in SWIRL
        return default
    try:
        return getattr(settings, name, default)
    except Exception:  # pragma: no cover - settings not configured
        return default


class TantivyIndexManager:
    '''One manager per data directory. The default instance reads settings.'''

    def __init__(self, data_dir=None, writer_heap_mb=None, begin_ttl=None):
        self._data_dir = data_dir
        self._writer_heap_mb = writer_heap_mb
        self._begin_ttl = begin_ttl
        self._readers = {}
        self._lock = threading.Lock()

    ########################################
    # Configuration

    @property
    def data_dir(self):
        if self._data_dir:
            return self._data_dir
        default = DEFAULT_DATA_DIRNAME
        try:
            from django.conf import settings
            default = os.path.join(str(settings.BASE_DIR), DEFAULT_DATA_DIRNAME)
        except Exception:  # pragma: no cover - settings not configured
            pass
        return str(_setting('SWIRL_TANTIVY_DATA_DIR', default))

    @property
    def writer_heap_bytes(self):
        heap_mb = self._writer_heap_mb
        if heap_mb is None:
            heap_mb = int(_setting('SWIRL_TANTIVY_WRITER_HEAP_MB',
                                   DEFAULT_WRITER_HEAP_MB))
        return int(heap_mb) * 1024 * 1024

    @property
    def begin_ttl(self):
        if self._begin_ttl is not None:
            return self._begin_ttl
        return int(_setting('SWIRL_TANTIVY_BEGIN_TTL', gen.DEFAULT_BEGIN_TTL))

    def tuning(self):
        '''The effective tuning, read from ``<data_dir>/tuning.json``.'''
        return load_tuning(self.data_dir)

    def configure(self, payload):
        '''Persist a tuning block and return the effective tuning.

        Applied on the next ``begin``; the live generations keep the analyzers
        they were built with until they are replaced.
        '''
        current = self.tuning().to_dict()
        current.update(payload or {})
        return save_tuning(self.data_dir, Tuning.from_dict(current))

    ########################################
    # Write side

    def begin(self, type_name, started_by=None):
        return gen.begin(self.data_dir, type_name, ttl=self.begin_ttl,
                         started_by=started_by)

    def open_generation(self, type_name):
        return gen.open_generation(self.data_dir, type_name, ttl=self.begin_ttl)

    def add(self, type_name, generation, documents, doc_type=None):
        '''Validate and write a batch, then commit.

        Every document in the batch is validated before anything is written, so
        a bad document rejects the whole batch and leaves the generation as it
        was. Raises ValueError with the offending index.
        '''
        if not isinstance(documents, list):
            raise ValueError('"documents" must be a list')
        if len(documents) > MAX_BATCH:
            raise ValueError(
                'at most {} documents per request, got {}'.format(
                    MAX_BATCH, len(documents)))
        path = gen.require_open(self.data_dir, type_name, generation,
                                ttl=self.begin_ttl)
        for position, document in enumerate(documents):
            validate_document(document, position)
        if not documents:
            return 0

        tuning = self.tuning()
        index = self._open_writable(path, tuning)
        writer = index.writer(self.writer_heap_bytes)
        try:
            for document in documents:
                writer.add_document(self._to_tantivy(document, type_name, doc_type))
            writer.commit()
            writer.wait_merging_threads()
        except Exception:
            # wait_merging_threads consumes the writer; on any other failure the
            # writer is dropped here and the directory lock is released.
            raise
        self._bump_count(path, len(documents))
        return len(documents)

    def finalize(self, type_name, generation):
        path = gen.require_open(self.data_dir, type_name, generation,
                                ttl=self.begin_ttl)
        count = self._read_count(path)
        result = gen.finalize(self.data_dir, type_name, generation,
                              doc_count=count, ttl=self.begin_ttl)
        result['count'] = count
        result['bytes'] = gen.directory_bytes(path)
        self.invalidate(type_name)
        return result

    def abort(self, type_name, generation):
        gen.abort(self.data_dir, type_name, generation, ttl=self.begin_ttl)
        return generation

    def delete(self, type_name):
        deleted = gen.delete_type(self.data_dir, type_name)
        self.invalidate(type_name)
        return deleted

    ########################################
    # Read side

    def types(self):
        '''Every type that has a live generation.'''
        return [name for name in gen.list_types(self.data_dir)
                if gen.live_generation(self.data_dir, name)]

    def stats(self, type_name):
        live = gen.live_generation(self.data_dir, type_name)
        row = {
            'type': type_name,
            'live': live,
            'doc_count': 0,
            'bytes': 0,
            'updated': None,
            'open': self.open_generation(type_name),
        }
        if not live:
            return row
        path = os.path.join(gen.type_dir(self.data_dir, type_name), live)
        row['doc_count'] = self._read_count(path)
        row['bytes'] = gen.directory_bytes(path)
        try:
            row['updated'] = os.stat(gen.live_file(self.data_dir, type_name)).st_mtime
        except OSError:
            row['updated'] = None
        return row

    def all_stats(self):
        return [self.stats(name) for name in gen.list_types(self.data_dir)]

    def invalidate(self, type_name=None):
        with self._lock:
            if type_name is None:
                self._readers.clear()
            else:
                self._readers.pop(type_name, None)

    def reader(self, type_name):
        '''The cached reader index for the live generation, or None.

        The cache key is the live generation plus the LIVE file mtime, so a
        finalize in another process is picked up on the next query.
        '''
        live = gen.live_generation(self.data_dir, type_name)
        if not live:
            self.invalidate(type_name)
            return None
        stamp = gen.live_mtime(self.data_dir, type_name)
        with self._lock:
            cached = self._readers.get(type_name)
            if cached and cached[0] == live and cached[1] == stamp:
                return cached[2]
        path = os.path.join(gen.type_dir(self.data_dir, type_name), live)
        try:
            index = Index.open(path)
        except Exception as err:
            logger.warning('tantivy_index: cannot open %s: %s', path, err)
            return None
        register_analyzers(index, self.tuning())
        index.reload()
        with self._lock:
            self._readers[type_name] = (live, stamp, index)
        return index

    def search(self, types=None, term='', filters=None, limit=10, offset=0,
               fuzzy=None, highlight=None):
        '''Search one or more type indexes and merge the hits by score.

        Returns a list of dicts with title, body, location, doc_id, type, score
        and, when highlighting is on and a snippet is available, snippet.
        '''
        tuning = self.tuning()
        if fuzzy is None:
            fuzzy = tuning.fuzzy_enabled
        if highlight is None:
            highlight = tuning.highlight
        wanted = list(types) if types else self.types()
        limit = max(int(limit or 10), 1)
        offset = max(int(offset or 0), 0)
        hits = []
        for type_name in wanted:
            try:
                gen.validate_type_name(type_name)
            except InvalidTypeName:
                logger.warning('tantivy_index: ignoring bad type name %s', type_name)
                continue
            index = self.reader(type_name)
            if index is None:
                continue
            try:
                hits.extend(self._search_one(index, type_name, term, filters,
                                             limit + offset, fuzzy, highlight,
                                             tuning))
            except Exception as err:
                logger.warning('tantivy_index: search of %s failed: %s',
                               type_name, err)
        hits.sort(key=lambda hit: hit['score'], reverse=True)
        return hits[offset:offset + limit]

    ########################################
    # Internals

    def _open_writable(self, path, tuning):
        return open_index(path, tuning)

    def _to_tantivy(self, document, type_name, doc_type=None):
        title = document.get('title') or ''
        return Document(
            title_exact=title,
            title_ngram=title,
            text=document.get('text') or '',
            attrs=document_attrs(document),
            doc_id=document_id(document),
            type=doc_type or type_name,
            title=title,
            location=document.get('location') or '',
            document_json=json.dumps(document, sort_keys=True, default=str),
        )

    def _count_path(self, path):
        return os.path.join(path, 'swirl_count.json')

    def _read_count(self, path):
        try:
            with open(self._count_path(path), 'r', encoding='utf-8') as handle:
                return int(json.load(handle).get('count') or 0)
        except (FileNotFoundError, NotADirectoryError, ValueError, OSError, TypeError):
            return 0

    def _bump_count(self, path, delta):
        count = self._read_count(path) + int(delta)
        tmp = self._count_path(path) + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as handle:
            json.dump({'count': count}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, self._count_path(path))
        return count

    def build_query(self, index, term, filters=None, fuzzy=False, tuning=None):
        '''The query TECH_DESIGN 3.1 describes.

        A parsed multi field query, plus a SHOULD phrase query on title_exact
        for multi word input, plus one MUST boolean_query of attrs term queries
        per filter, multi valued filters as SHOULD inside that.
        '''
        tuning = tuning or DEFAULT_TUNING
        schema = index.schema
        fuzzy_fields = {}
        if fuzzy:
            fuzzy_fields = {'title_exact': (False, tuning.fuzzy_distance, True)}
        parsed = index.parse_query(
            escape_term(term),
            default_field_names=list(SEARCH_FIELDS),
            field_boosts=dict(tuning.field_boosts),
            fuzzy_fields=fuzzy_fields,
        )
        subqueries = [(Occur.Must, parsed)]

        from swirl.tantivy_index.schema import build_analyzers
        tokens = build_analyzers(tuning)['swirl_exact'].analyze(term or '')
        if len(tokens) > 1:
            phrase = Query.phrase_query(schema, 'title_exact', list(tokens))
            subqueries.append((Occur.Should, Query.boost_query(
                phrase, tuning.title_exact_boost * tuning.phrase_boost_multiplier)))

        for key, value in (filters or {}).items():
            values = value if isinstance(value, (list, tuple, set)) else [value]
            clauses = [
                (Occur.Should, Query.term_query(
                    schema, 'attrs',
                    '{}={}'.format(str(key).strip().lower(), str(item).strip().lower()),
                    'basic'))
                for item in values if str(item).strip()
            ]
            if clauses:
                subqueries.append((Occur.Must, Query.boolean_query(clauses)))

        return Query.boolean_query(subqueries)

    def _search_one(self, index, type_name, term, filters, limit, fuzzy,
                    highlight, tuning):
        query = self.build_query(index, term, filters=filters, fuzzy=fuzzy,
                                 tuning=tuning)
        searcher = index.searcher()
        result = searcher.search(query, limit)
        snippets = None
        if highlight:
            try:
                snippets = SnippetGenerator.create(searcher, query, index.schema, 'text')
                snippets.set_max_num_chars(tuning.snippet_chars)
            except Exception as err:
                logger.debug('tantivy_index: no snippets for %s: %s', type_name, err)
                snippets = None
        hits = []
        for score, address in result.hits:
            stored = searcher.doc(address)
            payload = stored.get_first('document_json')
            document = {}
            if payload:
                try:
                    document = json.loads(payload)
                except ValueError:
                    document = {}
            body = document.get('text') or ''
            snippet = ''
            if snippets is not None:
                try:
                    snippet = snippets.snippet_from_doc(stored).to_html()
                except Exception:
                    snippet = ''
            hits.append({
                'title': stored.get_first('title') or '',
                'body': body[:tuning.snippet_chars],
                'snippet': snippet,
                'location': stored.get_first('location') or '',
                'doc_id': stored.get_first('doc_id') or '',
                'type': stored.get_first('type') or type_name,
                'score': float(score),
                'document': document,
            })
        return hits


#: The process wide manager the views and the connector use.
default_manager = TantivyIndexManager()
