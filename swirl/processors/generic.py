'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL Preview3
'''

from datetime import datetime

from .utils import create_result_dictionary

import logging as logger
logger.basicConfig(level=logger.INFO)

from jsonpath_ng import parse

#############################################    
#############################################    

chars_allowed_in_query = [' ', '+', '-', '"', "'", '(', ')', '_', '~'] 

def generic_pre_query_processor(query_string):

    module_name = 'generic_pre_query_processor.py'

    try:
        query_clean = ''.join(ch for ch in query_string.strip() if ch.isalnum() or ch in chars_allowed_in_query)
    except NameError as err:
        logger.warning(f'{module_name}: Error: NameError: {err}')
    except TypeError as err:
        logger.warning(f'{module_name}: Error: TypeError: {err}')
    if query_string != query_clean:
        logger.info(f"{module_name}: rewrote query from {query_string} to {query_clean}")

    return query_clean

#############################################    
#############################################    

def generic_query_processor(query_string):

    module_name = 'generic_query_processor'

    # Add new logic here!
    
    return query_string

#############################################    
#############################################    

from dateutil import parser
import re

def generic_result_processor(json_data, provider, query_string):

    module_name = 'generic_result_processor'
    list_results = []

    use_payload = True
    if 'NO_PAYLOAD' in provider.result_mappings:
        use_payload = False

    # transform json
    json_results = json_data

    result_number = 1
    for result in json_results:
        swirl_result = create_result_dictionary()
        payload = {}
        # report searchprovider rank, not ours
        swirl_result['rank'] = result_number
        swirl_result['date_published'] = 'unknown'
        swirl_result['date_retrieved'] = str(datetime.now())
        # to do: figure out url scheme P1
        if 'id' in result:
            swirl_result['url'] = provider.url + '/' + str(result['id'])

        #############################################  
        # handle mappings 
        # provided in form source_key=swirl_key, ..., where source_key can be a json_string e.g. _source.customer_full_name
        # to do: support form 'string {variable} etc etc '=swirl_key
        # to do: support form 'string {variable}' and have that go into payload!!
        if provider.result_mappings:
            mappings = provider.result_mappings.split(',')
            for mapping in mappings:
                stripped_mapping = mapping.strip()
                # control codez
                if stripped_mapping == 'NO_PAYLOAD':
                    use_payload = False
                    continue
                # extract source_key=swirl_key
                swirl_key = ""
                if '=' in stripped_mapping:
                    source_key = stripped_mapping[:stripped_mapping.find('=')]
                    swirl_key = stripped_mapping[stripped_mapping.find('=')+1:]
                else:
                    source_key = stripped_mapping
                # check for template
                template_list = []
                if source_key.startswith("'"):
                    template_list = re.findall(r'\{.*?\}', source_key)
                else:
                    template_list.append('{' + source_key + '}')
                # search for source_keys & construct a result_dict
                result_dict = {}
                for k in template_list:
                    jxp_key = f'$.{k[1:-1]}'
                    jxp = parse(jxp_key)
                    # search result for this 
                    matches = [match.value for match in jxp.find(result)]
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
                    # single mapping
                    if source_key in result_dict:
                        if swirl_key:
                            # user has specified the target location
                            if swirl_key in swirl_result:
                                if type(swirl_result[swirl_key]) == type(result_dict[source_key]):
                                    # same type, copy it
                                    if swirl_key.lower().startswith('date'):
                                        swirl_result[swirl_key] = str(parser.parse(result_dict[source_key]))
                                    else:
                                        swirl_result[swirl_key] = result_dict[source_key]
                                    # end if
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
        # end if

        #############################################  
        # copy remaining fields, avoiding collisions
        for key in result.keys():
            if key in swirl_result.keys():
                if not swirl_result[key]:
                    swirl_result[key] = result[key]
            else:
                if use_payload:
                    # aggregate all other keys to payload
                    payload[key] = result[key]
        # end for

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
        swirl_result['searchprovider'] = provider.name
        list_results.append(swirl_result)
        result_number = result_number + 1
        if result_number > provider.results_per_query:  
            break
    # end for

    return list_results

#############################################    
#############################################    

def generic_post_result_processor(search_id):

    module_name = 'generic_post_result_processor'
    
    # to do: post_result_processor is expected to update the results using a csv and return the number of modified results
    
    return 0
