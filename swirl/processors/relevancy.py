'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

import logging as logger

from attr import Attribute

#############################################    
#############################################    

from swirl.models import Search, Result
from .utils import highlight

from swirl.processors import *

#############################################    
#############################################    

from math import sqrt, isnan
 
def squared_sum(x):
    """ return 3 rounded square rooted value """
 
    return round(sqrt(sum([a*a for a in x])),3)

#############################################    

def cos_similarity(x,y):
    """ return cosine similarity between two lists """
    """ can return NaN (not a number) if one of the embeddings is a zero-array - caller must handle """

    numerator = sum(a*b for a,b in zip(x,y))
    denominator = squared_sum(x)*squared_sum(y)
    return round(numerator/float(denominator),3)

#############################################    

from .utils import clean_string_alphanumeric

def cosine_relevancy_processor(search_id):

    module_name = 'cosine_relevancy_processor'

    if Search.objects.filter(id=search_id).exists():
        search = Search.objects.get(id=search_id)
        if search.status == 'POST_RESULT_PROCESSING' or search.status == 'RESCORING':
            results = Result.objects.filter(search_id=search_id)
        else:
            logger.warning(f"{module_name}: search {search_id} has status {search.status}, this processor requires: status == 'POST_RESULT_PROCESSING'")
            return 0
        # end if
    else:
        logger.error(f"{module_name}: search {search_id} was not found")
        return 0
    # end if

    # note: do not use url as it is usually a proxy vote for title
    RELEVANCY_CONFIG = {
        'title': {
            'weight': 3.0
        },
        'body': {
            'weight': 1.0
        },
        'author': {
            'weight': 2.0
        }
    }
    
    # prep query string
    query_string_nlp = nlp(clean_string_alphanumeric(search.query_string_processed)).vector

    ############################################
    # main loop
    updated = 0
    for result in results:
        highlighted_json_results = []
        if result.json_results:
            for item in result.json_results:
                weighted_score = 0.0
                dict_score = {}
                match_dict = {}
                item['boosts'] = []
                for field in RELEVANCY_CONFIG:
                    if field in item:
                        last_term = ""
                        ############################################
                        # highlight 
                        if not search.status == 'RESCORING':
                            item[field] = highlight(item[field], search.query_string_processed)
                        ############################################
                        # summarize matches
                        try:
                            for term in search.query_string_processed.strip().split():
                                item_field = item[field]
                                if type(item[field]) == list:
                                    item_field = item[field][0]
                                if term.lower() in item_field.lower():
                                    if field in match_dict:
                                        match_dict[field].append(term)
                                    else:
                                        match_dict[field] = []
                                        match_dict[field].append(term)
                                    # end if
                                # check for bi-gram match
                                if last_term:
                                    if not term.lower() == last_term.lower():
                                        if f'*{last_term.lower()}* *{term.lower()}*' in item_field.lower():
                                            if f"{last_term}_{term}" not in match_dict[field]:
                                                match_dict[field].append(f"{last_term}_{term}")
                                last_term = term
                            # end for
                        except AttributeError:
                            logger.error(f"AttributeError: term: {term}, item: {item[field]}")
                       ############################################
                        # cosine similarity between query and matching field store in dict_score
                        if field in match_dict:
                            # hit!!
                            # dict_score[field + "_field"] = clean_string_alphanumeric(item[field])
                            field_nlp = nlp(clean_string_alphanumeric(item_field)).vector
                            if field_nlp.all() == 0 or query_string_nlp.all() == 0:
                                item['boosts'].append("BLANK_EMBEDDING")
                                dict_score[field] = 0.5
                            else:
                                dict_score[field] = cos_similarity(query_string_nlp, field_nlp)
                                if isnan(dict_score[field]):
                                    item['boosts'].append("COSINE_NAAN")
                                    dict_score[field] = 0.5
                            # end if
                        # end if
                    # end if
                # end for 
                ############################################
                # weight field similarity
                item['swirl_score'] = 0.0
                weight = 0.0
                for field in dict_score:
                    if not field.endswith('_field'):
                        item['swirl_score'] = float(item['swirl_score']) + float(RELEVANCY_CONFIG[field]['weight']) * float(dict_score[field])
                        weight = weight + float(RELEVANCY_CONFIG[field]['weight'])
                    # end if
                # end for
                if weight == 0.0:
                    item['swirl_score'] = weighted_score = 0.0
                else:
                    weighted_score = round(float(item['swirl_score'])/float(weight),2)
                    item['swirl_score'] = weighted_score
                ############################################
                # boosting                
                query_len = len(search.query_string_processed.strip().split())
                term_match = 0
                phrase_match = 0
                all_terms = 0
                for match in match_dict:
                    terms_field = 0
                    for hit in match_dict[match]:
                        if '_' in hit:
                            phrase_match = phrase_match + 1
                        else:
                            term_match = term_match + 1
                            terms_field = terms_field + 1
                    # boost if all terms match this field
                    # to do: no all_terms_match for a single term query
                    if terms_field == query_len and query_len > 1:
                        all_terms = all_terms + 1
                # take away credit for one field, one term hit
                if term_match == 1:
                    term_match = 0
                    term_boost = 0.0
                else:
                    term_boost = round((float(term_match) * 0.1) / float(query_len), 2)
                    if term_boost > 0:
                        item['boosts'].append(f'term_match {term_boost}')
                phrase_boost = round((float(phrase_match) * 0.2) / (float(query_len) / 2), 2)
                if phrase_boost > 0:
                    item['boosts'].append(f'phrase_match {phrase_boost}')
                all_terms_boost = round((float(all_terms) * 0.1), 2)
                if all_terms_boost > 0:
                    item['boosts'].append(f'all_terms {all_terms_boost}')
                item['swirl_score'] = item['swirl_score'] + max([term_boost, phrase_boost, all_terms_boost])
                item['swirl_score'] = round(item['swirl_score'], 2)
                ###########################################
                # check for overrun
                if item['swirl_score'] > 1.0:
                    item['swirl_score'] = 1.0
                # explain
                item['explain'] = {} 
                item['explain']['matches'] = match_dict
                item['explain']['similarity'] = weighted_score
                item['explain']['boosts'] = item['boosts']
                # clean up 
                del item['boosts']
                ##############################################
                updated = updated + 1
                highlighted_json_results.append(item)
            # end for
            # logger.info(f"Updating results: {result.id}")
            # save!!!!
            result.json_results = highlighted_json_results
            # to do: catch invalid json error P2
            # to do: why would we do that here?
            result.save()
        # end if
    # end for

    return updated
