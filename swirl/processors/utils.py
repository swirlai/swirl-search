'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

#############################################
#############################################

def create_result_dictionary():
    """
    Create an empty ressult dictionary, when entries are made this dictionary, the type must
    correspond w/ the type that will be mapped from in results_mapping, if the types do not
    agree, the mapped values will not be added to the results.
    """

    dict_result = {}
    dict_result['swirl_rank'] = 0
    dict_result['swirl_score'] = 0.0
    dict_result['searchprovider'] = ""
    dict_result['searchprovider_rank'] = 0
    dict_result['title'] = ""
    dict_result['url'] = ""
    dict_result['body'] = ""
    dict_result['date_published'] = ""
    dict_result['date_retrieved'] = ""
    dict_result['author'] = ""
    dict_result['title_hit_highlights'] = []
    dict_result['body_hit_highlights'] = []
    dict_result['payload'] = {}
    return dict_result

#############################################
# fix for https://github.com/swirlai/swirl-search/issues/34

from ..nltk import ps

import json

def decode_single_quote_json(json_string):
    """
        Replace single quotes with double quotes and
        decode to a dictionary.
        Log error and return empty on failure
    """
    if not json_string:
        return {}

    json_string = json_string.replace("'", '"')
    try:
        return json.JSONDecoder().decode(json_string)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {e}")
        return {}

def stem_string(s):

    nl=[]
    for s in s.strip().split():
        nl.append(ps.stem(s))

    return ' '.join(nl)

#############################################

def has_numeric(string_or_list):

    list_thing = []
    if type(string_or_list) == str:
        list_thing = string_or_list.strip().split(' ')
    if type(string_or_list) == list:
        list_thing = string_or_list
    if list_thing == []:
        return False

    for t in list_thing:
        if t.isnumeric():
            return True
        else:
            for c in t:
                if c.isnumeric():
                    return True
                # end if
            # end for
        # end if
    # end for

    return False

#############################################

def remove_numeric(string_or_list):

    list_thing = []
    if type(string_or_list) == str:
        list_thing = string_or_list.strip().split(' ')
    if type(string_or_list) == list:
        list_thing = string_or_list
    if list_thing == []:
        return list_thing

    list_new = []
    for t in list_thing:
        if t.isalpha():
            list_new.append(t)
        else:
            new_c = ''
            for c in t:
                if c.isalpha():
                    new_c = new_c + c
                # end if
            # end for
            if new_c:
                list_new.append(new_c)
        # end if
    # end for

    if type(string_or_list) == str:
        return ' '.join(list_new)

    return list_new

#############################################

from django.conf import settings

SWIRL_HIGHLIGHT_START_CHAR = getattr(settings, 'SWIRL_HIGHLIGHT_START_CHAR', '*')
SWIRL_HIGHLIGHT_END_CHAR = getattr(settings, 'SWIRL_HIGHLIGHT_END_CHAR', '*')

import re

WORD_CHAR_PAT = r'[A-Za-z0-9]+'

def highlight_list(target_str, word_list):
    # Create canonical word list in lower case
    source_words = [w.lower() for w in word_list]

    ret = target_str

    # create a unique list of words from the target, so that we only highlight each once.
    all_words = []
    seen_words = set()
    for aw in re.findall(WORD_CHAR_PAT, target_str):
        aw_lower = aw.lower()
        if aw_lower not in seen_words:
            seen_words.add(aw_lower)
            all_words.append(aw)

    for word in all_words:
        # If the word matches any of the source words, add it to the list of highlighted words
        if word.lower() in source_words:
            ret = ret.replace(word,f'{SWIRL_HIGHLIGHT_START_CHAR}{word}{SWIRL_HIGHLIGHT_END_CHAR}')

    return ret

#############################################

def position_dict(text, word_list):
    if type(word_list) != list:
        return []
    if word_list == []:
        return []
    positions = {word: [] for word in word_list}
    words = text.split()
    for i, word in enumerate(words):
        if word in word_list:
            positions[word].append(i)
    return positions

#############################################
# fix for https://github.com/swirlai/swirl-search/issues/33

from swirl.bs4 import bs

# Function to remove tags
def remove_tags(html):

    # parse html content
    soup = bs(html, "html.parser")

    for data in soup(['style', 'script']):
        # Remove tags
        data.decompose()

    # return data by retrieving the tag content
    return ' '.join(soup.stripped_strings)

# Function to remove tags
def extract_text_from_tags(html,tag):
    # parse html content
    soup = bs(html, "html.parser")
    ret = []
    for t in soup.find_all(tag):
        ret.append(t.text)
    # return data by retrieving the tag content
    return ret

#############################################

def clean_string(s):

    # remove entities and tags
    s1 = remove_tags(s)

    # parse s1 carefully
    module_name = 'clean_string'
    string_clean = ""
    try:
        for ch in s1.strip():
            # numbers
            if ch.isnumeric():
                string_clean = string_clean + ch
                continue
            # letters
            if ch.isalpha():
                string_clean = string_clean + ch
                continue
            if ch in [ '"', "'", '’', ' ', '-', '$', '%', '?', ':', '(', ')' ]:
                string_clean = string_clean + ch
                continue
            if ch in [ '\n', '!', ';', '/', '_', '|', '.' ]:
                string_clean = string_clean + ' '
        # end for
    except NameError as err:
        return(f'{module_name}: Error: NameError: {err}')
    except TypeError as err:
        return(f'{module_name}: Error: TypeError: {err}')
    # remove extra spaces
    if '  ' in string_clean:
        while '  ' in string_clean:
            string_clean = string_clean.replace('  ', ' ')
    # end if
    # remove as single token
    string_cleaner = []
    for t in string_clean.split():
        if t not in [ '-', '--']:
            string_cleaner.append(t)
    return ' '.join(string_cleaner)

#############################################

def match_all(list_find, list_targets):

    match_list = []
    if not list_targets:
        return match_list

    if not list_find:
        return match_list

    find = ' '.join(list_find)

    p = 0
    while p < len(list_targets):
        if find.lower() in ' '.join(list_targets[p:p+len(list_find)]).lower():
            match_list.append(p)
        p = p + 1

    return match_list

#############################################

def match_any(list_find, list_targets):

    for item in list_find:
        for target in list_targets:
            if item.lower() in target.lower():
                return True

    return False

#############################################

def bigrams(list_terms):

    if not list_terms:
        return []

    if len(list_terms) == 0:
        return []

    if len(list_terms) <= 2:
        return list_terms

    bigrams = []
    p = 0
    while p < len(list_terms) - 1:
        bigrams.append(list_terms[p:p+2])
        p = p + 1

    return bigrams

#############################################

import logging as logger

def capitalize(list_lower, list_unknown):

    if not list_lower:
        return list_lower

    if not list_unknown:
        return list_unknown

    if len(list_lower) != len(list_unknown):
        logger.error("capitalize: inputs were not same length")
        return list_lower

    list_capitalized = []
    for m in list_unknown:
        if m[0].isupper():
            list_capitalized.append(list_lower[list_unknown.index(m)][0].upper() + list_lower[list_unknown.index(m)][1:])
        else:
            list_capitalized.append(list_lower[list_unknown.index(m)])

    return list_capitalized

#############################################

def capitalize_search(list_lower, list_unknown):
    """

    """

    if type(list_lower) != list:
        return None

    if type(list_unknown) != list:
        return None

    if not list_lower:
        return list_lower

    if not list_unknown:
        return list_unknown

    list_capitalized = []
    for i in list_lower:
        loc_list = match_all([i], list_unknown)
        capped = False
        for loc in loc_list:
            if list_unknown[loc][0].isupper():
                list_capitalized.append(i[0].upper() + i[1:])
                capped = True
                break
        if capped:
            continue
        list_capitalized.append(i)
    # end for

    return list_capitalized


def json_to_flat_string(json_data, separator=' ', deadman=None):
    """
    A flat string representation of any JSON object.
    use deadman to limit recursion into JSON objects.
    Separator the character the individual data pieces will be joined on.
    """
    if isinstance(json_data, str):
        return json_data

    if deadman:
        deadman = deadman - 1
        if deadman <= 0:
            raise ValueError('recursion limit reached in JSON structure')

    if isinstance(json_data, dict):
        return separator.join(json_to_flat_string(v, separator=separator, deadman=deadman) for v in json_data.values())
    elif isinstance(json_data, list):
        return separator.join(json_to_flat_string(v, separator=separator, deadman=deadman) for v in json_data)
    elif isinstance(json_data, (int, float, bool)):
        return str(json_data)
    elif json_data is None:
        return 'null'
    else:
        raise TypeError(f"Unsupported JSON data type: {type(json_data)}")

def str_replace_all_keys(s, d):
    """
    Simple one pass replace, does not handle nested replacement.
    """
    if len(s) <= 0 or not d:
        return s
    ret = s
    for k in d.keys():
        ret = ret.replace("{"+k+"}", d[k])
    return ret


#############################################
def str_tok_get_prefixes(toks, sep = ' '):
    """
    given a list of tokens, get a list of the
    of token lists, one for each pre-fix of
    the input.
    """
    lt = len(toks)
    if not toks or lt <= 0:
        return []
    ret = []
    for i in range(lt):
        for r  in range (lt - 1, i - 1, -1 ):
            prfx = toks[i : r + 1]
            ret.append(' '.join(prfx))
    return ret


#############################################

def get_mappings_dict(mappings):

    '''
    accepts: any provider mapping
    returns: dict of the mappings by swirl_key
    warns if any swirl_key is repeated
    '''

    module_name = 'get_mappings'

    dict_mappings = {}

    mappings = mappings.split(',')
    if mappings:
        for mapping in mappings:
            stripped_mapping = mapping.strip()
            if '=' in stripped_mapping:
                swirl_key = stripped_mapping[:stripped_mapping.find('=')]
                source_key = stripped_mapping[stripped_mapping.find('=')+1:]
            else:
                source_key = None
                swirl_key = stripped_mapping
            # end if
            if swirl_key in dict_mappings:
                logger.warning(f"{module_name}: Warning: control mapping {swirl_key} found more than once, ignoring")
                continue
            dict_mappings[swirl_key] = source_key
        # end for
    # end if

    return dict_mappings

def str_safe_format(s, d):
    """
    Safer string replace, uses format, if there is a key error, attempts string replace.
    """
    if len(s) <=0 or not d:
        return s
    try:
        ret = s.format(**d)
    except KeyError:
        ret = str_replace_all_keys(s,d)
    return ret

from dateutil import parser

def _date_str_parse_to_timestamp(s):
    """
        try to parse the string as a date to a timestampe
    """
    ret = ""
    try:
        ret = str(parser.parse(str(s)))
    except Exception as x:
        logger.debug(f'{x} : unable to convert {s} as string to timestamp')
    return ret

import datetime as x_datetime
def _date_float_parse_to_timestamp(s):
    """
        convert to a string then to float and try to make a timestamp out of it.
    """
    ret = ""
    try:
        dtf = float(str(s))
        ret = str(x_datetime.datetime.fromtimestamp(dtf))
    except Exception as x:
        logger.debug(f'{x} : unable to convert {s} as float to timestamp')
    return ret

def date_str_to_timestamp(s):
    """
        Convert the input to a string and try to make a timestamp from it using known string formats
        and raw numeric values
    """
    ret = _date_str_parse_to_timestamp(s)
    if not ret: ret = _date_float_parse_to_timestamp(s)
    if not ret:
        logger.error(f'Unable to convert {s} to timestamp using any known type')
    return ret
