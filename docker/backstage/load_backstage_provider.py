#!/usr/bin/env python
'''
Load SearchProviders/backstage.json into the database, reconcile the preloaded
providers that belong to the federated lane, and make sure the admin user has an
API token (TECH_DESIGN_swirl_for_backstage.md section 3.8).

Idempotent: run on every container start. Providers are matched by name, so a
restart updates the shipped fields and leaves anything an operator edited in the
admin under a different name alone.

Why the reconciliation is here rather than in the seed database. The container
seeds /data/db.sqlite3 from the shipped db.sqlite3.dist, which is a binary
artifact regenerated only by the .github/workflows/db-dist.yml workflow (a full
install, `swirl.py setup`, a running server and `swirl_load.py`). Any edit to
SearchProviders/preloaded.json is therefore invisible to the image until that
workflow runs and its pull request merges. The `backstage` tag the engine
module's federated lane selects on, and the placeholder scope templates WP05
added, both landed in preloaded.json after the current dist was built, so the
shipped `Code - GitHub` row still carried ["GitHub", "Code", "Dev"] and an
unscoped template. Reconciling from preloaded.json on every start makes the
image correct whatever the age of the dist database.

What it will and will not touch, for a provider named in preloaded.json with the
`backstage` tag:

  * the tag is added to whatever tags the row already has, never replacing them;
  * the scope template is copied over only when the row is inactive and still
    unscoped, so an operator who filled in their org, repo or space, or who
    switched the provider on, keeps their edit;
  * a provider an operator deleted is not recreated.

No secrets here. The admin password is only set when SWIRL_ADMIN_PASSWORD is
supplied in the environment; otherwise the shipped db.sqlite3.dist admin is left
exactly as it is.
'''

import json
import os
import sys

if __name__ == '__main__':
    # Bootstrap Django when run as the entrypoint's script. Under pytest the
    # module is imported with the apps already loaded, so this must not run.
    sys.path.insert(0, os.environ.get('SWIRL_APP_DIR', '/app'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
    import django

    django.setup()

from django.contrib.auth.models import User  # noqa: E402
from rest_framework.authtoken.models import Token  # noqa: E402

from swirl.models import SearchProvider  # noqa: E402
from swirl.scope import is_scoped  # noqa: E402

APP_DIR = os.environ.get('SWIRL_APP_DIR', '/app')
PROVIDER_FILE = os.path.join(APP_DIR, 'SearchProviders', 'backstage.json')
PRELOADED_FILE = os.path.join(APP_DIR, 'SearchProviders', 'preloaded.json')
ADMIN_USERNAME = os.environ.get('SWIRL_ADMIN_USER', 'admin')

#: The tag the Backstage engine module's federated lane selects on. Its default
#: federated.providerTags is ["backstage"], so a provider without this tag
#: cannot join the lane whatever else is right about it.
FEDERATED_TAG = 'backstage'


def admin_user():
    user = User.objects.filter(username=ADMIN_USERNAME).first()
    if user is None:
        user = User.objects.create_superuser(username=ADMIN_USERNAME, email='')
        print('load_backstage_provider: created superuser {}'.format(ADMIN_USERNAME))
    password = os.environ.get('SWIRL_ADMIN_PASSWORD', '')
    if password:
        user.set_password(password)
        user.save()
        print('load_backstage_provider: admin password set from the environment')
    return user


def load_provider(owner):
    with open(PROVIDER_FILE, encoding='utf-8') as handle:
        entry = json.load(handle)
    fields = {
        'owner': owner,
        'shared': True,
        'active': entry.get('active', True),
        'default': entry.get('default', True),
        'connector': entry['connector'],
        'url': entry.get('url', ''),
        'query_template': entry.get('query_template', ''),
        'query_template_json': entry.get('query_template_json', {}),
        'post_query_template': entry.get('post_query_template', {}),
        'http_request_headers': entry.get('http_request_headers', {}),
        'page_fetch_config_json': entry.get('page_fetch_config_json', {}),
        'query_processors': entry.get('query_processors', []),
        'query_mappings': entry.get('query_mappings', ''),
        'result_grouping_field': entry.get('result_grouping_field', ''),
        'result_processors': entry.get('result_processors', []),
        'response_mappings': entry.get('response_mappings', ''),
        'result_mappings': entry.get('result_mappings', ''),
        'results_per_query': entry.get('results_per_query', 100),
        'tags': entry.get('tags', []),
    }
    provider, created = SearchProvider.objects.update_or_create(
        name=entry['name'], defaults=fields)
    print('load_backstage_provider: {} SearchProvider {} (id {})'.format(
        'created' if created else 'updated', provider.name, provider.id))
    return provider


def federated_entries(path=None):
    '''The preloaded.json entries that carry the federated lane tag.'''
    path = path or PRELOADED_FILE
    try:
        with open(path, encoding='utf-8') as handle:
            entries = json.load(handle)
    except (OSError, ValueError) as err:
        print('load_backstage_provider: cannot read {}: {}'.format(path, err))
        return []
    wanted = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get('name'):
            continue
        tags = [str(tag).strip().lower() for tag in (entry.get('tags') or [])]
        if FEDERATED_TAG in tags:
            wanted.append(entry)
    return wanted


def reconcile_federated_providers(path=None):
    '''Bring the shipped federated providers back in line with preloaded.json.

    Returns the list of (name, [what changed]) for the rows that were written,
    so the entrypoint log says exactly what the start had to repair.
    '''
    changed = []
    for entry in federated_entries(path):
        name = entry['name']
        provider = SearchProvider.objects.filter(name=name).first()
        if provider is None:
            # Deleted on purpose by an operator, or a provider this database
            # never had. Recreating it on every start would be a nuisance.
            continue
        notes = []

        tags = list(provider.tags or [])
        if FEDERATED_TAG not in [str(tag).strip().lower() for tag in tags]:
            tags.append(FEDERATED_TAG)
            provider.tags = tags
            notes.append('tag')

        template = entry.get('query_template') or ''
        template_json = entry.get('query_template_json') or {}
        if not provider.active and not is_scoped(provider):
            shipped = SearchProvider(
                name=name, tags=tags, query_template=template,
                query_template_json=template_json,
                config=entry.get('config') or {})
            if is_scoped(shipped):
                provider.query_template = template
                provider.query_template_json = template_json
                notes.append('scope template')

        if notes:
            provider.save()
            changed.append((name, notes))
            print('load_backstage_provider: reconciled {} ({})'.format(
                name, ', '.join(notes)))
    if not changed:
        print('load_backstage_provider: federated providers already in line '
              'with preloaded.json')
    return changed


def ensure_token(user):
    token, created = Token.objects.get_or_create(user=user)
    print('load_backstage_provider: api token for {} is {}'.format(
        user.username, 'new' if created else 'existing'))
    if os.environ.get('SWIRL_PRINT_ADMIN_TOKEN', '').lower() == 'true':
        print('load_backstage_provider: token {}'.format(token.key))
    return token


def main():
    user = admin_user()
    load_provider(user)
    reconcile_federated_providers()
    ensure_token(user)
    return 0


if __name__ == '__main__':
    sys.exit(main())
