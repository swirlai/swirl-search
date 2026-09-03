'''
@author:     Sid Probstein
@contact:    sid@swirl.today

Query processing for the SWIRL for Backstage index
(TECH_DESIGN_swirl_for_backstage.md section 3.4).

Why this exists. Gate zero asks for `foo-bar.com` at rank 1, which is the
Backstage issue about dotted hostnames. Re-running the gauntlet against the
released image showed the case failing on the shipped path while passing in
process: AdaptiveQueryProcessor runs clean_string(), which keeps `-` but turns
`.` into a space, so the provider was asked for `foo-bar com`. The bare token
`com` then matched inside every `recommendation-*` title through the title_ngram
field and swamped the one exact hit.

BackstageQueryProcessor is AdaptiveQueryProcessor with a different character
filter: the tag adaptation, the NOT handling and the mappings are inherited
unchanged, and only the cleaning step is replaced. Punctuation that carries
meaning inside a Backstage identifier is kept when it is between two
identifier characters:

    .  hostnames and dotted names        foo-bar.com
    -  the usual entity name separator   tech-radar
    _  snake case names                  my_service
    /  entity references and locations   component/petstore
    :  Backstage compound refs           component:default/petstore

Everything else is dropped rather than turned into a space, so nothing splits a
token that the index holds as one. Leading and trailing punctuation goes: a
trailing full stop is sentence punctuation, not part of the name.

Galaxy is untouched. Only SearchProviders/backstage.json names this processor.
'''

from celery.utils.log import get_task_logger

from swirl.processors.adaptive import AdaptiveQueryProcessor
from swirl.processors.utils import remove_tags

logger = get_task_logger(__name__)

#############################################
#############################################

#: Punctuation kept when it sits between two identifier characters.
INNER_PUNCTUATION = '.-_/:'

#: Punctuation kept anywhere, matching clean_string()'s own allowances for
#: quoting and for the currency and percent signs.
KEPT_ANYWHERE = '"\'’$%'


def clean_string_keep_identifiers(query_string):
    '''Strip markup and punctuation but keep what holds an identifier together.

    Unlike clean_string(), a character that is dropped is dropped rather than
    replaced with a space, so `foo-bar.com` stays one token instead of becoming
    two. INNER_PUNCTUATION survives only between two identifier characters, so
    a trailing full stop or a leading slash still goes.
    '''
    if query_string is None:
        return ''
    text = remove_tags(query_string)
    if not isinstance(text, str):
        return ''

    out = []
    for token in text.split():
        # A leading minus is the inherited "not this term" syntax, so it is kept
        # and the rest of the token is cleaned without it.
        negated = token.startswith('-') and len(token) > 1
        if negated:
            token = token[1:]
        characters = []
        for position, character in enumerate(token):
            if character.isalnum() or character in KEPT_ANYWHERE:
                characters.append(character)
                continue
            if character not in INNER_PUNCTUATION:
                continue
            previous = token[position - 1] if position else ''
            following = token[position + 1] if position + 1 < len(token) else ''
            if previous.isalnum() and following.isalnum():
                characters.append(character)
        cleaned = ''.join(characters)
        if not cleaned or cleaned in ('-', '--'):
            continue
        out.append('-' + cleaned if negated else cleaned)
    return ' '.join(out)


class BackstageQueryProcessor(AdaptiveQueryProcessor):

    type = 'BackstageQueryProcessor'

    def clean(self, query_string):
        return clean_string_keep_identifiers(query_string)
