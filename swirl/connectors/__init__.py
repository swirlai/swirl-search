'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from swirl.connectors.requestsget import RequestsGet
from swirl.connectors.requestspost import RequestsPost
from swirl.connectors.sqlite3 import Sqlite3
from swirl.connectors.elastic import Elastic
from swirl.connectors.opensearch import OpenSearch
from swirl.connectors.qdrant import QdrantDB
from swirl.connectors.bigquery import BigQuery
from swirl.connectors.gen_ai import GenAI
from swirl.connectors.microsoft_graph import M365OutlookMessages
from swirl.connectors.microsoft_graph import M365OneDrive
from swirl.connectors.microsoft_graph import M365OutlookCalendar
from swirl.connectors.microsoft_graph import M365SharePointSites
from swirl.connectors.microsoft_graph import MicrosoftTeams
from swirl.connectors.mongodb import MongoDB
from swirl.connectors.snowflake import Snowflake
from swirl.connectors.oracle import Oracle
from swirl.connectors.pinecone import PineconeDB

# uncomment the line below to enable PostgreSQL
# from swirl.connectors.postgresql import PostgreSQL

# Add new connectors here!

def alloc_connector(connector):
    if not connector:
        return None
    return globals()[connector]
