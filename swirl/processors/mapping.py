'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''
import logging
from celery.utils.log import get_task_logger
logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

from datetime import datetime
from jsonpath_ng import parse
from jsonpath_ng.exceptions import JsonPathParserError

from swirl.processors.processor import *
from swirl.processors.result_map_url_encoder import ResultMapUrlEncoder
from swirl.processors.utils import create_result_dictionary, extract_text_from_tags, str_safe_format, date_str_to_timestamp
from swirl.swirl_common import RESULT_MAPPING_COMMANDS

#############################################
#############################################

from dateutil import parser

import re
from re import error as re_error

class MappingResultProcessor(ResultProcessor):

    type="MappingResultProcessor"

    def put_query_terms_from_provider(self, swirl_key, text, lBuf):
        """ remember query terms from the hihglight field of each result"""
        if not ( swirl_key and text ):
            return
        if swirl_key not in ('title_hit_highlights','body_hit_highlights'):
            return
        for teaser_text in text:
            hits = extract_text_from_tags(teaser_text, 'em')
            for hit in hits:
                lBuf.append(str(hit).lower())

    def get_opt_result_processor_feedback_json(self, lBuf):
        """
        Create a JSON object from the list of query terms:
        """
        if not lBuf or len(lBuf)<=0:
            return None

        ret = {
                'result_processor_feedback': {
                'query': {
	                'provider_query_terms': sorted(list(set(lBuf)))
                }
            }
        }
        return ret

    def process(self):

        list_results = []
        provider_query_term_results = []
        result_block = ""

        json_types = [str,int,float,list,dict]
        use_payload = True
        file_system = False
        if 'NO_PAYLOAD' in self.provider.result_mappings:
            use_payload = False
        if 'FILE_SYSTEM' in self.provider.result_mappings:
            file_system = True

        result_number = 1
        for result in self.results:
            swirl_result = create_result_dictionary()
            payload = {}
            # report searchprovider rank, not ours
            swirl_result['searchprovider_rank'] = result_number
            swirl_result['date_retrieved'] = str(datetime.now())
            #############################################
            # mappings are in form swirl_key=source_key, where source_key can be a json_string e.g. _source.customer_full_name
            if self.provider.result_mappings:
                mappings = self.provider.result_mappings.split(',')
                for mapping in mappings:
                    stripped_mapping = mapping.strip()
                    # control codez NO_PAYLOAD, FILE_SYSTEM
                    if stripped_mapping in RESULT_MAPPING_COMMANDS:
                        # ignore, values were set above
                        continue
                    # extract source_key=swirl_key
                    swirl_key = ""
                    if '=' in stripped_mapping:
                        # no need to switch to rfind, since multiple = is not allowed
                        # source key may be a json path
                        swirl_key = stripped_mapping[:stripped_mapping.find('=')]
                        source_key = stripped_mapping[stripped_mapping.find('=')+1:]
                    else:
                        source_key = stripped_mapping
                    # control codez
                    if swirl_key.isupper():
                        # to do: check the result mappings list???
                        if swirl_key == 'BLOCK':
                            result_block = source_key
                        else:
                            # ignore for now
                            continue
                    # check for field list |
                    source_field_list = []
                    if '|' in source_key:
                        source_field_list = source_key.split('|')
                        # self.warning(f"source_field_list! {source_field_list}")
                    if len(source_field_list) == 0:
                        source_field_list.append(source_key)
                    #############################################
                    # check for template
                    template_list = []
                    if source_key.startswith("'"):
                        try:
                            template_list = re.findall(r'\{.*?\}', source_key)
                        except re_error as err:
                            self.error(f"re: {err} in re.findall(r\'\{{.*?\}}\'): {source_key}")
                            return []
                        # end try
                    else:
                        for key in source_field_list:
                            template_list.append('{' + key + '}')
                    # search for source_keys & construct a result_dict
                    result_dict = {}
                    # self.warning(f"template_list: {template_list}")
                    for k in template_list:
                        uc = ResultMapUrlEncoder(f'$.{k[1:-1]}')
                        jxp_key = uc.get_key()
                        try:
                            jxp = parse(jxp_key)
                            # search result for this
                            matches = [uc.get_value(match.value) for match in jxp.find(result)]
                        except JsonPathParserError as err:
                            self.error(f'JsonPathParser: {err} in jsonpath_ng.find: {jxp_key}')
                            return []
                        except (NameError, TypeError, ValueError) as err:
                            self.error(f'{err.args}, {err} in jsonpath_ng.find: {jxp_key}')
                            return []
                        # end try
                        if len(matches) == 1:
                            result_dict[k[1:-1]] = matches[0]
                        else:
                            result_dict[k[1:-1]] = matches
                    if source_key.startswith("'"):
                        # template
                        bound_template =  str_safe_format(source_key, result_dict)
                        if swirl_key:
                            if swirl_key in swirl_result:
                                swirl_result[swirl_key] = bound_template[1:-1]
                            # end if
                        # end if
                    else:
                        #############################################
                        # single mapping
                        for source_key in source_field_list:
                            if source_key in result_dict:
                                if not result_dict[source_key]:
                                    # blank key
                                    continue
                                if swirl_key:
                                    # provider specifies the target
                                    if swirl_key in swirl_result:
                                        if not type(result_dict[source_key]) in json_types:
                                            if 'date' in source_key.lower():
                                                # parser.parse will fill-in a missing time portion etc
                                                result_dict[source_key] = date_str_to_timestamp(result_dict[source_key])
                                            else:
                                                result_dict[source_key] = str(result_dict[source_key])
                                            # end if
                                        # end if
                                        if type(swirl_result[swirl_key]) == type(result_dict[source_key]):
                                            # same type, copy it
                                            if 'date' in swirl_key.lower():
                                                if swirl_result[swirl_key] == "":
                                                    swirl_result[swirl_key] = date_str_to_timestamp(result_dict[source_key])
                                                else:
                                                    payload[swirl_key+"_"+source_key] = date_str_to_timestamp(result_dict[source_key])
                                                # end if
                                            else:
                                                if not swirl_result[swirl_key]:
                                                    swirl_result[swirl_key] = result_dict[source_key]
                                                    self.put_query_terms_from_provider(swirl_key,
                                                                                   swirl_result[swirl_key],
                                                                                   provider_query_term_results)
                                                else:
                                                    payload[swirl_key+"_"+source_key] = result_dict[source_key]
                                                # end if
                                        else:
                                            # not same type, convert it
                                            if 'date' in swirl_key.lower():
                                                if swirl_result[swirl_key] == "":
                                                    if type(result_dict[source_key]) == int:
                                                        # check for int vs long fix for DS-320
                                                        if result_dict[source_key] > 2147483647:
                                                            swirl_result[swirl_key] = str(datetime.fromtimestamp(result_dict[source_key]/1000))
                                                        else:
                                                            swirl_result[swirl_key] = str(datetime.fromtimestamp(result_dict[source_key]))
                                                        # end if
                                                    if type(result_dict[source_key]) == float:
                                                        swirl_result[swirl_key] = str(datetime.fromtimestamp(result_dict[source_key]))
                                                # end if
                                            if type(swirl_result[swirl_key]) == str and type(result_dict[source_key]) == list:
                                                swirl_result[swirl_key] = ' '.join(result_dict[source_key])
                                            # different type, so payload it
                                            if use_payload:
                                                payload[swirl_key] = result_dict[source_key]
                                        # end if
                                    else:
                                        if use_payload:
                                            # to do: check type!!!
                                            if type(result_dict[source_key]) not in [str, int, list, dict]:
                                                payload[swirl_key] = str(result_dict[source_key])
                                            else:
                                                payload[swirl_key] = result_dict[source_key]
                                        # end if
                                    # end if
                                else:
                                    # no target key specified, so it will go into payload with that name
                                    # since it was specified we do not check NO_PAYLOAD
                                    if type(result_dict[source_key]) not in [str, int, list, dict]:
                                        payload[source_key] = str(result_dict[source_key])
                                    else:
                                        payload[source_key] = result_dict[source_key]
                                # end if
                            else:
                                # no results for this mapping were found - normal
                                pass
                            # end if
                        # end for
                # end for
            # end if

            #############################################
            # copy remaining fields, avoiding collisions
            for key in result.keys():
                if key in swirl_result.keys():
                    if not swirl_result[key]:
                        swirl_result[key] = result[key]
                else:
                    if use_payload:
                        if not type(result[key]) in json_types:
                            result[key] = str(result[key])
                        payload[key] = result[key]
                        # end if
                    # end if
            # end for

            # if no date_published, set it to unknown
            # TO DO: maybe this should be left blank? P1 *****
            if swirl_result['date_published'] == "":
                swirl_result['date_published'] = 'unknown'

            #############################################
            # connector specific
            # remove <matched_term> tags from title (northernlight)
            if '<matched_term>' in swirl_result['title']:
                swirl_result['title'] = swirl_result['title'].replace('<matched_term>', '')
                swirl_result['title'] = swirl_result['title'].replace('</matched_term>', '')

            #############################################
            # final assembly
            if payload:
                swirl_result['payload'] = payload
            if result_block:
                swirl_result['result_block'] = result_block
            # try to find a title, if none provided
            if swirl_result['title'] == "":
                if swirl_result['url']:
                    swirl_result['title'] = swirl_result['url']
                elif swirl_result['author']:
                    swirl_result['title'] = swirl_result['author']
                # end if
            # end if
            # mark results from SearchProviders with result_mapping FILE_SYSTEM
            if file_system:
                swirl_result['_relevancy_model'] = 'FILE_SYSTEM'
            swirl_result['searchprovider'] = self.provider.name
            list_results.append(swirl_result)
            result_number = result_number + 1
            # stop if we have enough results
            if result_number > self.provider.results_per_query:
                self.warning("Truncating extra results, found & retrieved may be incorrect")
                break
            # unique list of terms from highligts
        # end for

        fb = self.get_opt_result_processor_feedback_json(provider_query_term_results)
        if fb:
            list_results.append(fb)
        self.processed_results = list_results
        return self.processed_results
