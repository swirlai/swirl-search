#!/usr/bin/env python
'''
Load SearchProviders/backstage.json into the database and make sure the admin
user has an API token (TECH_DESIGN_swirl_for_backstage.md section 3.8).

Idempotent: run on every container start. The provider is matched by name, so a
restart updates the shipped fields and leaves anything an operator edited in the
admin under a different name alone.

No secrets here. The admin password is only set when SWIRL_ADMIN_PASSWORD is
supplied in the environment; otherwise the shipped db.sqlite3.dist admin is left
exactly as it is.
'''

import json
import os
import sys

sys.path.insert(0, os.environ.get('SWIRL_APP_DIR', '/app'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')

import django  # noqa: E402

django.setup()

from django.contrib.auth.models import User  # noqa: E402
from rest_framework.authtoken.models import Token  # noqa: E402

from swirl.models import SearchProvider  # noqa: E402

PROVIDER_FILE = os.path.join(
    os.environ.get('SWIRL_APP_DIR', '/app'), 'SearchProviders', 'backstage.json')
ADMIN_USERNAME = os.environ.get('SWIRL_ADMIN_USER', 'admin')


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
    ensure_token(user)
    return 0


if __name__ == '__main__':
    sys.exit(main())
