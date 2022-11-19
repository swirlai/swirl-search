'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

#############################################    
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
# fix for https://github.com/sidprobstein/swirl-search/issues/34

from ..nltk import ps

def stem_string(s):
        
    nl=[]
    for s in s.strip().split():
        nl.append(ps.stem(s))

    return ' '.join(nl)

#############################################

def highlighted_list(text, word_list):

    highlighted_text = text
    for word in word_list:
        loc = highlighted_text.find(word)
        if loc > -1:
            highlighted_text = highlighted_text.replace(word, f'*{word}*')
        else:
            # logger.warning(f"highlight_list: failed to find match: {word}, {highlighted_text}, ignoring")
            pass
              
    return highlighted_text

def highlight_list(text, word_list):

    highlighted_list = []
    for term in text.split():
        if term in word_list:
            highlighted_list.append(f"*{term}*")
        else:
            highlighted_list.append(term)
              
    return ' '.join(highlighted_list)

#############################################
# fix for https://github.com/sidprobstein/swirl-search/issues/33

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

#############################################

def clean_string(s):

    # remove entities and tags
    s1 = remove_tags(s)

    # parse s1 carefully
    module_name = 'clean_string'
    query_clean = ""
    try:
        for ch in s1.strip():
            # numbers
            if ch.isnumeric():
                query_clean = query_clean + ch
            # letters
            if ch.isalpha():
                query_clean = query_clean + ch
            if ch in [ '"', "'", '’', ' ', '-' ]:
                query_clean = query_clean + ch
            # if ch in [ '.', '!', '?', ':' ]:
            #     query_clean = query_clean + ' ' + ch + ' '
        # end for
    except NameError as err:
        return(f'{module_name}: Error: NameError: {err}')
    except TypeError as err:
        return(f'{module_name}: Error: TypeError: {err}')
    # remove extra spaces
    if '  ' in query_clean:
        while '  ' in query_clean:
            query_clean = query_clean.replace('  ', ' ')
    # end if
    return query_clean.strip()

#############################################

def cleanish_string(s):

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
                if ch in [ '"', "'", '#', '@', '-' ]:
                    query_clean = query_clean + ch
                    if numeric:
                        numeric = False
                    if currency:
                        currency = False
                    lastnum = ""
                    last_ch = ch
                    continue
                # replace with space
                # as of swirl 1.6, - is left in
                if ch in [ ' ', '_', ':', '\t', '\n', '\r', '+', '/', '\\' ]:
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

def cleaner_string(s):

    # remove entities and tags
    s1 = remove_tags(s)

    # parse s1 carefully
    module_name = 'cleaner_string'
    query_cleaner = ""
    last_ch = ""
    currency = False
    numeric = False
    lastnum = ""
    try:
        for ch in s1.strip():
            # numbers
            if ch.isnumeric():
                numeric = True
                if last_ch in [ '$', '£', '€', '¥', '₣' ]:
                    query_cleaner = query_cleaner + last_ch
                    currency = True
                if currency:
                    query_cleaner = query_cleaner + ch
                if numeric:
                    lastnum = lastnum + ch
                last_ch = ch
                continue
            # letters
            if ch.isalpha():
                query_cleaner = query_cleaner + ch
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
                if ch in [ '#', '@' ]:
                    query_cleaner = query_cleaner + ch
                    if numeric:
                        numeric = False
                    if currency:
                        currency = False
                    lastnum = ""
                    last_ch = ch
                    continue
                # replace with space
                # as of swirl 1.6, - is left in
                if ch in [ '"', "'", '-', ',', '_', ':', '\t', '\n', '\r', '+', '/', '\\' ]:
                    if numeric:
                        numeric = False
                    if currency:
                        currency = False
                    lastnum = ""       
                    # emit no more than 1 space
                    if last_ch != ' ':
                        query_cleaner = query_cleaner + ' '
                        continue
                    # end if
                # end if
                # replace with .
                if ch in [ '|', '?', '!' ]:
                    query_cleaner = query_cleaner + '.'
                    last_ch = '.'
                    continue                
                # don't express if numeric 
                if ch in [ '.', ',' ]:
                    if not numeric and not currency:
                        query_cleaner = query_cleaner + ch
                        last_ch = ch
                        continue
                # percent
                if ch == '%' and len(lastnum) > 0:
                    query_cleaner = query_cleaner + lastnum + ch
                    last_ch = ch
                    continue
                # keep in numeric
                if ch in [ '.', ',' ]:
                    if currency:
                        query_cleaner = query_cleaner + ch
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
    if '  ' in query_cleaner:
        while '  ' in query_cleaner:
            query_cleaner = query_cleaner.replace('  ', ' ')

    # remove 
    return query_cleaner.strip()

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


    