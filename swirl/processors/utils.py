'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

import re

#############################################    

def create_result_dictionary():

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
    dict_result['payload'] = {}
    return dict_result

#############################################

import copy

STOP_WORDS = ['and', 'not', 'or', 'a', 'an', 'the']
IMPORTANT_CHARS = ['$', '%']

def highlight(text, query_string):

    text2 = copy.copy(text)

    highlighted_text = text
    
    for term in query_string.strip().split():
        if term in STOP_WORDS:
            continue
        # update text3 which is a tokenized text2
        text3 = ""
        for ch in text2:
            if ch.isalnum():
                text3 = text3 + ch
            else:
                if ch in IMPORTANT_CHARS:
                    text3 = text3 + ch
                else:
                    text3 = text3 + ' '
            # end if
        # end for
        # get a list of the locations for this term
        hit_list = []
        if text3.lower().startswith(term.lower()):
            hit_list.append(0)
        re_term = term
        # escape characters that need to be regexable
        for c in IMPORTANT_CHARS:
            if c in re_term:
                re_term = re_term.replace(c, '\\' + c)
        if len(text3.strip().split()) > 1:
            hit_list = hit_list + [m.start() for m in re.finditer(' ' + re_term.lower() + ' ', text3.lower())]
            if text3.lower().endswith(term.lower()):
                hit_list.append(len(text3) - len(term) - 1)
        # print(hit_list)
        # highlight the hits
        if hit_list:
            last = 0
            highlighted_text = ""
            for hit in hit_list:
                if hit == 0:
                    highlighted_text = '*' + text2[:len(term)] + '*'
                    last = len(term)
                else:
                    if highlighted_text:
                        highlighted_text = highlighted_text + text2[last:hit+1] + '*' + text2[hit+1:hit+1+len(term)] + '*'
                    else:
                        highlighted_text = text2[last:hit+1] + '*' + text2[hit+1:hit+1+len(term)] + '*'
                    last = hit + 1 + len(term)
                    # end if
                # end if
                # print(highlighted_text)
            # end for
            if last < len(text2):
                highlighted_text = highlighted_text + text2[last:]
            # print(highlighted_text)
            # update text2
            text2 = highlighted_text  
            # end if
        # end if
              
    return highlighted_text

#############################################

from nltk.stem import PorterStemmer

ps = PorterStemmer()

def stem_string(s):
        
    nl=[]
    for s in s.strip().split():
        nl.append(ps.stem(s))

    return ' '.join(nl)

#############################################

def clean_string(s):
    list_tag_chars = [ '<', '>' ]
    module_name = 'clean_snippet'
    query_clean = ""
    last_ch = ""
    start_tag = False
    entity = False
    try:
        for ch in s.strip():
            if ch in list_tag_chars:
                if start_tag:
                    start_tag = False
                else:
                    start_tag = True
                    continue
            if start_tag:
                continue
            if ch == '&':
                entity = True
                continue
            if ch == ';' and entity:
                entity = False
                continue
            if entity:
                continue
            if ch.isalnum():
                query_clean = query_clean + ch
                continue
            else:
                # to do: handle $000 or $00,00 or $0.00
                # to do: handle x.y%
                if ch in [ '.', '"', "'", '?', '!' ]:
                    query_clean = query_clean + ch
                # else:
                #     if last_ch != ' ':
                #         query_clean = query_clean + ' '
                # end if
                # to do: preserve numbers, e.g. if in 0 then keep .,% or if $ or L(pound) etc proceeds a number
                if last_ch != ' ':
                    if ch == ' ':
                        query_clean = query_clean + ch
                        continue
                # end if
            # end if
            last_ch = ch
    except NameError as err:
        return(f'{module_name}: Error: NameError: {err}')
    except TypeError as err:
        return(f'{module_name}: Error: TypeError: {err}')
    # remove extra spaces
    if '  ' in query_clean:
        while '  ' in query_clean:
            query_clean = query_clean.replace('  ', ' ')
    return query_clean.strip()

#############################################

def match_all(list_find, list_targets):

    match_list = []
    if not list_targets:
        return match_list

    find = ' '.join(list_find)
    p = 0

    while p < len(list_targets):
        if find.strip().lower() == ' '.join(list_targets[p:p+len(list_find)]).strip().lower():
            match_list.append(p)
        p = p + 1
    
    return match_list