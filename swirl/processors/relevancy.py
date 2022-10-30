'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

import logging as logger

#############################################    
#############################################    

# TO DO: clean up this order

from swirl.models import Search, Result

from .processor import *

#############################################    
#############################################    

from math import isnan

from django.conf import settings

from .utils import clean_string, stem_string, match_all, match_any, highlight_list, remove_tags

from ..spacy import nlp

# to do: detect language and load all stopwords? P1
from ..nltk import stopwords_en, word_tokenize, sent_tokenize

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
        # fix for https://github.com/sidprobstein/swirl-search/issues/34
        query_stemmed_list = stem_string(clean_string(self.search.query_string_processed)).strip().split()

        # check for zero vector
        empty_query_vector = False
        if query_nlp.vector.all() == 0:
            empty_query_vector = True

        # check for stopword query
        query_without_stopwords = []
        for extract in query_list:
            if not extract in stopwords_en:
                query_without_stopwords.append(extract)
        if len(query_without_stopwords) == 0:
            self.error(f"query_string_processed is all stopwords!")
            # to do: handle more gracefully
            return self.results
        
        ############################################
        # main loop
        updated = 0
        total_len = 0
        for results in self.results:
            # result set
            # self.warning("Results!")
            highlighted_json_results = []
            if not results.json_results:
                continue
            for result in results.json_results:
                # result item
                dict_score = {}
                result_len = 0
                for field in RELEVANCY_CONFIG:
                    if field in result:
                        # result_field is shorthand for item[field]
                        if type(result[field]) == list:
                            result[field] = result[field][0]
                        # prepare result field
                        result_field = clean_string(result[field]).strip()
                        result_field_nlp = nlp(result_field)
                        result_field_list = result_field.strip().split()
                        # counts
                        result_len = result_len + len(result_field_list)
                        total_len = total_len + result_len
                        # fix for https://github.com/sidprobstein/swirl-search/issues/34
                        result_field_stemmed = stem_string(result_field)
                        result_field_stemmed_list = result_field_stemmed.strip().split()
                        if len(result_field_list) != len(result_field_stemmed_list):
                            self.error("len(result_field_list) != len(result_field_stemmed_list), highlighting errors may occur")
                        dict_score[field] = {}
                        extracted_highlights = []
                        match_stems = []
                        ###########################################
                        # query vs result_field
                        # to do: if no match, and score is below .7, then set to 0?
                        if match_any(query_stemmed_list, result_field_stemmed_list):                            
                            if empty_query_vector or result_field_nlp.vector.all() == 0:
                                if len(result_field_list) == 0:
                                    qvr = 0.0
                                else:
                                    qvr = 0.3 + 1/3
                                # end if
                            else:
                                label = '_*'
                                if len(sent_tokenize(result_field)) > 1:
                                    # by sentence, take highest
                                    max_similarity = 0.0
                                    for sent in sent_tokenize(result_field):
                                        result_sent_nlp = nlp(sent)
                                        qvs = query_nlp.similarity(result_sent_nlp)
                                        if qvs > max_similarity:
                                            max_similarity = qvs
                                    # end for
                                    qvr = max_similarity
                                    label = '_s*'
                                else:
                                    qvr = query_nlp.similarity(result_field_nlp)
                            # end if
                            if qvr >= settings.SWIRL_MIN_SIMILARITY:
                                dict_score[field]['_'.join(query_list)+label] = qvr
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
                                    continue
                                # end if
                                if len(result_field_list) == 0:
                                    continue
                                # a slice can be 1 gram (if query is length 1)
                                query_slice_list = query_list[p:p+gram]
                                query_slice_len = len(query_slice_list)
                                if query_slice_len == 1:
                                    if query_slice_list[0] in stopwords_en:
                                        continue
                                if query_slice_len == 0:
                                    continue
                                query_slice_stemmed_list = query_stemmed_list[p:p+gram]
                                if '_'.join(query_slice_list) in dict_score[field]:
                                    continue
                                ####### MATCH
                                # iterate across all matches, match on stem; match_all returns a list of result_field_list indexes that match
                                match_list = match_all(query_slice_stemmed_list, result_field_stemmed_list)
                                if len(match_list) > settings.SWIRL_MAX_MATCHES:
                                    match_list = match_list[:settings.SWIRL_MAX_MATCHES-1]
                                qw = query_slice_list
                                if match_list:
                                    key = ''
                                    for match in match_list:
                                        extracted_match_list = result_field_list[match:match+len(query_slice_stemmed_list)]
                                        key = '_'.join(extracted_match_list)+'_'+str(match)
                                        rw = result_field_list[match-(gram*2)-1:match+query_slice_len+2+(gram*2)]
                                        dict_score[field][key] = ""
                                        ######## SIMILARITY vs WINDOW
                                        rw_nlp = nlp(' '.join(rw))
                                        if rw_nlp.vector.all() == 0:
                                            dict_score[field][key] = 0.31 + 1/3
                                        if not dict_score[field][key]:
                                            qw_nlp = nlp(' '.join(qw))
                                            if qw_nlp.vector.all() == 0:
                                                dict_score[field][key] = 0.32 + 1/3
                                        if not dict_score[field][key]:
                                            dict_score[field][key] = qw_nlp.similarity(rw_nlp)
                                        ######### COLLECT MATCHES FOR HIGHLIGHTING
                                        for extract in extracted_match_list:
                                            if extract in extracted_highlights:
                                                continue
                                            extracted_highlights.append(extract)
                                        if '_'.join(query_slice_stemmed_list) not in match_stems:
                                            match_stems.append('_'.join(query_slice_stemmed_list))
                                    # end for
                                    # dict_score[field]['_highlight_hits'] = extracted_highlights
                                    # dict_score[field]['_matching_stems'] = match_stems
                            # end for
                            p = p + 1
                        # end while
                        if dict_score[field] == {}:
                            del dict_score[field]
                        ############################################
                        # highlight
                        result[field] = result[field].replace('*','')   # remove old
                        # fix for https://github.com/sidprobstein/swirl-search/issues/33
                        result[field] = highlight_list(remove_tags(result[field]), extracted_highlights)
                        ############################################
                    # end if
                # end for field in RELEVANCY_CONFIG:
                # score the item 
                result['swirl_score'] = 0.0
                # dict_len_adjusts = {}
                for f in dict_score:
                    if f in RELEVANCY_CONFIG:
                        # len_adjust = 1.0
                        weight = RELEVANCY_CONFIG[f]['weight']
                        # lenf = len(clean_string(result[f]).split())
                        # if 'len_boost_max' in RELEVANCY_CONFIG[f]:
                        #     if lenf <= RELEVANCY_CONFIG[f]['len_boost_max']:
                        #         # boost
                        #         len_adjust = float(RELEVANCY_CONFIG[f]['len_boost'])
                        # if 'len_penalty_min' in RELEVANCY_CONFIG[f]:
                        #     if lenf >= RELEVANCY_CONFIG[f]['len_penalty_min']:
                        #         # penalty
                        #         len_adjust = float(RELEVANCY_CONFIG[f]['len_penalty'])
                        # dict_len_adjusts[f] = len_adjust
                    # end if
                    for k in dict_score[f]:
                        if k.startswith('_'):
                            continue
                        if dict_score[f][k] >= settings.SWIRL_MIN_SIMILARITY:
                            if k.endswith('_*'):
                                result['swirl_score'] = result['swirl_score'] + (weight * dict_score[f][k]) # * len_adjust
                            else:
                                result['swirl_score'] = result['swirl_score'] + (weight * dict_score[f][k]) * (len(k) * len(k)) # * len_adjust
                        # end if
                    # end for
                # end for
                ####### explain
                # for f in dict_len_adjusts:
                #     # dict_score[f]['_length'] = len(clean_string(result[f]).split())
                #     if dict_len_adjusts[f] != 1.0:
                #         dict_score[f]['_len_boost'] = dict_len_adjusts[f]
                result['explain'] = dict_score                
                updated = updated + 1
                # save highlighted version
                highlighted_json_results.append(result)
                # save count
                result['length'] = result_len
            # end for result in results.json_results:
            results.save()
        # end for results in self.results:
        ############################################
        # normalize scores by length
        if updated > 0:
            average_len = total_len / updated
        for results in self.results:
            if not results.json_results:
                continue
            for result in results.json_results:
                if result['length'] > 0:
                    adjust = average_len / result['length']
                    if adjust > (2 + 2/3):
                        adjust = 2 + 2/3
                    result['swirl_score'] = round(result['swirl_score'] * adjust,0)
                    result['explain']['length_adjust'] = adjust
                if 'length' in result:
                    del result['length']
            # end for
            results.save()
        # end for
        ############################################

        self.results_updated = int(updated)
        
        return self.results_updated                