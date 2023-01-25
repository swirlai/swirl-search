'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import sys
import csv
import argparse
import os
from dateutil import parser
from urllib.parse import urlparse
from opensearchpy import OpenSearch

##################################################

def main(argv):

    # arguments
    aparse = argparse.ArgumentParser(description="Bulk index email in CSV format to OpenSearch")
    aparse.add_argument('filespec', help="path to the csv file to load")
    aparse.add_argument('-o', '--opensearch', help="the URL to opensearch", default='http://localhost:9200/')
    aparse.add_argument('-i', '--index', help="the index to receive the email messages", default='email')
    aparse.add_argument('-m', '--max', help="maximum number of rows to index", default=0)
    aparse.add_argument('-u', '--username', default='admin', help="the OpenSearch user, default 'admin'")
    aparse.add_argument('-p', '--password', help="the password for the OpenSearch user")
    args = aparse.parse_args()

    if not os.path.exists(args.filespec):
        print(f"Error: file not found: {args.filespec}")
        return

    f = open(args.filespec, 'r')
    csvr = csv.reader(f, quoting=csv.QUOTE_ALL)

    parsed_url = urlparse(args.opensearch)
    host = parsed_url.hostname
    port = parsed_url.port

    es = OpenSearch(http_auth=(args.username, args.password), hosts=[{'host': host, 'port': port}], use_ssl = True, verify_certs = False, ssl_assert_hostname = False, ssl_show_warn = False)

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
                flag = True
        # end for
        # create the content field
        email['content'] = body
        res = es.index(index='email', body=email, refresh=True)
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