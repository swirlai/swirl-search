'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import argparse
import sys
import os
import glob
import json

import requests
from requests.auth import HTTPBasicAuth
from http import HTTPStatus

module_name = 'swirl_load.py'

from swirl.banner import SWIRL_BANNER, bcolors

##################################################

def main(argv):

    print(f"{SWIRL_BANNER}")
    print()
    # arguments
    parser = argparse.ArgumentParser(description="Bulk load Swirl objects in json format")
    parser.add_argument('filespec', help="path to one or more json files to load, optionally including wildcards, example folder-name/*.txt")
    parser.add_argument('-d', '--debug', action="store_true", help="provide debugging information")
    parser.add_argument('-u', '--username')
    parser.add_argument('-p', '--password')
    parser.add_argument('-s', '--swirl', default="http://localhost:8000/", help="the url of the swirl server")
    args = parser.parse_args()

    list_files = []
    if args.filespec:
        list_files = glob.glob(args.filespec)
    else:
        print(f"{module_name}: no input file(s) specified: {args.filespec}")
        sys.exit(1)
    if list_files == []:
        print(f"{module_name}: no files found: {args.filespec}")
        sys.exit(1)
                
    for s_file in list_files:

        if os.path.isdir(s_file):
            # recurse into directory
            for new_file in glob.glob(s_file + '/*'):
                list_files.append(new_file)
        
        try:
            f = open(s_file, 'r')
        except Exception as err:
            print(f"{module_name}: Error opening {s_file}: {err}")
            continue
        
        # read the file
        try:
            json_data = json.load(f)
        except Exception as err:
            print(f"{module_name}: Error reading {s_file}: {err}")
            continue
        f.close()

        if type(json_data) == list:
            json_list = json_data
        else:
            json_list = []
            json_list.append(json_data)
        
        if args.debug:
            print(f"{module_name}: debug: Swirl='{args.swirl}'")

        records = 0
        errors = 0
        for json_item in json_list:
            # determine type of item, and thus target
            target = None
            if 'name' in json_item.keys():
                # searchprovider
                target = 'searchproviders'
            elif 'query_string' in json_item.keys():
                # search
                target = 'search'
            elif 'search_id' in json_item.keys():
                # result
                target = 'results'
            if not target:
                print(f"{module_name}: Error: unknown object type:'{json_item}', ignoring")
                continue
            # feed it
            url = args.swirl + "swirl/" + target + "/"
            if args.debug:
                print(f"{module_name}: debug POST: '{json_item}' to: {url}")
            try:
                response = requests.post(url, headers={'Content-type': 'application/json'}, json=json_item, auth=HTTPBasicAuth(username=args.username, password=args.password))
            except ConnectionError as err:
                print(f'{module_name}: Error: requests.post reports {err}')
                continue
            records = records + 1
            if response.status_code != 201:
                print(f'{module_name}: Error: request.get returned: {response.status_code} {response.reason}')
                errors = errors + 1
                continue
            # end if
        # end for

        print(f"{module_name}: fed {records} into Swirl, {errors} errors")

#############################################    
    
if __name__ == "__main__":
    main(sys.argv)

# end