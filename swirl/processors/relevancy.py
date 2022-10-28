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

from django.conf import settings

from .utils import clean_string, stem_string, match_all

from ..spacy import nlp

# to do: detect language and load all stopwords? P1
from ..nltk import stopwords_en

class CosineRelevancyProcessor(PostResultProcessor):

    type = 'CosineRelevancyPostResultProcessor'

    ############################################

    def process(self):

        RELEVANCY_CONFIG = settings.SWIRL_RELEVANCY_CONFIG
        
        # prep query string
        query = clean_string(self.search.query_string_processed).strip()
        query_nlp = nlp(query)
        query_list = query.strip().split()
        query_len = len(query_list)
        query_stemmed_list = stem_string(clean_string(self.search.query_string_processed)).strip().split()

        # check for zero vector
        empty_query_vector = False
        if query_nlp.vector.all() == 0:
            empty_query_vector = True

        # check for stopword query
        query_without_stopwords = []
        for term in query_list:
            if not term in stopwords_en:
                query_without_stopwords.append(term)
        if len(query_without_stopwords) == 0:
            self.error(f"query_string_processed is all stopwords!")
        
        ############################################
        # main loop
        updated = 0
        for results in self.results:
            # result set
            # self.warning("Results!")
            highlighted_json_results = []
            if not results.json_results:
                continue
            for result in results.json_results:
                # result item
                dict_score = {}
                for field in RELEVANCY_CONFIG:
                    if field in result:
                        # result_field is shorthand for item[field]
                        if type(result[field]) == list:
                            result[field] = result[field][0]
                        # prepare result field
                        result_field = clean_string(result[field]).strip()
                        result_field_nlp = nlp(result_field)
                        result_field_list = clean_string(result_field).strip().split()
                        result_field_stemmed = stem_string(clean_string(result_field))
                        result_field_stemmed_list = result_field_stemmed.strip().split()
                        dict_score[field] = {}
                        ############################################
                        # query vs result_field
                        if empty_query_vector or result_field_nlp.vector.all() == 0:
                            if len(result_field_list) == 0:
                                qvr = 0.0
                            else:
                                qvr = 0.3 + 1/3
                            # end if
                        else:
                            qvr = query_nlp.similarity(result_field_nlp)
                        # end if
                        if qvr > 0.5:
                            dict_score[field]['_'.join(query_list)+'_*'] = qvr
                        ############################################
                        # 1, 2, all gram
                        p = 0
                        while p <= query_len - 1:
                            grams = [1]
                            if query_len == 2:
                                grams = [2,1]
                            if query_len > 2:
                                grams = [query_len,2,1]
                            for gram in grams:
                                if gram == "":
                                    self.warning("skipping blank gram")
                                    continue
                                # end if
                                if len(result_field_list) == 0:
                                    self.warning("skipping blank field")
                                    continue
                                # a slice can be 1 gram (if query is length 1)
                                query_slice_list = query_list[p:p+gram]
                                query_slice_len = len(query_slice_list)
                                if query_slice_len == 1:
                                    if query_slice_list[0] in stopwords_en:
                                        self.warning(f"Ignoring stopword: {query_slice_list[0]}")
                                        continue
                                if query_slice_len == 0:
                                    continue
                                query_slice_stemmed_list = query_stemmed_list[p:p+gram]
                                if '_'.join(query_slice_list) in dict_score[field]:
                                    continue
                                ####### MATCH
                                # iterate across all matches
                                # match on stem
                                # match_all returns a list of result_field_list indexes that match
                                match_list = match_all(query_slice_stemmed_list, result_field_stemmed_list)
                                if len(match_list) > settings.SWIRL_MAX_MATCHES:
                                    match_list = match_list[:settings.SWIRL_MAX_MATCHES-1]
                                qw = query_slice_list
                                if match_list:
                                    key = ''
                                    for match in match_list:
                                        rw = result_field_list[match-(gram*2)-1:match+query_slice_len+2+(gram*2)]
                                        key = '_'.join(qw)+'_'+str(match)
                                        ######## SIMILARITY vs WINDOW
                                        rw_nlp = nlp(' '.join(rw))
                                        if rw_nlp.vector.all() == 0:
                                            dict_score[field][key] = 0.31 + 1/3
                                            continue
                                        qw_nlp = nlp(' '.join(qw))
                                        if qw_nlp.vector.all() == 0:
                                            dict_score[field][key] = 0.32 + 1/3
                                            continue
                                        dict_score[field][key] = qw_nlp.similarity(rw_nlp)
                                    # end for
                            # end for
                            p = p + 1
                        # end while
                        if dict_score[field] == {}:
                            del dict_score[field]
                        ############################################
                        # highlight 
                        result[field] = result[field].replace('*','')   # remove old
                        result[field] = highlight(result[field], self.search.query_string_processed)
                        ############################################
                    # end if
                # end for field in RELEVANCY_CONFIG:
                # score the item 
                result['swirl_score'] = 0.0
                dict_len_adjusts = {}
                for f in dict_score:
                    if f in RELEVANCY_CONFIG:
                        len_adjust = 1.0
                        weight = RELEVANCY_CONFIG[f]['weight']
                        lenf = len(clean_string(result[f]).split())
                        if 'len_boost_max' in RELEVANCY_CONFIG[f]:
                            if lenf <= RELEVANCY_CONFIG[f]['len_boost_max']:
                                # boost
                                len_adjust = float(RELEVANCY_CONFIG[f]['len_boost'])
                        if 'len_penalty_min' in RELEVANCY_CONFIG[f]:
                            if lenf >= RELEVANCY_CONFIG[f]['len_penalty_min']:
                                # penalty
                                len_adjust = float(RELEVANCY_CONFIG[f]['len_penalty'])
                        dict_len_adjusts[f] = len_adjust
                    # end if
                    for k in dict_score[f]:
                        if dict_score[f][k] >= settings.SWIRL_MIN_SIMILARITY:
                            if k.endswith('_*'):
                                result['swirl_score'] = result['swirl_score'] + (weight * dict_score[f][k]) * len_adjust
                            else:
                                result['swirl_score'] = result['swirl_score'] + (weight * dict_score[f][k]) * (len(k) * len(k)) * len_adjust
                        # end if
                    # end for
                # end for
                ####### explain
                for f in dict_len_adjusts:
                    # dict_score[f]['_length'] = len(clean_string(result[f]).split())
                    if dict_len_adjusts[f] != 1.0:
                        dict_score[f]['_len_boost'] = dict_len_adjusts[f]
                result['explain'] = dict_score                
                updated = updated + 1
                # save highlighted version
                highlighted_json_results.append(result)
            # end for result in results.json_results:
            results.save()
        # end for results in self.results:

        self.results_updated = int(updated)
        
        return self.results_updated                