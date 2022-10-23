'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

import logging as logger

from regex import E

#############################################    
#############################################    

from swirl.models import Search, Result
from .utils import highlight

from .processor import *

#############################################    
#############################################    

from math import isnan

#############################################    

from .utils import clean_string, stem_string, match_all

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
        query_len = len(self.search.query_string_processed.strip().split())
        empty_query_vector = False
        query_string_nlp = nlp(self.search.query_string_processed)
        if query_string_nlp.vector.all() == 0:
            # zero vector!! similiarty won't work
            empty_query_vector = True
        # self.warning(f'nlp: {query_string_nlp}')

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
                                            if f'{last_term.lower()} {term.lower()}' in item_field.lower():
                                                if f"{last_term}_{term}" not in match_dict[field]:
                                                    match_dict[field].append(f"{last_term}_{term}")
                                    last_term = term
                                # end for
                            except AttributeError:
                                self.error(f"AttributeError: term: {term}, item: {item[field]}")
                            ############################################
                            # cosine similarity between query and matching field store in dict_score
                            # to do: handle phrases in query, e.g. foo "bar baz" bee
                            # to do: seems like bar_baz has to become field
                            if field in match_dict:
                                # hit!!
                                if empty_query_vector:
                                    dict_score[field] = 0.5
                                else:
                                    if len(item_field) > (query_len * 3):
                                        # process item_field in chunks and take the highest score
                                        pass
                                    # to do: remove <...> from item_field
                                    field_nlp = nlp(item_field)
                                    dict_score[field] = query_string_nlp.similarity(field_nlp)
                                # end if
                            # end if
                            ############################################
                            # highlight 
                            if not self.search.status == 'RESCORING':
                                item[field] = highlight(item[field], self.search.query_string_processed)
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
                    term_match = 0
                    phrase_match = 0
                    for match in match_dict:
                        terms_field = 0
                        for hit in match_dict[match]:
                            if '_' in hit:
                                phrase_match = phrase_match + 1
                            else:
                                term_match = term_match + 1
                                terms_field = terms_field + 1
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
                    item['swirl_score'] = item['swirl_score'] + max([term_boost, phrase_boost])
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

        self.results_updated = int(updated)
        
        return self.results_updated

############################################

from nltk.corpus import stopwords

from math import sqrt

class NewishCosineRelevancyProcessor(PostResultProcessor):

    type = 'NewishCosineRelevancyPostResultProcessor'

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
        query_list = self.search.query_string_processed.strip().split()
        query_stemmed_list = stem_string(clean_string(self.search.query_string_processed)).strip().split()
        self.warning(f"query_list: {query_stemmed_list}")
        query_len = len(query_stemmed_list)
        
        query_string_nlp = nlp(self.search.query_string_processed)

        # check for zero vector
        empty_query_vector = False
        if query_string_nlp.vector.all() == 0:
            empty_query_vector = True
            self.warning("Warning: empty query vector")

        ############################################
        # main loop
        updated = 0
        for results in self.results:
            # result set
            # self.warning("Results!")
            highlighted_json_results = []
            if not results.json_results:
                # self.warning("Blank result set!")
                continue
            for result in results.json_results:
                # result item
                self.warning("Result!---------------")
                weighted_score = 0.0
                dict_result_matches = {}
                dict_result_score = {}
                result['boosts'] = []
                for field in RELEVANCY_CONFIG:
                    # dict_sim contains the similarity scores, keyed by query term(s) (e.g. x, x_y, x_y_z) for this field
                    dict_sim = {}
                    if field in result:
                        # self.warning(f"Field: {field}")
                        last_term = ""
                        # item_field is shorthand for item[field]
                        result_field = result[field]
                        result_field_list = clean_string(result_field).strip().split()
                        result_stemmed = stem_string(clean_string(result_field))
                        result_stemmed_list = result_stemmed.strip().split()
                        if len(result_field_list) != len(result_stemmed_list):
                            self.error("result_field_list does not equal result_stemmed_list!")
                        ############################################
                        # 1, 2 gram
                        p = 0
                        while p < query_len:
                            grams = [1]
                            if query_len > 1:
                                grams = [1,2]
                            for gram in grams:
                                # a slice can be 1 gram (if query is length 1)
                                qslice = query_stemmed_list[p:p+gram]
                                self.warning(f"qslice: {qslice}")
                                if '_'.join(qslice) in dict_sim:
                                    continue
                                qs = ' '.join(qslice)
                                ####### MATCH
                                if qs.lower() in result_stemmed.lower():
                                    iidx = -1
                                    for i in result_stemmed_list:
                                        if qslice[0].lower() == i.lower():
                                            # here is the beginning of the match?!?
                                            # to do: WARNING: the below could miss, because the lower() is not applied in the index() P1 P1 P1
                                            iidx = result_stemmed_list.index(qslice[0])
                                            break
                                    if iidx == -1:
                                        # to do: handle error
                                        self.warning("no iidx")
                                        pass
                                    rw = result_field_list[iidx-(gram*2)-1:iidx+len(qslice)+2+(gram*2)]
                                    qw = query_list[p:p+gram]
                                    ######## SIMILARITY vs WINDOW
                                    self.warning(f"similarity: {qw} ? {rw}")
                                    rw_nlp = nlp(' '.join(rw))
                                    qw_nlp = nlp(' '.join(qw))
                                    if qw_nlp.vector.all() == 0:
                                        self.warning("Warning: qw_nlp is 0")
                                    dict_sim['_'.join(qslice)] = qw_nlp.similarity(rw_nlp)             
                                    # self.warning(f"scoring {w} = {qslice_nlp.similarity(w_nlp)}")
                                # end if
                            # end for
                            p = p + 1   
                        # end if
                        ############################################
                        # all_terms
                        if query_len > 2:
                            if ' '.join(query_stemmed_list).lower() in result_stemmed.lower():
                                # self.warning("all_terms")
                                # to do: iterate through matches
                                iidx = -1
                                for i in result_stemmed_list:
                                    if query_stemmed_list[0].lower() == i.lower():
                                        # here is the beginning of the match?!?
                                        iidx = result_stemmed_list.index(query_stemmed_list[0])
                                        break
                                if iidx == -1:
                                    # to do: handle error
                                    self.warning("No iidx")
                                    pass
                                # to do: extract window around the match
                                rw = result_stemmed_list[iidx-int(query_len/2):iidx+query_len+int(query_len/2)]
                                rw_nlp = nlp(' '.join(rw))
                                dict_sim['_'.join(query_stemmed_list).lower()] = query_string_nlp.similarity(rw_nlp)
                            # end if
                        # end if
                        self.warning(f"dict_sim: {dict_sim}")
                        ############################################
                        # select longest/highest match
                        dict_weighted = {}
                        if dict_sim:
                            for match in dict_sim:
                                dict_weighted[match] = dict_sim[match] * (len(match) * len(match))
                            self.warning(f"dict_weighted: {dict_weighted}")
                            top_key = sorted(dict_weighted.items(), key=lambda item: item[1], reverse=True)[0][0]
                            self.warning(f"score! {field}: {top_key}, {dict_sim[top_key]}")
                            dict_result_matches[field] = top_key
                            dict_result_score[field] = dict_sim[top_key]
                        else:
                            dict_result_score[field] = 0.0
                        ############################################
                        # highlight 
                        # self.warning("highlighting")
                        if not self.search.status == 'RESCORING':
                            result[field] = highlight(result[field], self.search.query_string_processed)
                    # end if
                # end for 
                ############################################
                # weight field similarity
                self.warning("weighting")
                result['swirl_score'] = 0.0
                weight = 0.0
                for field in dict_result_score:
                    # if not field.endswith('_field'):
                    self.warning(f"score! {field} sim was: {dict_result_score[field]}")
                    if dict_result_score[field] > 0.0:
                        result['swirl_score'] = float(result['swirl_score']) + float(RELEVANCY_CONFIG[field]['weight']) * float(dict_result_score[field])
                        weight = weight + float(RELEVANCY_CONFIG[field]['weight'])
                    # end if
                # end for
                self.warning(f"raw score: {result['swirl_score']}")
                self.warning(f"weight: {weight}")
                if weight == 0.0:
                    result['swirl_score'] = weighted_score = 0.0
                    self.warning("weight 0")
                else:
                    weighted_score = round(float(result['swirl_score'])/float(weight),2)
                    result['swirl_score'] = weighted_score
                    self.warning(f"weighted score: {weighted_score}")
                # end if
                result['explain'] = {} 
                result['explain']['matches'] = dict_result_matches
                result['explain']['similarity'] = weighted_score
                result['explain']['boosts'] = []
                # clean up 
                # del item['boosts']
                ##############################################
                updated = updated + 1
                highlighted_json_results.append(result)
            # end for
            # logger.info(f"Updating results: {result.id}")
            # save!!!!
            results.json_results = highlighted_json_results
            # to do: catch invalid json error P2
            # to do: why would we do that here?
            results.save()
        # end for

        self.results_updated = int(updated)
        
        return self.results_updated

############################################

class NewCosineRelevancyProcessor(PostResultProcessor):

    type = 'NewCosineRelevancyPostResultProcessor'

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
        query = clean_string(self.search.query_string_processed).strip()
        query_nlp = nlp(query)
        query_list = query.strip().split()
        query_len = len(query_list)
        query_stemmed_list = stem_string(clean_string(self.search.query_string_processed)).strip().split()
        query_stemmed = ' '.join(query_stemmed_list)
        query_stemmed_nlp = nlp(query_stemmed)

        # check for zero vector
        empty_query_vector = False
        if query_nlp.vector.all() == 0:
            empty_query_vector = True
            self.warning("query vector is 0")

        ############################################
        # main loop
        updated = 0
        for results in self.results:
            # result set
            # self.warning("Results!")
            highlighted_json_results = []
            if not results.json_results:
                # self.warning("Blank result set!")
                continue
            for result in results.json_results:
                # result item
                dict_score = {}
                self.warning("Result!---------------")
                for field in RELEVANCY_CONFIG:
                    if field in result:
                        # result_field is shorthand for item[field]
                        result_field = clean_string(result[field]).strip()
                        result_field_nlp = nlp(result_field)
                        result_field_list = clean_string(result_field).strip().split()
                        result_field_stemmed = stem_string(clean_string(result_field))
                        result_field_stemmed_list = result_field_stemmed.strip().split()
                        dict_score[field] = {}
                        ############################################
                        # query vs result_field
                        dict_score[field]['_'.join(query_list)] = query_nlp.similarity(result_field_nlp)
                        ############################################
                        # 1, 2, all gram
                        p = 0
                        while p < query_len:
                            grams = [1]
                            if query_len > 1:
                                grams = [1,2]
                            if query_len > 2:
                                grams = [1,2,query_len]
                            for gram in grams:
                                # a slice can be 1 gram (if query is length 1)
                                query_slice_list = query_list[p:p+gram]
                                query_slice_len = len(query_slice_list)
                                if query_slice_len == 0:
                                    continue
                                query_slice_stemmed_list = query_stemmed_list[p:p+gram]
                                if '_'.join(query_slice_list) in dict_score[field]:
                                    continue
                                ####### MATCH
                                # iterate across all matches
                                # match on stem to increase match rate
                                # match_all returns a list of result_field_list indexes that match
                                match_list = match_all(query_slice_stemmed_list, result_field_stemmed_list)
                                # self.warning(f"match_all: {query_slice_stemmed_list} ? {result_field_stemmed_list} = {match_list}")
                                if match_list:
                                    for match in match_list:
                                        rw = result_field_list[match-gram-1:match+query_slice_len+2+gram]
                                        qw = query_slice_list
                                        ######## SIMILARITY vs WINDOW
                                        rw_nlp = nlp(' '.join(rw))
                                        qw_nlp = nlp(' '.join(qw))
                                        if qw_nlp.vector.all() == 0:
                                            self.warning("Warning: qw_nlp is 0")
                                        dict_score[field]['_'.join(query_slice_list) + '_' + str(match)] = qw_nlp.similarity(rw_nlp)  
                                    # end for
                                # end if
                            # end for
                            p = p + 1
                        # end while
                        ############################################
                        # highlight 
                        if not self.search.status == 'RESCORING':
                            result[field] = highlight(result[field], self.search.query_string_processed)
                        ############################################
                    # end if
                # end for field in RELEVANCY_CONFIG:
                # score the item 
                result['swirl_score'] = 0.0
                for f in dict_score:
                    weight = 1
                    if f in RELEVANCY_CONFIG:
                        weight = RELEVANCY_CONFIG[f]['weight']
                    for k in dict_score[f]:
                        # if dict_score[f][k] > 0.0:
                        result['swirl_score'] = result['swirl_score'] + (weight * dict_score[f][k]) * (len(k) * len(k))
                result['explain'] = dict_score                
                updated = updated + 1
                # save highlighted version
                highlighted_json_results.append(result)
            # end for result in results.json_results:
            results.save()
        # end for results in self.results:

        self.results_updated = int(updated)
        
        return self.results_updated                