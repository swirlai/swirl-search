'''
@author:     Sid Probstein
@contact:    sid@swirl.today

Sync the `name` and `tags` fields of SearchProvider and AIProvider rows
in a running SWIRL database against the authoritative
`SearchProviders/preloaded.json` and `AIProviders/preloaded.json` files.

Only `name` and `tags` are touched. Every other field (active, default,
connector, url, query_template, credentials, api_key, model, …) is
preserved exactly as currently configured in the DB — the script reads
each record back via GET, swaps in the new name+tags, and PUTs the
result, so per-install customisations are not clobbered.

Matching (default: fingerprint)
  Each name is reduced to a "fingerprint" — lowercased, parenthetical
  qualifiers stripped, then the right-side source token after " - " is
  taken, TLDs (.com/.org/.io/.net) trimmed, and whitespace/punctuation
  removed. preloaded "Drawings - Miro" → ``miro``; DB
  "Boards - Miro.com" → ``miro``; they match. A substring fallback
  catches near-misses like "Vectors - Pinecone" → ``pinecone`` matching
  DB "PineconeDB" → ``pineconedb``.

  This works for clean installs (where names + positions agree with
  preloaded.json) AND for installs that have drifted — extra rows or
  reorderings won't cause the script to rename the wrong row.

  Ambiguous (multi-match) or unmatched preloaded entries are reported
  and skipped; nothing is written for them.

Matching (--match position)
  1-indexed position in preloaded.json maps to the DB primary key. Use
  this ONLY when the DB was loaded directly from this preloaded.json
  with no subsequent inserts.

Defaults are conservative:
  - dry-run prints what would change, writes nothing
  - --apply actually writes
  - --quiet prints only the summary line
'''

import argparse
import json
import os
import re
import sys
from http import HTTPStatus

import requests
from requests.auth import HTTPBasicAuth

module_name = 'swirl_sync.py'

try:
    from swirl.banner import SWIRL_BANNER
except Exception:  # allow running outside the django source tree
    SWIRL_BANNER = ''


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SP_FILE = os.path.join(SCRIPT_DIR, 'SearchProviders', 'preloaded.json')
DEFAULT_AIP_FILE = os.path.join(SCRIPT_DIR, 'AIProviders', 'preloaded.json')


# ---------------------------------------------------------------------------
# Fingerprinting / matching
# ---------------------------------------------------------------------------

_TLD_SUFFIXES = ('.com', '.org', '.io', '.net', '.ai', '.cloud')


def _normalise(s):
    '''Lower-case + strip TLDs + remove punctuation.'''
    s = s.lower()
    for suffix in _TLD_SUFFIXES:
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    s = re.sub(r'[\s\-_\./]+', '', s)
    return s


def _fingerprint_pair(name):
    '''
    Return (left, right) normalised tokens. ``left`` is the type token
    (e.g. ``Articles``, ``Tasks``); ``right`` is the source/vendor
    token (e.g. ``arxiv``, ``atlassian trello``). Parenthetical
    qualifiers are stripped before splitting.

    Names without a " - " separator collapse to ('', whole_name).
    '''
    if not name:
        return '', ''
    s = re.sub(r'\s*\([^)]*\)', '', name)
    if ' - ' in s:
        left, right = s.split(' - ', 1)
        return _normalise(left), _normalise(right)
    return '', _normalise(s)


def _pair_match(target, candidate):
    '''
    Score how well a candidate (left, right) matches target (left, right).
    Returns:
      ('exact', 2)     — right tokens equal AND left tokens equal
      ('exact_right', 1) — right tokens equal, left tokens differ
      ('substring', 1) — one right is a substring of the other AND
                         left tokens equal (or one is empty)
      ('substring_right', 0) — one right is a substring of the other,
                         left tokens differ
      (None, -1)       — no match
    '''
    t_left, t_right = target
    c_left, c_right = candidate
    if not t_right or not c_right:
        return None, -1
    if t_right == c_right:
        if t_left == c_left or not t_left or not c_left:
            return 'exact', 2
        return 'exact_right', 1
    if t_right in c_right or c_right in t_right:
        if t_left == c_left or not t_left or not c_left:
            return 'substring', 1
        return 'substring_right', 0
    return None, -1


def _resolve_matches(preloaded_entries, rows):
    '''
    Two-pass matching:
      1. Best-score match (exact-pair beats exact-right beats substring).
      2. For each preloaded entry, pick the highest-scoring still-free
         candidate. Ties at the highest score are ambiguous.

    Returns a list of (preloaded_index, row_or_None, status_str_or_None)
    aligned with preloaded_entries.
    '''
    targets = [_fingerprint_pair(e.get('name', '')) for e in preloaded_entries]
    cand = [(row, _fingerprint_pair(row.get('name', ''))) for row in rows]

    # For each preloaded entry, rank all candidates.
    ranked_per_entry = []
    for tgt in targets:
        scored = []
        for row, cfp in cand:
            tier, score = _pair_match(tgt, cfp)
            if tier is not None:
                scored.append((score, tier, row))
        scored.sort(key=lambda x: -x[0])
        ranked_per_entry.append(scored)

    assigned = {}  # preloaded_idx -> (row, tier)
    taken = set()  # row id

    # Process preloaded entries in order of their best score (highest
    # first) so high-confidence matches lock in before weaker ones can
    # steal their rows.
    order = sorted(
        range(len(preloaded_entries)),
        key=lambda i: -(ranked_per_entry[i][0][0] if ranked_per_entry[i] else -1),
    )
    for idx in order:
        scored = [(s, tier, row) for (s, tier, row) in ranked_per_entry[idx]
                  if row.get('id') not in taken]
        if not scored:
            assigned[idx] = (None, None)
            continue
        top_score = scored[0][0]
        top = [item for item in scored if item[0] == top_score]
        if len(top) > 1:
            assigned[idx] = (None, 'ambiguous')
            continue
        _, tier, row = top[0]
        assigned[idx] = (row, tier)
        taken.add(row.get('id'))

    return [(i, *assigned[i]) for i in range(len(preloaded_entries))]


# ---------------------------------------------------------------------------
# Diff / payload helpers
# ---------------------------------------------------------------------------

def _normalise_tags(tags):
    if tags is None:
        return []
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(',') if t.strip()]
    return list(tags)


def _format_diff(label, before, after):
    cur_name, cur_tags = before
    new_name, new_tags = after
    parts = []
    if cur_name != new_name:
        parts.append(f'name: {cur_name!r} -> {new_name!r}')
    if cur_tags != new_tags:
        parts.append(f'tags: {cur_tags!r} -> {new_tags!r}')
    return f'  [{label}] ' + '; '.join(parts) if parts else f'  [{label}] (in sync)'


def _load_json(path):
    if not os.path.isfile(path):
        print(f'{module_name}: preloaded file not found: {path}')
        sys.exit(2)
    with open(path, 'r') as f:
        return json.load(f)


def _fetch_all(base_url, list_path, auth):
    '''GET the (paginated) collection and return a flat list of row dicts.'''
    rows = []
    url = base_url.rstrip('/') + list_path
    while url:
        resp = requests.get(url, auth=auth,
                            headers={'Accept': 'application/json'})
        if resp.status_code != HTTPStatus.OK:
            raise RuntimeError(
                f'GET {url} failed: {resp.status_code} {resp.reason}'
            )
        payload = resp.json()
        if isinstance(payload, list):
            rows.extend(payload)
            url = None
        else:
            rows.extend(payload.get('results', []))
            url = payload.get('next')
    return rows


# ---------------------------------------------------------------------------
# Per-collection sync
# ---------------------------------------------------------------------------

def sync_collection(label, base_url, list_path, item_path_fmt,
                    preloaded_entries, auth, match_mode='fingerprint',
                    dry_run=True, quiet=False):
    '''
    Returns (synced, skipped, errors).
    '''
    try:
        rows = _fetch_all(base_url, list_path, auth)
    except RuntimeError as err:
        print(f'{module_name}: {err}')
        return 0, 0, 1

    rows_by_id = {r.get('id'): r for r in rows}

    # Pre-compute matches when fingerprinting so high-confidence matches
    # lock in before weaker ones can steal their rows.
    if match_mode == 'fingerprint':
        resolutions = _resolve_matches(preloaded_entries, rows)
    else:
        resolutions = None

    synced = 0
    skipped = 0
    errors = 0

    for idx_zero, entry in enumerate(preloaded_entries):
        idx = idx_zero + 1
        desired_name = entry.get('name')
        desired_tags = _normalise_tags(entry.get('tags', []))

        # Pick the candidate row according to match_mode.
        row = None
        match_note = ''
        if match_mode == 'position':
            row = rows_by_id.get(idx) or rows_by_id.get(str(idx))
            match_note = f'pk={idx}'
        else:
            _, row, status = resolutions[idx_zero]
            if status == 'ambiguous':
                if not quiet:
                    print(f'  [{label}] AMBIGUOUS match for {desired_name!r} — skipping')
                skipped += 1
                continue
            if row is None:
                if not quiet:
                    print(f'  [{label}] NO MATCH for {desired_name!r} — skipping')
                skipped += 1
                continue
            match_note = f"pk={row.get('id')} via {status} match"

        if row is None:
            if not quiet:
                print(f'  [{label}] pk={idx}: NOT IN DB — skipping {desired_name!r}')
            skipped += 1
            continue

        cur_name = row.get('name')
        cur_tags = _normalise_tags(row.get('tags'))
        unchanged = (cur_name == desired_name) and (cur_tags == desired_tags)
        if unchanged:
            if not quiet:
                print(f'  [{label} {match_note}] {desired_name!r}: in sync')
            continue

        if not quiet:
            print(_format_diff(
                f'{label} {match_note}',
                (cur_name, cur_tags),
                (desired_name, desired_tags),
            ))

        if dry_run:
            synced += 1
            continue

        # Build the PUT payload: round-trip every field, override only
        # name + tags, and drop server-managed read-onlys.
        payload = dict(row)
        payload['name'] = desired_name
        payload['tags'] = desired_tags
        for read_only in ('owner', 'date_created', 'date_updated', 'id'):
            payload.pop(read_only, None)

        item_url = base_url.rstrip('/') + item_path_fmt.format(pk=row.get('id'))
        try:
            put = requests.put(
                item_url,
                auth=auth,
                headers={'Content-Type': 'application/json'},
                json=payload,
            )
        except requests.RequestException as err:
            print(f'  [{label} pk={row.get("id")}] PUT failed: {err}')
            errors += 1
            continue

        if put.status_code in (HTTPStatus.OK, HTTPStatus.ACCEPTED):
            synced += 1
        else:
            errors += 1
            body = put.text[:300]
            print(
                f'  [{label} pk={row.get("id")}] PUT {item_url} returned '
                f'{put.status_code} {put.reason}: {body}'
            )

    return synced, skipped, errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv):
    print(f'{SWIRL_BANNER}')
    print()

    parser = argparse.ArgumentParser(
        description=(
            'Sync name and tags of SearchProvider / AIProvider rows from '
            'preloaded.json into a running SWIRL DB. Only name and tags '
            'are touched.'
        )
    )
    parser.add_argument('-u', '--username', required=True,
                        help='SWIRL username (must own the rows to be updated)')
    parser.add_argument('-p', '--password', required=True, help='SWIRL password')
    parser.add_argument('-s', '--swirl', default='http://localhost:8000/',
                        help='base URL of the SWIRL server (default: %(default)s)')
    parser.add_argument('--sp-file', default=DEFAULT_SP_FILE,
                        help='path to SearchProviders/preloaded.json '
                             '(default: %(default)s)')
    parser.add_argument('--aip-file', default=DEFAULT_AIP_FILE,
                        help='path to AIProviders/preloaded.json '
                             '(default: %(default)s)')
    parser.add_argument('--match', choices=('fingerprint', 'position'),
                        default='fingerprint',
                        help='how to map preloaded entries to DB rows. '
                             '"fingerprint" (default) is safe for drifted '
                             'DBs; "position" assumes the DB was loaded '
                             'directly from this preloaded.json with no '
                             'subsequent inserts.')
    parser.add_argument('--apply', action='store_true',
                        help='actually write changes (default: dry-run)')
    parser.add_argument('--only', choices=('sp', 'aip', 'both'), default='both',
                        help='which collection to sync (default: %(default)s)')
    parser.add_argument('--quiet', action='store_true',
                        help='print only the final summary line')
    args = parser.parse_args(argv[1:])

    auth = HTTPBasicAuth(args.username, args.password)
    dry_run = not args.apply

    mode_label = 'DRY-RUN' if dry_run else 'APPLY'
    print(f'{module_name}: target={args.swirl}  match={args.match}  mode={mode_label}')
    print(f'  SearchProviders: {args.sp_file}')
    print(f'  AIProviders:     {args.aip_file}')
    print()

    sp_synced = sp_skipped = sp_errors = 0
    aip_synced = aip_skipped = aip_errors = 0

    if args.only in ('sp', 'both'):
        print('=== SearchProviders ===')
        sp_entries = _load_json(args.sp_file)
        sp_synced, sp_skipped, sp_errors = sync_collection(
            'SP',
            args.swirl,
            '/swirl/searchproviders/',
            '/swirl/searchproviders/{pk}/',
            sp_entries,
            auth,
            match_mode=args.match,
            dry_run=dry_run,
            quiet=args.quiet,
        )
        print()

    if args.only in ('aip', 'both'):
        print('=== AIProviders ===')
        aip_entries = _load_json(args.aip_file)
        aip_synced, aip_skipped, aip_errors = sync_collection(
            'AIP',
            args.swirl,
            '/swirl/aiproviders/',
            '/swirl/aiproviders/{pk}/',
            aip_entries,
            auth,
            match_mode=args.match,
            dry_run=dry_run,
            quiet=args.quiet,
        )
        print()

    verb = 'would sync' if dry_run else 'synced'
    print(
        f'{module_name}: SP {verb}={sp_synced} skipped={sp_skipped} '
        f'errors={sp_errors}; AIP {verb}={aip_synced} skipped={aip_skipped} '
        f'errors={aip_errors}'
    )
    if dry_run and (sp_synced or aip_synced):
        print(f'{module_name}: rerun with --apply to commit the changes')
    return 1 if (sp_errors or aip_errors) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
