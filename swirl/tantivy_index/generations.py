'''
Generation directories for the SWIRL Tantivy index (TECH_DESIGN section 3.1).

Layout::

    <data_dir>/<type>/<generation>/     one Tantivy index directory
    <data_dir>/<type>/LIVE              names the live generation
    <data_dir>/<type>/OPEN              the single writer lock

``begin`` creates a new generation directory and takes the OPEN lock.
``finalize`` writes LIVE atomically (write a temp file, rename over LIVE), then
deletes every older generation except the previous one, so a reader that is
mid-query on the previous generation is not pulled out from under.
``abort`` deletes the generation and releases the lock.

The filesystem is the source of truth. The ``SearchIndexGeneration`` rows added
in WP02 are bookkeeping for the admin.
'''

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time

LIVE_FILE = 'LIVE'
OPEN_FILE = 'OPEN'

#: Type names are used as directory names, so they are tightly constrained.
TYPE_NAME_RE = re.compile(r'^[a-z0-9-]{1,64}$')
GENERATION_RE = re.compile(r'^[0-9]{8}T[0-9]{6}-[0-9]{6}$')

#: Default seconds after which an OPEN lock is considered abandoned.
#: Half an hour: long enough for a slow collator pass over a large catalog,
#: short enough that a run which died without aborting does not hold the type
#: for the rest of the working day. An operator who does not want to wait can
#: clear the lock from the SearchIndexGeneration admin.
DEFAULT_BEGIN_TTL = 30 * 60

#: How many times ``begin`` retries after taking over a stale lock. Each retry
#: costs one O_EXCL create, so a low number is enough; the loop only spins when
#: two callers race for the same abandoned lock.
BEGIN_ATTEMPTS = 3


class TantivyIndexError(Exception):
    '''Base for every generation error.'''


class InvalidTypeName(TantivyIndexError):
    '''The type name is not ``^[a-z0-9-]{1,64}$``.'''


class GenerationOpen(TantivyIndexError):
    '''A generation is already open for this type. The view answers 409.'''

    def __init__(self, type_name, generation, age_seconds):
        self.type_name = type_name
        self.generation = generation
        self.age_seconds = age_seconds
        super().__init__(
            'a generation is already open for type "{}": {} (open for {} s)'.format(
                type_name, generation, int(age_seconds)))


class GenerationNotFound(TantivyIndexError):
    '''The named generation directory does not exist.'''


class NoDocuments(TantivyIndexError):
    '''Finalize was called on a generation with zero documents.'''


########################################
# Names and paths


def validate_type_name(type_name):
    if not isinstance(type_name, str) or not TYPE_NAME_RE.match(type_name):
        raise InvalidTypeName(
            'type name must match ^[a-z0-9-]{{1,64}}$, got "{}"'.format(type_name))
    return type_name


def new_generation_id(now=None):
    '''A sortable generation id: ``YYYYmmddTHHMMSS-uuuuuu``.'''
    now = now if now is not None else time.time()
    stamp = time.strftime('%Y%m%dT%H%M%S', time.gmtime(now))
    micros = int(round((now - int(now)) * 1000000)) % 1000000
    return '{}-{:06d}'.format(stamp, micros)


def type_dir(data_dir, type_name):
    validate_type_name(type_name)
    return os.path.join(data_dir, type_name)


def generation_dir(data_dir, type_name, generation):
    if not GENERATION_RE.match(generation or ''):
        raise GenerationNotFound('malformed generation "{}"'.format(generation))
    return os.path.join(type_dir(data_dir, type_name), generation)


def live_file(data_dir, type_name):
    return os.path.join(type_dir(data_dir, type_name), LIVE_FILE)


def open_file(data_dir, type_name):
    return os.path.join(type_dir(data_dir, type_name), OPEN_FILE)


########################################
# Atomic writes


def _write_atomic(path, payload):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        'w', encoding='utf-8', dir=directory, prefix='.tmp-', delete=False)
    try:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    os.replace(handle.name, path)


########################################
# LIVE


def live_generation(data_dir, type_name):
    '''The live generation for the type, or None.'''
    try:
        with open(live_file(data_dir, type_name), 'r', encoding='utf-8') as handle:
            generation = handle.read().strip()
    except (FileNotFoundError, NotADirectoryError):
        return None
    if not generation:
        return None
    if not os.path.isdir(os.path.join(type_dir(data_dir, type_name), generation)):
        return None
    return generation


def live_mtime(data_dir, type_name):
    '''The mtime of the LIVE file, for the reader cache. 0 when absent.'''
    try:
        return os.stat(live_file(data_dir, type_name)).st_mtime_ns
    except (FileNotFoundError, NotADirectoryError):
        return 0


def live_path(data_dir, type_name):
    '''The directory of the live generation, or None.'''
    generation = live_generation(data_dir, type_name)
    if not generation:
        return None
    return os.path.join(type_dir(data_dir, type_name), generation)


########################################
# The single writer lock


def read_open(data_dir, type_name):
    '''The open generation record for the type, or None.'''
    try:
        with open(open_file(data_dir, type_name), 'r', encoding='utf-8') as handle:
            record = json.load(handle)
    except (FileNotFoundError, NotADirectoryError):
        return None
    except (ValueError, OSError):
        return None
    if not isinstance(record, dict) or not record.get('generation'):
        return None
    return record


def open_generation(data_dir, type_name, ttl=DEFAULT_BEGIN_TTL):
    '''The open generation id when the lock is held and not stale, else None.'''
    record = read_open(data_dir, type_name)
    if not record:
        return None
    if _is_stale(record, ttl):
        return None
    return record['generation']


def _is_stale(record, ttl):
    started_at = record.get('started_at') or 0
    try:
        started_at = float(started_at)
    except (TypeError, ValueError):
        return True
    return (time.time() - started_at) > float(ttl)


def clear_open(data_dir, type_name, generation=None):
    '''Release the OPEN lock. Returns True when a lock file was removed.

    With ``generation``, the lock is only released when it still names that
    generation, so a caller cleaning up after itself cannot delete a lock some
    other process took in the meantime.
    '''
    if generation is not None:
        record = read_open(data_dir, type_name)
        if record and record.get('generation') != generation:
            return False
    try:
        os.unlink(open_file(data_dir, type_name))
    except (FileNotFoundError, NotADirectoryError):
        return False
    return True


def take_open_lock(data_dir, type_name, generation, started_by=None):
    '''Create the OPEN file exclusively. True when this caller took the lock.

    O_CREAT | O_EXCL is the whole point: two processes calling ``begin`` in the
    same instant used to both read "no lock", both create a generation
    directory and both write OPEN, which left one of them believing it owned a
    generation nobody would ever finalize. Exactly one create can win now.

    The record is written into the file that was created exclusively, not into
    a temp file renamed over it, because a rename would clobber a lock another
    caller had already taken.
    '''
    path = open_file(data_dir, type_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = json.dumps({
        'generation': generation,
        'started_at': time.time(),
        'pid': os.getpid(),
        'started_by': started_by or '',
    })
    try:
        handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return False
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        # Never leave a lock file with no record in it: read_open would treat
        # it as absent and the next begin would create a second generation.
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    return True


def rollback(data_dir, type_name, generation):
    '''Undo a ``begin``: drop the generation directory and release the lock.

    Called when the caller could not finish opening the generation (the ingest
    view could not write its bookkeeping row, say). Without it a half-done
    begin leaves the type answering 409 to every later begin until the TTL runs
    out. The live generation is never touched.
    '''
    validate_type_name(type_name)
    if generation and generation != live_generation(data_dir, type_name):
        if GENERATION_RE.match(generation):
            shutil.rmtree(os.path.join(type_dir(data_dir, type_name), generation),
                          ignore_errors=True)
    return clear_open(data_dir, type_name, generation)


def clear_stale_open(data_dir, type_name, ttl=DEFAULT_BEGIN_TTL):
    '''Release the OPEN lock when it has gone stale. True when one was cleared.

    The admin uses this to unwedge a type whose ingest run died. A lock that is
    still inside its TTL is left alone.
    '''
    record = read_open(data_dir, type_name)
    if not record:
        return False
    if not _is_stale(record, ttl):
        return False
    return clear_open(data_dir, type_name, record.get('generation'))


########################################
# Lifecycle


def begin(data_dir, type_name, ttl=DEFAULT_BEGIN_TTL, started_by=None, now=None):
    '''Take the OPEN lock, then create the generation directory.

    Raises GenerationOpen when another generation is open for the same type and
    the lock has not gone stale past ``ttl``. A stale lock is taken over and the
    abandoned generation directory is removed.

    The lock is taken with an exclusive create before anything else exists on
    disk, so two callers arriving in the same instant cannot both believe they
    opened a generation. The loser sees GenerationOpen and nothing of its own
    was created; the winner owns both the lock and the directory.
    '''
    validate_type_name(type_name)
    directory = type_dir(data_dir, type_name)
    os.makedirs(directory, exist_ok=True)

    for _attempt in range(BEGIN_ATTEMPTS):
        generation = new_generation_id(now)
        while os.path.exists(os.path.join(directory, generation)):
            generation = new_generation_id((now or time.time()) + 0.000001)

        if take_open_lock(data_dir, type_name, generation, started_by):
            try:
                os.makedirs(os.path.join(directory, generation))
            except OSError:
                # The lock is ours and nothing else has run yet, so release it
                # rather than hold the type on a directory that never appeared.
                clear_open(data_dir, type_name, generation)
                raise
            return generation

        # Somebody else holds the lock. Take it over only when it is stale.
        record = read_open(data_dir, type_name)
        if record is None:
            # Released between our create and this read; go round again.
            continue
        started_at = record.get('started_at') or 0
        try:
            age = time.time() - float(started_at)
        except (TypeError, ValueError):
            age = float(ttl) + 1
        if age <= float(ttl):
            raise GenerationOpen(type_name, record.get('generation'), age)
        stale = record.get('generation')
        if stale and stale != live_generation(data_dir, type_name):
            shutil.rmtree(os.path.join(directory, stale), ignore_errors=True)
        clear_open(data_dir, type_name, stale)

    # Every attempt lost the race for the same lock. Answer the way a caller
    # that lost to a live generation is answered: 409, nothing created.
    record = read_open(data_dir, type_name) or {}
    raise GenerationOpen(type_name, record.get('generation'), 0)


def require_open(data_dir, type_name, generation, ttl=DEFAULT_BEGIN_TTL):
    '''Raise GenerationNotFound unless this generation is the open one.'''
    path = generation_dir(data_dir, type_name, generation)
    if not os.path.isdir(path):
        raise GenerationNotFound(
            'no generation "{}" for type "{}"'.format(generation, type_name))
    record = read_open(data_dir, type_name)
    if not record or record.get('generation') != generation:
        raise GenerationNotFound(
            'generation "{}" for type "{}" is not open'.format(generation, type_name))
    return path


def finalize(data_dir, type_name, generation, doc_count=0, ttl=DEFAULT_BEGIN_TTL):
    '''Swap LIVE to this generation and prune everything but the previous one.

    A zero document generation is refused: the live generation is kept and the
    caller gets NoDocuments, which the view turns into 400. The generation stays
    open so the caller can add documents or abort.
    '''
    path = require_open(data_dir, type_name, generation, ttl=ttl)
    if doc_count <= 0:
        raise NoDocuments(
            'generation "{}" for type "{}" has no documents; the live generation '
            'is unchanged'.format(generation, type_name))
    previous = live_generation(data_dir, type_name)
    _write_atomic(live_file(data_dir, type_name), generation)
    clear_open(data_dir, type_name)
    prune(data_dir, type_name, keep=[generation, previous])
    return {'live': generation, 'previous': previous, 'path': path}


def abort(data_dir, type_name, generation, ttl=DEFAULT_BEGIN_TTL):
    '''Delete the generation and release the lock. The live generation is kept.'''
    validate_type_name(type_name)
    path = generation_dir(data_dir, type_name, generation)
    if generation == live_generation(data_dir, type_name):
        raise TantivyIndexError(
            'refusing to abort the live generation "{}"'.format(generation))
    record = read_open(data_dir, type_name)
    if record and record.get('generation') == generation:
        clear_open(data_dir, type_name)
    if not os.path.isdir(path):
        raise GenerationNotFound(
            'no generation "{}" for type "{}"'.format(generation, type_name))
    shutil.rmtree(path, ignore_errors=True)
    return generation


def prune(data_dir, type_name, keep=()):
    '''Delete every generation directory not named in ``keep``.'''
    directory = type_dir(data_dir, type_name)
    keep = {name for name in keep if name}
    removed = []
    try:
        entries = sorted(os.listdir(directory))
    except (FileNotFoundError, NotADirectoryError):
        return removed
    for name in entries:
        if name in keep or not GENERATION_RE.match(name):
            continue
        target = os.path.join(directory, name)
        if os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=True)
            removed.append(name)
    return removed


def generations(data_dir, type_name):
    '''Every generation directory for the type, oldest first.'''
    directory = type_dir(data_dir, type_name)
    try:
        entries = sorted(os.listdir(directory))
    except (FileNotFoundError, NotADirectoryError):
        return []
    return [name for name in entries
            if GENERATION_RE.match(name)
            and os.path.isdir(os.path.join(directory, name))]


def list_types(data_dir):
    '''Every type directory under the data dir, sorted.'''
    try:
        entries = sorted(os.listdir(data_dir))
    except (FileNotFoundError, NotADirectoryError):
        return []
    return [name for name in entries
            if TYPE_NAME_RE.match(name) and os.path.isdir(os.path.join(data_dir, name))]


def delete_type(data_dir, type_name):
    '''Remove the whole type directory, live generation included.'''
    validate_type_name(type_name)
    directory = type_dir(data_dir, type_name)
    if not os.path.isdir(directory):
        return False
    shutil.rmtree(directory, ignore_errors=True)
    return True


def directory_bytes(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                continue
    return total
