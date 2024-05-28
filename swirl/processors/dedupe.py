'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from swirl.processors.processor import *
from django.conf import settings
from swirl.spacy import nlp

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

#############################################
#############################################

SWIRL_DEDUPE_FIELD = getattr(settings, 'SWIRL_DEDUPE_FIELD', 'url')
SWIRL_DEDUPE_SIMILARITY_FIELDS = getattr(settings, 'SWIRL_DEDUPE_SIMILARITY_FIELDS', ['title', 'body'])
SWIRL_DEDUPE_SIMILARITY_MINIMUM = getattr(settings, 'SWIRL_DEDUPE_SIMILARITY_MINIMUM', 0.95)

def _get_field_value_top_level_or_payload (item, field):
    """
    try to get the field value in both the top level record and the payload sidecar.
    """
    ret = item.get(field, None)
    if not ret and item.get('payload', None):
        ret = item['payload'].get(field, None)
    return ret

def _dedup_results (results, dedupe_key_dict, deduped_item_list, grouping_field):
    n_dups = 0
    for item in results:
        f_value = _get_field_value_top_level_or_payload(item, grouping_field)
        if f_value:
            if f_value in dedupe_key_dict:
                n_dups = n_dups + 1
                continue # skip item, it's a duplicate
            else:
                dedupe_key_dict[f_value] = 1 ## add item, not a dup
        else:
            pass # add item, not a dup
        # end if
        deduped_item_list.append(item)
    # end for
    return n_dups

class DedupeByFieldResultProcessor(ResultProcessor):
    """
    This is meant to remove duplcates from a single source, this is what differentiates from a post result processor
    """

    type="DedupeByFieldResultProcessor"

    def __init__(self, results, provider, query_string, request_id='', **kwargs):
        super().__init__(results, provider, query_string, request_id=request_id, **kwargs)

    def process(self):
        ## nothing to do
        if not self.provider.result_grouping_field:
            self.processed_results = self.results
            return False

        results = self.results
        provider = self.provider

        dedupe_key_dict = {}
        deduped_item_list = []
        dupes = 0
        dupes = dupes + _dedup_results(results, dedupe_key_dict, deduped_item_list, self.provider.result_grouping_field)
        logger.debug(f'removed {dupes} using field {provider.result_grouping_field} from result with length : {len(results)}')
        self.processed_results = deduped_item_list

        if dupes > 0:
            return -1 * dupes
        
        return 0

class DedupeByFieldPostResultProcessor(PostResultProcessor):

    type="DedupeByFieldPostResultProcessor"

    def process(self):

        dupes = 0
        dedupe_key_dict = {}
        for result in self.results:
            deduped_item_list = []
            dupes = dupes + _dedup_results(result.json_results, dedupe_key_dict, deduped_item_list, SWIRL_DEDUPE_FIELD)
            result.json_results = deduped_item_list
            result.save()
        # end for

        if dupes > 0:
            self.results_updated = -1 * dupes
        else:
            self.results_updated = 0

        return self.results_updated

#############################################

class DedupeBySimilarityPostResultProcessor(PostResultProcessor):

    type="DedupeBySimilarityPostResultProcessor"

    def process(self):

        dupes = 0
        nlp_list = []
        for result in self.results:
            deduped_item_list = []
            for item in result.json_results:
                content = ""
                for field in SWIRL_DEDUPE_SIMILARITY_FIELDS:
                    if field in item:
                        if field:
                            content = content + ' ' + item[field].strip()
                        # end if
                # end for
                content = content.strip()
                nlp_content = nlp(content)
                dupe = False
                max_sim = 0.0
                for n in nlp_list:
                    sim = nlp_content.similarity(n)
                    if sim > SWIRL_DEDUPE_SIMILARITY_MINIMUM:
                        # similar
                        dupe = True
                        dupes = dupes + 1
                        break
                    else:
                        if sim > max_sim:
                            max_sim = sim
                    # end if
                # end for
                if not dupe:
                    nlp_list.append(nlp_content)
                    deduped_item_list.append(item)
                # end if
            # end for
            result.json_results = deduped_item_list
            logger.debug(f"{self}: result.save()")
            result.save()
        # end for

        if dupes > 0:
            self.results_updated = -1 * dupes
        else:
            self.results_updated = 0
            
        return self.results_updated