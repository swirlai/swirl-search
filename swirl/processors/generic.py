'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
'''

from datetime import datetime

from jsonpath_ng import parse
from jsonpath_ng.exceptions import JsonPathParserError

from swirl.processors.processor import *
from swirl.processors.utils import clean_string, create_result_dictionary
from swirl.connectors.utils import get_mappings_dict
  
#############################################    
#############################################    

class GenericQueryProcessor(QueryProcessor):

    type = 'GenericQueryProcessor'
    
    def process(self):
        return clean_string(self.query_string).strip()
                
#############################################    

class AdaptiveQueryProcessor(QueryProcessor):

    type = 'AdaptiveQueryProcessor'
    
    def process(self):

        query = clean_string(self.query_string).strip()
        query_list = query.split()

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
                self.warning(f"Provider does not support NOT in query: {self.query_string}")
                # remove the notted portion
                return ' '.join(list_and)

        return query

#############################################    

class GenericResultProcessor(ResultProcessor):

    type="GenericResultProcessor"

    def process(self):

        self.processed_results = self.results
        return self.processed_results

#############################################    

from dateutil import parser

import re
from re import error as re_error

class MappingResultProcessor(ResultProcessor):

    type="MappingResultProcessor"

    def process(self):

        list_results = []
        json_types = [str,int,float,list,dict]

        use_payload = True
        if 'NO_PAYLOAD' in self.provider.result_mappings:
            use_payload = False

        result_number = 1
        for result in self.results:
            swirl_result = create_result_dictionary()
            payload = {}
            # report searchprovider rank, not ours
            swirl_result['searchprovider_rank'] = result_number
            swirl_result['date_retrieved'] = str(datetime.now())
            #############################################  
            # mappings are in form swirl_key=source_key, where source_key can be a json_string e.g. _source.customer_full_name
            # to do: support swirl_key=source_key1|source_key2|source_key3
            if self.provider.result_mappings:
                mappings = self.provider.result_mappings.split(',')
                for mapping in mappings:
                    stripped_mapping = mapping.strip()
                    # control codez
                    if stripped_mapping == 'NO_PAYLOAD':
                        use_payload = False
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
                        jxp_key = f'$.{k[1:-1]}'
                        try:
                            jxp = parse(jxp_key)
                            # search result for this 
                            matches = [match.value for match in jxp.find(result)]
                        except JsonPathParserError:
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
                        bound_template = source_key.format(**result_dict)
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
                                                result_dict[source_key] = str(parser.parse(str(result_dict[source_key])))
                                            else:
                                                result_dict[source_key] = str(result_dict[source_key])
                                            # end if
                                        # end if
                                        if type(swirl_result[swirl_key]) == type(result_dict[source_key]):
                                            # same type, copy it
                                            if 'date' in swirl_key.lower():
                                                if swirl_result[swirl_key] == "":
                                                    swirl_result[swirl_key] = str(parser.parse(result_dict[source_key]))
                                                else:
                                                    payload[swirl_key+"_"+source_key] = str(parser.parse(result_dict[source_key]))
                                            else:
                                                if swirl_result[swirl_key] == "":
                                                    swirl_result[swirl_key] = result_dict[source_key]
                                                else:
                                                    payload[swirl_key+"_"+source_key] = result_dict[source_key]
                                        else:
                                            # different type, so payload it
                                            if use_payload:
                                                payload[swirl_key] = result_dict[source_key]
                                        # end if
                                    else:
                                        if use_payload:
                                            payload[swirl_key] = result_dict[source_key]
                                        # end if
                                    # end if
                                else:
                                    # no target key specified, so it will go into payload with that name
                                    # since it was specified we do not check NO_PAYLOAD
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
            # try to find a title, if none provided
            if swirl_result['title'] == "":
                if swirl_result['url']:
                    swirl_result['title'] = swirl_result['url']
                elif swirl_result['author']:
                    swirl_result['title'] = swirl_result['author']
                # end if
            # end if
            swirl_result['searchprovider'] = self.provider.name
            list_results.append(swirl_result)
            result_number = result_number + 1
            if result_number > self.provider.results_per_query:  
                break
        # end for

        self.processed_results = list_results
        return self.processed_results
