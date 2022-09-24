'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

import logging as logger

#############################################    
#############################################    

from swirl.models import Search, Result
from .utils import highlight

from .processor import *

#############################################    
#############################################    

from math import isnan

#############################################    

from .utils import clean_string_alphanumeric

from ..spacy import nlp

class CosineRelevancyProcessor(PostResultProcessor):

    type = 'CosineRelevancyPostResultProcessor'

    ############################################

    # def __init__(self, search_id):

    #     self.nlp = spacy.load('en_core_web_md')
    #     super().__init__(search_id)

    ############################################

    def process(self):

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
        query_string_nlp = nlp(self.search.query_string_processed)
        self.warning(f'nlp: {query_string_nlp}')

        ############################################
        # main loop
        updated = 0
        for result in self.results:
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
                            if not self.search.status == 'RESCORING':
                                item[field] = highlight(item[field], self.search.query_string_processed)
                            ############################################
                            # summarize matches
                            try:
                                for term in self.search.query_string_processed.strip().split():
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
                                self.error(f"AttributeError: term: {term}, item: {item[field]}")
                        ############################################
                            # cosine similarity between query and matching field store in dict_score
                            if field in match_dict:
                                # hit!!
                                # dict_score[field + "_field"] = clean_string_alphanumeric(item[field])
                                field_nlp = nlp(item_field)
                                # if field_nlp.all() == 0 or query_string_nlp.all() == 0:
                                #     item['boosts'].append("BLANK_EMBEDDING")
                                #     dict_score[field] = 0.5
                                # else:
                                dict_score[field] = query_string_nlp.similarity(field_nlp)
                                # if isnan(dict_score[field]):
                                #     item['boosts'].append("COSINE_NAAN")
                                #     dict_score[field] = 0.5
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
                    query_len = len(self.search.query_string_processed.strip().split())
                    if query_len > 1:
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
                        phrase_boost = round((float(phrase_match) * 0.2) / float(query_len), 2)
                        if phrase_boost > 0:
                            item['boosts'].append(f'phrase_match {phrase_boost}')
                        all_terms_boost = round((float(all_terms) * 0.2), 2)
                        if all_terms_boost > 0:
                            item['boosts'].append(f'all_terms {all_terms_boost}')
                        item['swirl_score'] = item['swirl_score'] + max([term_boost, phrase_boost, all_terms_boost])
                        item['swirl_score'] = round(item['swirl_score'], 2)
                    # end if
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

        self.results_updated = int(updated)
        
        return self.results_updated