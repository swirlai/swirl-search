'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

from gettext import lngettext
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

# TO DO: review all below

import copy

from nltk.corpus import stopwords
# to do: detect language, set correctly
stop_words = set(stopwords.words('english'))

STOP_WORDS = stop_words

IMPORTANT_CHARS = ['$', '%']

import logging as logger

# TO DO: remove this? 

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

def highlight_list (text, word_list):

    highlighted_text = text
    for word in word_list:
        if highlighted_text.find(word) > -1:
            highlighted_text = highlighted_text.replace(word, f'*{word}*')
        else:
            logger.error(f"highlight_list: failed to find match: {word}, {highlighted_text}")
              
    return highlighted_text

#############################################
# fix for https://github.com/sidprobstein/swirl-search/issues/34

from nltk.stem import PorterStemmer

ps = PorterStemmer()

def stem_string(s):
        
    nl=[]
    for s in s.strip().split():
        nl.append(ps.stem(s))

    return ' '.join(nl)

#############################################

def clean_string(s):

    # remove entities and tags
    s1 = remove_tags(s)

    # parse s1 carefully
    module_name = 'clean_string'
    query_clean = ""
    last_ch = ""
    tag = False
    tagloc = closeloc = xloc = -1
    currency = False
    numeric = False
    lastnum = ""
    try:
        for ch in s1.strip():
            # numbers
            if ch.isnumeric():
                numeric = True
                if last_ch in [ '$', '£', '€', '¥', '₣' ]:
                    query_clean = query_clean + last_ch
                    currency = True
                if currency:
                    query_clean = query_clean + ch
                if numeric:
                    lastnum = lastnum + ch
                last_ch = ch
                continue
            # letters
            if ch.isalpha():
                query_clean = query_clean + ch
                if numeric:
                    numeric = False
                if currency:
                    currency = False
                lastnum = ""
                last_ch = ch
                continue
            else:
                # all others
                # copy chars
                if ch in [ '"', "'", '#', '@' ]:
                    query_clean = query_clean + ch
                    if numeric:
                        numeric = False
                    if currency:
                        currency = False
                    lastnum = ""
                    last_ch = ch
                    continue
                # replace with space
                if ch in [ ' ', '-', '_', ':', '\t', '\n', '\r', '+', '/', '\\' ]:
                    if numeric:
                        numeric = False
                    if currency:
                        currency = False
                    lastnum = ""       
                    # emit no more than 1 space
                    if last_ch != ' ':
                        query_clean = query_clean + ' '
                        continue
                    # end if
                # end if
                # replace with .
                if ch in [ '|', '?', '!' ]:
                    query_clean = query_clean + '.'
                    last_ch = '.'
                    continue                
                # don't express if numeric 
                if ch in [ '.', ',' ]:
                    if not numeric and not currency:
                        query_clean = query_clean + ch
                        last_ch = ch
                        continue
                # percent
                if ch == '%' and len(lastnum) > 0:
                    query_clean = query_clean + lastnum + ch
                    last_ch = ch
                    continue
                # keep in numeric
                if ch in [ '.', ',' ]:
                    if currency:
                        query_clean = query_clean + ch
                    lastnum = lastnum + ch
                # end if
            # end if
            last_ch = ch
        # end for
    except NameError as err:
        return(f'{module_name}: Error: NameError: {err}')
    except TypeError as err:
        return(f'{module_name}: Error: TypeError: {err}')
    # remove extra spaces
    if '  ' in query_clean:
        while '  ' in query_clean:
            query_clean = query_clean.replace('  ', ' ')

    # remove 
    return query_clean.strip()

#############################################
# fix for https://github.com/sidprobstein/swirl-search/issues/33

from bs4 import BeautifulSoup

# Function to remove tags
def remove_tags(html):
  
    # parse html content
    soup = BeautifulSoup(html, "html.parser")
  
    for data in soup(['style', 'script']):
        # Remove tags
        data.decompose()
  
    # return data by retrieving the tag content
    return ' '.join(soup.stripped_strings)

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
        if find.strip().lower() == ' '.join(list_targets[p:p+len(list_find)]).strip().lower():
            match_list.append(p)
        p = p + 1
    
    return match_list