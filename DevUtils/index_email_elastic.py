'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import sys
import csv
import argparse
import os
import dateutil
from dateutil import parser
from elasticsearch import Elasticsearch

##################################################

def main(argv):

    # arguments
    parser = argparse.ArgumentParser(description="Bulk index email in CSV format to elasticsearch/opensearch")
    parser.add_argument('filespec', help="path to the csv file to load")
    parser.add_argument('-e', '--elasticsearch', help="the URL to elasticsearch", default='https://localhost:9200/')
    parser.add_argument('-i', '--index', help="the index to receive the email messages", default='email')
    parser.add_argument('-m', '--max', help="maximum number of rows to index", default=0)
    parser.add_argument('-u', '--username', default='elastic', help="the elastic user, default 'elastic'")
    parser.add_argument('-p', '--password', help="the password for the elastic user")
    parser.add_argument('-v', '--no-verify', help="don't verify certificates", default=False, action="store_true")
    parser.add_argument('-c', '--cacert', help="path to cert file", default=None)

    args = parser.parse_args()

    if not os.path.exists(args.filespec):
        print(f"Error: file not found: {args.filespec}")
        return

    csv.field_size_limit(sys.maxsize)

    f = open(args.filespec, 'r')
    csvr = csv.reader(f, quoting=csv.QUOTE_ALL)
    # Insert path to Elastic cert below
    ca_certs = args.cacert
    no_verify = args.no_verify

    es = Elasticsearch(basic_auth=tuple((args.username, args.password)),
                       hosts=args.elasticsearch,
                       verify_certs=(not no_verify),
                       ca_certs=ca_certs
                       )
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
                s_date = field[field.find(':')+1:].strip()
                dt = dateutil.parser.parse(s_date)
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
                flag = True
        # end for
        # create the content field
        email['content'] = body
        res = es.index(index=args.index, document=email)
        rows = rows + 1
        if rows % 100 == 0:
            print(f"Indexed {rows} records so far...")
        if int(args.max) > 0:
            if rows > int(args.max):
                break
    # end for

#############################################

if __name__ == "__main__":
    main(sys.argv)

# end