'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from swirl.connectors.elastic import Elastic
from swirl.connectors.requestsget import RequestsGet
from swirl.connectors.sqlite3 import Sqlite3
from swirl.connectors.bigquery import BigQuery

# fix for https://github.com/sidprobstein/swirl-search/issues/55 SWIRL 1.7
# uncomment this to enable PostgreSQL
# from swirl.connectors.postgresql import PostgreSQL

# Add new connectors here!
