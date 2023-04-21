'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from math import sqrt
from statistics import mean, median

from django.conf import settings

# to do: detect language and load all stopwords? P1
from swirl.nltk import stopwords, sent_tokenize, word_tokenize, is_punctuation
from swirl.processors.utils import *
from swirl.spacy import nlp

from swirl.processors.processor import PostResultProcessor

import logging
from celery.utils.log import get_task_logger
logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

SWIRL_RELEVANCY_CONFIG = getattr(settings, 'SWIRL_RELEVANCY_CONFIG', {
    'title': {
        'weight': 3.0
    },
    'body': {
        'weight': 1.0
    },
    'author': {
        'weight': 2.0
    }
})

SWIRL_MIN_SIMILARITY = getattr(settings, 'SWIRL_MIN_SIMILARITY', 0.51)
SWIRL_MAX_MATCHES = getattr(settings, 'SWIRL_MAX_MATCHES', 5)
SWIRL_HIGHLIGHT_START_CHAR = getattr(settings, 'SWIRL_HIGHLIGHT_START_CHAR', '*')
SWIRL_HIGHLIGHT_END_CHAR = getattr(settings, 'SWIRL_HIGHLIGHT_END_CHAR', '*')

#############################################
#############################################

class CosineRelevancyPostResultProcessor(PostResultProcessor):

    type = 'CosineRelevancyPostResultProcessor'

    ############################################

    def __init__(self, search_id):

        self.query_stemmed_list = None
        self.not_list = None
        self.query_list = None
        self.query_stemmed_target_list = None
        self.query_target_list = None
        self.query_has_numeric = None
        self.provider_query_terms = []

        return super().__init__(search_id)

    ############################################

    def prepare_query(self, q_string, results_processor_feedback):

        self.query_stemmed_list = []
        self.not_list = []
        self.query_list = []
        self.query_stemmed_target_list = []
        self.query_target_list = []
        self.query_has_numeric = False
        self.provider_query_terms = []

        if results_processor_feedback:
            self.provider_query_terms = results_processor_feedback.get(
                'result_processor_feedback', []).get('query', []).get(
                'provider_query_terms', [])

        # remove quotes
        query = clean_string(q_string).strip().replace('\"','')
        query_list = word_tokenize(query)
        ## I think the loop is okay since it's a very small list.
        for term in self.provider_query_terms:
            if not term in query_list:
                query_list.append(term)

        # remove AND, OR and parens
        query_list = [s for s in query_list if s not in ["AND","OR"] and not is_punctuation(s)]

        # check for numeric
        query_has_numeric = has_numeric(query_list)
        # not list
        not_list = []
        not_parsed_query = []
        if 'NOT' in query_list:
            not_parsed_query = query_list[:query_list.index('NOT')]
            not_list = query_list[query_list.index('NOT')+1:]
        else:
            for q in query_list:
                if q.startswith('-'):
                    not_list.append(q[1:])
                else:
                    not_parsed_query.append(q)
                # end if
            # end for
        # end if
        if not_parsed_query:
            query = ' '.join(not_parsed_query).strip()
            query_list = query.split()
        # end if

        # check for stopword query
        query_without_stopwords = []
        for extract in query_list:
            if not extract in stopwords:
                query_without_stopwords.append(extract)
        if len(query_without_stopwords) == 0:
            self.error(f"query_string_processed is all stopwords!")
            # to do: handle more gracefully P1
            return self.results

        # stem the query - fix for https://github.com/swirlai/swirl-search/issues/34
        query_stemmed_list = stem_string(clean_string(query)).strip().split()
        query_stemmed_list_len = len(query_stemmed_list)

        # check for non query?
        if query_stemmed_list_len == 0:
            self.warning("Query stemmed list is empty!")
            return self.results

        # prepare query targets
        query_stemmed_target_list = []
        query_target_list = []
        # 1 gram
        if query_stemmed_list_len == 1:
            query_stemmed_target_list.append(query_stemmed_list)
            query_target_list.append(query_list)
        # 2 gram
        if query_stemmed_list_len == 2:
            query_stemmed_target_list.append(query_stemmed_list)
            query_target_list.append(query_list)
            query_stemmed_target_list.append([query_stemmed_list[0]])
            query_target_list.append([query_list[0]])
            query_stemmed_target_list.append([query_stemmed_list[1]])
            query_target_list.append([query_list[1]])
        # more grams
        if query_stemmed_list_len >= 3:
            query_stemmed_target_list.append(query_stemmed_list)
            query_target_list.append(query_list)
            for bigram in bigrams(query_stemmed_list):
                query_stemmed_target_list.append(bigram)
            for bigram in bigrams(query_list):
                query_target_list.append(bigram)
            for gram in query_stemmed_list:
                # ignore stopword 1-grams
                if gram in stopwords:
                    continue
                query_stemmed_target_list.append([gram])
            for gram in query_list:
                # ignore stopword 1-grams
                if gram in stopwords:
                    continue
                query_target_list.append([gram])
        if len(query_stemmed_target_list) != len(query_target_list):
            # to do: handle more elegantly?!?
            self.error("len(query_stemmed_target_list) != len(query_target_list), highlighting errors may occur")

        self.query_stemmed_list = query_stemmed_list
        self.not_list = not_list
        self.query_list = query_list
        self.query_stemmed_target_list = query_stemmed_target_list
        self.query_target_list = query_target_list
        self.query_has_numeric = query_has_numeric

    ############################################

    def process(self):

        RELEVANCY_CONFIG = SWIRL_RELEVANCY_CONFIG

        updated = 0
        dict_result_lens = {}
        list_query_lens = []
        hit_dict = {}

        ############################################
        # PASS 1
        # For each results set from all providers that returned one.
        # to do: refactor the names so it is clearer, e.g. json_result instead of result, result_set instead of results
        for results in self.results:

            ############################################
            # result set
            highlighted_json_results = []
            if not results.json_results:
                continue
            # prepare the query for this result set, it can be different for each provider
            self.prepare_query(results.query_string_to_provider, results.result_processor_json_feedback)
            # capture query len
            list_query_lens.append(len(self.query_list))
            # iterate through the items in the result set
            for item in results.json_results:
                if 'explain' in item:
                    dict_score = item['explain']
                    item['dict_score'] = dict_score
                    dict_len = {}
                    # field length
                    # to do: refactor below to avoid duplication of code
                    for field in RELEVANCY_CONFIG:
                        if field in item:
                            if type(item[field]) == list:
                                # to do: handle this better
                                item[field] = item[field][0]
                            # result_field is shorthand for item[field]
                            result_field = clean_string(item[field]).strip()
                            # check for zero-length result
                            if result_field:
                                if len(result_field) == 0:
                                    continue
                            # prepare result field
                            if result_field.startswith('http'):
                                # the field is a URL, split it on -
                                if '-' in result_field:
                                    result_field = result_field.replace('-', ' ')
                            result_field_list = result_field.strip().split()
                            if field in dict_len:
                                self.warning("duplicate field?")
                            else:
                                dict_len[field] = len(result_field_list)
                            if field in dict_result_lens:
                                dict_result_lens[field].append(len(result_field_list))
                            else:
                                dict_result_lens[field] = []
                                dict_result_lens[field].append(len(result_field_list))
                            # end if
                        # end if
                    # end for
                    item['dict_len'] = dict_len
                    continue
                if not 'hits' in item:
                    item['hits'] = {}
                ############################################
                # result item
                dict_score = {}
                dict_score['stems'] = ' '.join(self.query_stemmed_list)
                dict_len = {}
                notted = ""
                for field in RELEVANCY_CONFIG:
                    if field in item:
                        if type(item[field]) == list:
                            # to do: handle this better
                            item[field] = item[field][0]
                        # result_field is shorthand for item[field]
                        # item[field] needs to be a string from this point forward.
                        # code expects this and blows up otherwise.
                        item[field] = json_to_flat_string(item[field],deadman=100)
                        result_field = clean_string(item[field]).strip()
                        # check for zero-length result
                        if result_field:
                            if len(result_field) == 0:
                                continue
                        # prepare result field
                        if result_field.startswith('http'):
                            # the field is a URL, split it on -
                            if '-' in result_field:
                                result_field = result_field.replace('-', ' ')
                        result_field_nlp = nlp(result_field)
                        result_field_list = result_field.strip().split()
                        # fix for https://github.com/swirlai/swirl-search/issues/34
                        result_field_stemmed = stem_string(result_field)
                        result_field_stemmed_list = result_field_stemmed.strip().split()
                        if len(result_field_list) != len(result_field_stemmed_list):
                            self.error("len(result_field_list) != len(result_field_stemmed_list), highlighting errors may occur")
                        # NOT test
                        for t in self.not_list:
                            if t.lower() in (result_field.lower() for result_field in result_field_list):
                                notted = {field: t}
                                break
                        # field length
                        if field in dict_len:
                            self.warning("duplicate field?")
                        else:
                            dict_len[field] = len(result_field_list)
                        if field in dict_result_lens:
                            dict_result_lens[field].append(len(result_field_list))
                        else:
                            dict_result_lens[field] = []
                            dict_result_lens[field].append(len(result_field_list))
                        # initialize
                        dict_score[field] = {}
                        extracted_highlights = []
                        match_stems = []
                        ###########################################
                        # query vs result_field
                        if match_any(self.query_stemmed_list, result_field_stemmed_list):
                            # capitalize search terms that are capitalied in the result field
                            query = ' '.join(capitalize_search(self.query_list, result_field_list))
                            query_nlp = nlp(query)
                            # check for zero vector
                            empty_query_vector = False
                            if query_nlp.vector.all() == 0:
                                empty_query_vector = True
                            qvr = 0.0
                            label = '_*'
                            if empty_query_vector or result_field_nlp.vector.all() == 0:
                                if len(result_field_list) == 0:
                                    qvr = 0.0
                                else:
                                    qvr = 0.3 + 1/3
                                # end if
                            else:
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
                            if qvr >= float(SWIRL_MIN_SIMILARITY):
                                dict_score[field]['_'.join(self.query_list)+label] = qvr
                            else:
                                logger.debug(f"{self}: item below SWIRL_MIN_SIMILARITY: {'_'.join(self.query_list)+label} ~?= {item}")
                        ############################################
                        # score each query target
                        for stemmed_query_target, query_target in zip(self.query_stemmed_target_list, self.query_target_list):
                            query_slice_stemmed_list = stemmed_query_target
                            query_slice_stemmed_len = len(query_slice_stemmed_list)
                            if '_'.join(query_target) in dict_score[field]:
                                # already have this query slice in dict_score - should not happen?
                                self.warning(f"{query_target} already in dict_score")
                                continue
                            ####### MATCH
                            # iterate across all matches, match on stem
                            # match_all returns a list of result_field_list indexes that match
                            match_list = match_all(query_slice_stemmed_list, result_field_stemmed_list)
                            # truncate the match list, if longer than configured
                            if len(match_list) > SWIRL_MAX_MATCHES:
                                self.warning(f"truncating matches for: {query_slice_stemmed_list}")
                                match_list = match_list[:SWIRL_MAX_MATCHES-1]
                            qw_list = query_target
                            if match_list:
                                key = ''
                                for match in match_list:
                                    extracted_match_list = result_field_list[match:match+query_slice_stemmed_len]
                                    # if the extracted match is capitalized, then capitalize the query
                                    qw_list = capitalize(qw_list, extracted_match_list)
                                    key = '_'.join(extracted_match_list)+'_'+str(match)
                                    # extract query window qw around the match
                                    if (match-(2*query_slice_stemmed_len)-1) < 0:
                                    #     if (match-query_slice_stemmed_len-1) < 0:
                                    #         rw_list = result_field_list_rel[match-query_slice_stemmed_len-1:match+(2*query_slice_stemmed_len)+1]
                                    #     else:
                                        rw_list = result_field_list[match:match+(3*query_slice_stemmed_len)+1]
                                    else:
                                        rw_list = result_field_list[match-(2*query_slice_stemmed_len)-1:match+(2*query_slice_stemmed_len)+1]
                                    # end if
                                    if not self.query_has_numeric and has_numeric(rw_list):
                                        rw_list = remove_numeric(rw_list)
                                        if not rw_list:
                                            rw_list = result_field_list[match:match+(3*query_slice_stemmed_len)+1]
                                    # end if
                                    dict_score[field][key] = 0.0
                                    ######## SIMILARITY vs WINDOW
                                    rw_nlp = nlp(' '.join(rw_list))
                                    if rw_nlp.vector.all() == 0:
                                        dict_score[field][key] = 0.31 + 1/3
                                    qw_nlp = nlp(' '.join(qw_list))
                                    if qw_nlp.vector.all() == 0:
                                        dict_score[field][key] = 0.32 + 1/3
                                    if dict_score[field][key] == 0.0:
                                        qw_nlp_sim = qw_nlp.similarity(rw_nlp)
                                        if qw_nlp_sim:
                                            # self.warning(f"compare: {qw_nlp} sim? {rw_nlp} = {qw_nlp_sim}")
                                            if qw_nlp_sim >= float(SWIRL_MIN_SIMILARITY):
                                                dict_score[field][key] = qw_nlp_sim
                                            else:
                                                logger.debug(f"{self}: item below SWIRL_MIN_SIMILARITY: {' '.join(qw_list)} ~?= {item}")
                                    if dict_score[field][key] == 0.0:
                                        del dict_score[field][key]
                                    ######### COLLECT MATCHES FOR HIGHLIGHTING
                                    for extract in extracted_match_list:
                                        if extract in extracted_highlights:
                                            continue
                                        extracted_highlights.append(extract)
                                    if '_'.join(query_slice_stemmed_list) not in match_stems:
                                        match_stems.append('_'.join(query_slice_stemmed_list))
                                # end for
                            # end if match_list
                        # end for
                        if dict_score[field] == {}:
                            del dict_score[field]
                        ############################################
                        # highlight
                        item[field] = item[field].replace(SWIRL_HIGHLIGHT_START_CHAR,'')   # remove old
                        item[field] = item[field].replace(SWIRL_HIGHLIGHT_END_CHAR,'')   # remove old
                        field_hits = position_dict(remove_tags(item[field]), extracted_highlights)
                        item['hits'][field] = {}
                        item['hits'][field] = field_hits
                        # fix for https://github.com/swirlai/swirl-search/issues/33
                        item[field] = highlight_list(remove_tags(item[field]), extracted_highlights)
                    # end if
                # end for field in RELEVANCY_CONFIG:
                if notted:
                    item['NOT'] = notted
                else:
                    item['dict_score'] = dict_score
                    item['dict_len'] = dict_len
            # end for result in results.json_results:
        # end for results in self.results:
        ############################################
        # compute field means
        dict_len_median = {}
        for field in dict_result_lens:
            dict_len_median[field] = median(dict_result_lens[field])
        # compute query length adjustmnet
        # dict_query_lens = {}

        ############################################
        # PASS 2
        # score results by field, adjusting for field length
        for results in self.results:
            if not results.json_results:
                continue
            for item in results.json_results:
                item['swirl_score'] = 0.0
                # check for not
                if 'NOT' in item:
                    item['swirl_score'] = -1.0 + 1/3
                    item['explain'] = { 'NOT': item['NOT'] }
                    del item['NOT']
                    break
                # retrieve the scores and lens from pass 1
                if 'dict_score' in item:
                    dict_score = item['dict_score']
                    del item['dict_score']
                else:
                    continue
                if 'dict_len' in item:
                    dict_len = item['dict_len']
                    del item['dict_len']
                else:
                    continue
                # score the item
                dict_len_adjust = {}
                for f in dict_score:
                    if f in RELEVANCY_CONFIG:
                        weight = RELEVANCY_CONFIG[f]['weight']
                    else:
                        continue
                    len_adjust = float(dict_len_median[f] / dict_len[f])
                    dict_len_adjust[f] = len_adjust
                    qlen_adjust = float(median(list_query_lens) / len(results.query_string_to_provider.strip().split()))
                    for k in dict_score[f]:
                        if k.startswith('_'):
                            continue
                        if not dict_score[f][k]:
                            continue
                        if dict_score[f][k] >= float(SWIRL_MIN_SIMILARITY):
                            rank_adjust = 1.0 + (1.0 / sqrt(item['searchprovider_rank']))
                            if k.endswith('_*') or k.endswith('_s*'):
                                item['swirl_score'] = item['swirl_score'] + (weight * dict_score[f][k]) * (len(k) * len(k))
                            else:
                                item['swirl_score'] = item['swirl_score'] + (weight * dict_score[f][k]) * (len(k) * len(k)) * len_adjust * qlen_adjust * rank_adjust
                        # end if
                    # end for
                # end for
                for f in dict_score:
                    if f in dict_len_adjust:
                        dict_score[f]['result_length_adjust'] = dict_len_adjust[f]
                        dict_score[f]['query_length_adjust'] = qlen_adjust
                ####### explain
                item['explain'] = dict_score
                possible_hits = item.get('hits', None)
                if possible_hits:
                    item['explain']['hits'] = item['hits']
                    del item['hits']
                else:
                    logger.debug('no hits to move')

                updated = updated + 1
                # save highlighted version
                highlighted_json_results.append(item)
            # end for
            results.save()
        # end for
        ############################################

        self.results_updated = int(updated)

        return self.results_updated