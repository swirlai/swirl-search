'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

from datetime import datetime

from .utils import create_result_dictionary, highlight

def swirl_result_matches_processor(json_data, provider, query_string):

    # note: this processor accepts a sqlite3 json_array only and returns the expected list of dict_result sets

    list_results = []
    result_number = 1
    
    for row in json_data:
        dict_result = create_result_dictionary()
        dict_result['searchprovider_rank'] = (100 - result_number)
        dict_result['date_retrieved'] = str(datetime.now())
        # there are 5 rows of {'id': 27, 'search_id_id': 38, 'matches':
        result_id = row['id']
        # construct the URL to the result
        dict_result['url'] = provider.url + str(result_id) + '/'
        search_id = row['search_id_id']
        # store the search_id in the payload for now
        dict_result['payload']['search_id'] = search_id
        # now process matches
        wrapper = eval(row['matches'])
        # print(wrapper)
        results = eval(wrapper[0])
        # print(results)
        matching_fields = wrapper[1]
        # to do: consider more than the first match
        result = results[0]
        # this is the first matching result object e.g. rank, title, body and payload
        dict_result['author'] = result['author']
        dict_result['searchprovider'] = result['searchprovider']
        dict_result['date_published'] = result['date_retrieved']
        # find matches
        matches = ""
        if query_string.lower() in result['title'].lower():
            matches = 'title: ' + highlight(result['title'], query_string)
        if query_string.lower() in result['body'].lower():
            if matches:
                matches = matches + '\nbody: ' + highlight(result['body'], query_string)
            else:
                matches = 'body: ' + highlight(result['body'], query_string)
            # end if
        # end if
        if matches:
            matches = matches + '\nurl: ' + result['url']
            dict_result['body'] = matches
        if dict_result['searchprovider']:
            dict_result['title'] = 'Result ' + str(result_id) + ' from ' + dict_result['searchprovider']
        else:
            dict_result['title'] = 'Result ' + str(result_id)
            # end if
        # end if

        # to do: copy the payload in future? P2

        list_results.append(dict_result)

        result_number = result_number + 1
        if result_number > provider.results_per_query:  
            break
        
    # end for

    return list_results