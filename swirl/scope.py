'''
Scope restriction for SearchProviders.

Some sources return the whole tenant when queried without a scope: a GitHub
search with no repo: or org: qualifier, a Confluence CQL with no space, a Jira
JQL with no project. Activating such a provider federates every query across
everything the shared credential can read, which is almost never what the
operator meant.

SCOPE_RULES maps a provider tag to a regular expression that a scoped query
must match. The check applies only when the provider is active and one of its
tags has a rule. It runs in three places, all through check_scope():

  * SearchProvider.clean()             model-level, so loaders and shells hit it
  * SearchProviderSerializer.validate() the REST API
  * SearchProviderAdminForm.clean()     the Django admin

An operator who genuinely wants an unrestricted source sets

    config = {"swirl": {"scope_unrestricted": true}}

on the provider. That allows activation, logs a warning on every federate, and
stamps payload.shared_visibility = "unrestricted" on the results so the
consumer can label them.
'''

import json
import logging
import re

logger = logging.getLogger(__name__)

# Tag (lower case) -> regular expression a scoped query must contain.
SCOPE_RULES = {
    'github': r'(repo:|org:|user:)',
    'confluence': r'(spaceKey=|space=|cql=.*space)',
    'jira': r'(project\s*(=|in)|jql=.*project)',
    'gitlab': r'(group_id=|projects/|groups/)',
}

SCOPE_UNRESTRICTED_KEY = 'scope_unrestricted'

SCOPE_ERROR_TEMPLATE = (
    'This source requires a scope restriction before it can be activated. '
    'Add one to query_template or query_template_json - for the "{tag}" tag it '
    'must match {pattern} - or, to search the whole source on purpose, set '
    'config to {{"swirl": {{"scope_unrestricted": true}}}}. See docs/security.'
)


def scope_rules_for(provider):
    '''Return [(tag, pattern)] for every tag on the provider that has a rule.'''
    rules = []
    for tag in (provider.tags or []):
        if not isinstance(tag, str):
            continue
        pattern = SCOPE_RULES.get(tag.strip().lower())
        if pattern:
            rules.append((tag, pattern))
    return rules


def is_scope_unrestricted(provider):
    '''True when the provider carries the explicit unrestricted bypass flag.'''
    config = getattr(provider, 'config', None) or {}
    if not isinstance(config, dict):
        return False
    swirl_config = config.get('swirl') or {}
    if not isinstance(swirl_config, dict):
        return False
    return bool(swirl_config.get(SCOPE_UNRESTRICTED_KEY))


def _scope_text(provider):
    '''The provider text a scope restriction may live in.'''
    parts = [provider.query_template or '']
    template_json = provider.query_template_json
    if template_json:
        if isinstance(template_json, str):
            parts.append(template_json)
        else:
            try:
                parts.append(json.dumps(template_json))
            except (TypeError, ValueError):
                parts.append(str(template_json))
    return ' '.join(parts)


def is_scoped(provider):
    '''True when the templates already carry the scope this provider's tags need.

    The active flag is deliberately not consulted, so this answers "would
    activating this be allowed", which is what an installer reconciling a
    shipped provider has to know before it decides whether to replace a
    template. check_scope() is the same question asked of an active provider.
    '''
    rules = scope_rules_for(provider)
    if not rules:
        return True
    if is_scope_unrestricted(provider):
        return True
    text = _scope_text(provider)
    return all(re.search(pattern, text, re.IGNORECASE) for _tag, pattern in rules)


def check_scope(provider):
    '''Return an error message when this provider may not be activated, else None.

    The single source of truth for the rule. Callers raise whichever
    ValidationError their layer expects; see the module docstring.
    '''
    if not provider.active:
        return None

    rules = scope_rules_for(provider)
    if not rules:
        return None

    if is_scope_unrestricted(provider):
        return None

    text = _scope_text(provider)
    unmatched = [
        (tag, pattern) for tag, pattern in rules
        if not re.search(pattern, text, re.IGNORECASE)
    ]
    if not unmatched:
        return None

    tag, pattern = unmatched[0]
    return SCOPE_ERROR_TEMPLATE.format(tag=tag, pattern=pattern)


def warn_if_unrestricted(provider):
    '''Log a warning when an unrestricted provider is about to be federated.

    Called once per federate so the bypass is visible in the logs every time it
    is used, not only when it is set.
    '''
    if not scope_rules_for(provider):
        return False
    if not is_scope_unrestricted(provider):
        return False
    logger.warning(
        f'SearchProvider "{provider.name}" is federating without a scope '
        f'restriction (config.swirl.{SCOPE_UNRESTRICTED_KEY} is true). Every '
        f'query reaches everything this credential can read.'
    )
    return True


def mark_shared_visibility(provider, results):
    '''Stamp payload.shared_visibility on results from an unrestricted provider.'''
    if not results:
        return 0
    if not scope_rules_for(provider) or not is_scope_unrestricted(provider):
        return 0
    marked = 0
    for result in results:
        if not isinstance(result, dict):
            continue
        payload = result.get('payload')
        if payload is None:
            payload = {}
            result['payload'] = payload
        if not isinstance(payload, dict):
            continue
        payload['shared_visibility'] = 'unrestricted'
        marked += 1
    return marked
