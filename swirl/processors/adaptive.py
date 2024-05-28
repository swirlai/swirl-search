'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.processors.processor import *
from swirl.processors.utils import clean_string, get_mappings_dict

#############################################
#############################################

class AdaptiveQueryProcessor(QueryProcessor):

    type = 'AdaptiveQueryProcessor'

    def process(self):

        # TAG: processing
        # Note: WOT is "without tags"

        query_wot_list = []
        dict_tags = {}
        tag = ""
        cannonical_provider_tag_set = {s.lower() for s in self.tags}

        for term in self.query_string.strip().split():
            val = ""
            if ':' in term:
                if term.endswith(':'):
                    # next term is tag
                    tag = term[:-1]
                    continue
                else:
                    tag = term.split(':')[0]
                    val = term.split(':')[1]
                # end if
            else:
                if tag:
                    val = term
                else:
                    query_wot_list.append(term)
                    continue
                # end if
            # end if
            if tag:
                if val:
                    if tag.lower() not in cannonical_provider_tag_set:
                        query_wot_list.append(term)
                    else:
                        if not tag.lower() in dict_tags:
                            dict_tags[tag.lower()] = []
                        dict_tags[tag.lower()].append(val)
                        query_wot_list.append(val)
                # end if
            # end if

        if self.tags:
            # if this provider has tags
            adapted_query_list = []
            for tag in self.tags:
                if tag.lower() in dict_tags:
                    # if the provider has a tag specified in this query
                    adapted_query_list.append(' '.join(dict_tags[tag.lower()]))
            if adapted_query_list:
                lower_adapted_query = ' '.join(adapted_query_list).lower()
                if 'not' in lower_adapted_query:
                    self.query_string = ' '.join(adapted_query_list)
                else:
                    # replace the query with just that text
                    return ' '.join(adapted_query_list)
            else:
                self.query_string = ' '.join(query_wot_list)
            # end if
        else:
            self.query_string = ' '.join(query_wot_list)

        query = clean_string(self.query_string).strip()
        query_list = query.split()

        # NOT tag
        # parse the query into list_not and list_and
        list_not = []
        list_and = []
        lower_query = ' '.join(query_list).lower()
        lower_query_list = lower_query.split()
        if 'not' in lower_query_list:
            list_and = query_list[:lower_query_list.index('not')]
            list_not = query_list[lower_query_list.index('not')+1:]
        else:
            for q in query_list:
                if q.startswith('-'):
                    list_not.append(q[1:])
                else:
                    list_and.append(q)
            # end for
        # end if

        if len(list_not) > 0:
            processed_query = ""
            dict_query_mappings = get_mappings_dict(self.query_mappings)
            not_cmd = False
            not_char = ""
            if 'NOT' in dict_query_mappings:
                not_cmd = bool(dict_query_mappings['NOT'])
            if 'NOT_CHAR' in dict_query_mappings:
                not_char = str(dict_query_mappings['NOT_CHAR'])
            if not_cmd and not_char:
                # leave the query as is, since it supports both NOT and -term
                return query
            if not_cmd:
                processed_query = ' '.join(list_and) + ' ' + 'NOT ' + ' '.join(list_not)
                return processed_query.strip()
            if not_char:
                processed_query = ' '.join(list_and) + ' '
                for t in list_not:
                    processed_query = processed_query + not_char + t + ' '
                return processed_query.strip()
            if not (not_cmd or not_char):
                self.warning(f"Provider does not support NOT in query, removing NOTted portion!")
                # remove the notted portion
                return ' '.join(list_and)

        # self.warning(f"query: {query}")

        return query

#############################################

class NoModQueryProcessor(QueryProcessor):

    type = 'NoModQueryProcessor'

    def process(self):
        
        if self.tags:
            for tag in self.tags:
                tagx = tag + ':'
                if self.query_string.lower().startswith(tagx.lower()):
                    return self.query_string[len(tagx):]
        
        return self.query_string

