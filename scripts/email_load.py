'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
'''

import sys
import csv
from dateutil import parser
import argparse
import os

from elasticsearch import Elasticsearch
import elasticsearch

module_name = 'email_load.py'

##################################################

class bcolors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

##################################################

def main(argv):

    print(f"{bcolors.BOLD}##S#W#I#R#L##1#.#5##############################################################{bcolors.ENDC}")
    # arguments
    parser = argparse.ArgumentParser(description="Bulk index email in CSV format to elasticsearch")
    parser.add_argument('filespec', help="path to the csv file to load")
    parser.add_argument('-e', '--elasticsearch', help="URL to elasticsearch", default='http://localhost:9200/')
    parser.add_argument('-m', '--max', help="maximum number of rows to index", default=0)
    parser.add_argument('-p', '--password', help="password for user 'elastic'")
    args = parser.parse_args()

    if not os.path.exists(args.filespec):
        print(f"{bcolors.FAIL}Error: file not found: {args.filespec}{bcolors.ENDC}")
        return

    f = open(args.filespec, 'r')
    csvr = csv.reader(f, quoting=csv.QUOTE_ALL)
    es = Elasticsearch(http_auth=("elastic", args.password), hosts='')

    print()
    print("Indexing...")

    rows = 0
    for row in csvr:
        if rows == 0:
            rows = 1
            continue
        email = {}
        email['url'] = row[0]
        # process and field the body row[1]
        content = row[1]
        # to do: this might be OS dependent, test on windows might need /r/n or different open incantation
        list_content = content.strip().split('\n')

        body = ""
        flag = False
        for field in list_content:
            if flag:
                body = body + field
                continue
            if field.startswith('Date:'):
                # to do: handle this date correctly!!!!
                s_date = field[field.find(':')+1:].strip()
                dt = parser.parse(s_date)
                email['date_published'] = dt.strftime('%Y-%m-%d %H:%M:%S.%f')
            if field.startswith('Subject:'):
                email['subject'] = field[field.find(':')+1:].strip()
            if field.startswith('To:'):
                email['to'] = field[field.find(':')+1:].strip()
            if field.startswith('X-To:'):
                # overwrite
                email['to'] = field[field.find(':')+1:].strip()
            if field.startswith('From:'):
                email['author'] = field[field.find(':')+1:].strip()
            if field.startswith('X-From:'):
                # overwrite
                email['author'] = field[field.find(':')+1:].strip()
            if field == '':
                # the next one is the body
                # hopefully this is sufficient
                flag = True
        # end for
        # finally, make the content field which is everything !
        email['content'] = body
        res = es.index(index='email', document=email)
        rows = rows + 1
        if rows % 100 == 0:
            print(f"Indexed {rows} records so far...")
        if int(args.max) > 0:
            if rows > args.max:
                break
    # end for

#############################################    
    
if __name__ == "__main__":
    main(sys.argv)

# end