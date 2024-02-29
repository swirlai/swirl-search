'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from sys import path
from os import environ

from datetime import datetime

import json

import snowflake.connector
from snowflake.connector import ProgrammingError

import snowflake.connector
import pandas as pd

import django
import json

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from swirl.connectors.connector import Connector
from swirl.processors.utils import clean_string_keep_punct

########################################
########################################

class SnowflakeAI(Connector):

    type = "SnowflakeAI"

    ########################################

    def execute_search(self, session=None):

        logger.debug(f"{self}: execute_search()")

        account = region = role = warehouse = schema = username = password = ""

        if self.provider.url:
            if ':' in self.provider.url:
                connlist = self.provider.url.split(':')
                if len(connlist) == 5:
                    account = connlist[0]
                    region = connlist[1]
                    role = connlist[2]
                    warehouse = connlist[3]
                    schema = connlist[4]
                else:
                    self.warning("Invalid connection parameters, should be: account:region:role:warehouse:schema")
                    self.status = "ERR_INVALID_CONN"
                    return
        else:
            self.warning("No connection parameters!")
            self.status = "ERR_NO_CONN"
            return

        if self.provider.credentials:
            if ':' in self.provider.credentials:
                # to do: improve, since a credential can have : in it!
                credlist = self.provider.credentials.split(':')
                if len(credlist) == 2:
                    username = credlist[0]
                    password = credlist[1]
                else:
                    self.warning("Invalid credentials, should be: username:password")
                    self.status = "ERR_INVALID_CRED"
                    return
        else:
            self.warning("No credentials!")
            self.status = "ERR_NO_CRED"
            return

        ########################

        self.warning(f"connecting...")
        try:
            # Create a new connection
            ctx=snowflake.connector.connect(
                user=username,
                password=password,
                account=account,
                region=region,
                role=role,
                warehouse=warehouse,
                schema=schema,
            )

            self.warning(f"Getting cursor...")
            cs=ctx.cursor()
            Question = self.query_string_to_provider

            sql_query='''
            select (NWA_REPORTING.ASK_QUESTION_MISHRC04_1(5,'''+"'"+Question+"'"+'''));
            '''

            self.warning(f"Querying...")
            cs.execute(sql_query, timeout=self._swirl_timeout - 2 ) # quit a little earlier than the entire swirl search timeout

            self.warning(f"Detching results...")
            data=cs.fetch_pandas_all()
            self.warning(f"Converting results to frame...")
            dataFrame=pd.DataFrame(data)
            logger.info(f"{self}: converting results to json...")
            json_data = json.loads(dataFrame.to_json())
        except ProgrammingError as err:
            self.status = 'ERR'
            return
        except Exception as err:
            logger.error(f'{err} while exceuting query')
            pass # Let this fall through so it does what it always did for now.



        if not json_data:
            self.error("No json_data found!")
            self.status = "ERR_JSON_DATA"
            return

        response = None

        self.warning("Extracting response key...")
        json_key = list(json_data.keys())[0]
        if json_key in json_data:
            if '0' in json_data[json_key]:
                self.warning("Extracting response body...")
                response = json_data[json_key]['0']
            else:
                self.error(f"Unexpected response from Snowflake AI: {json_data[json_key]}")
                self.status = 'ERR_RESPONSE'
                return
        else:
            self.error(f"Wrapper key not found in body: {json_key}")
            self.status = 'ERR_WRAPPER_KEY_NF'
            return

        if response:
            self.response = response
        else:
            self.error("Could not extract response")
            self.status = "ERR_RESPONSE"
            return

        self.found = 1
        self.retrieved = 1
        self.status = 'READY'
        return

    ########################################

    def normalize_response(self):

        logger.debug(f"{self}: normalize_response()")

        body = ""
        url = ""

        self.warning(f"SnowflakeAI: Response: {self.response}")

        body = self.response

        # extract URL at end
        if 'http' in self.response:
            self.warning("SnowflakeAI: processing More Information")
            url = self.response[self.response.find('http'):self.response.find('"', self.response.find('http')+1)]
            body = body[:body.find("More information :")]
        else:
            self.warning("No link detected in response")

        self.warning("Cleaning response...")
        # remove spaces and \n's
        if body:
            body = ' '.join(filter(None, body.split(' ')))
            body = body.replace('\n', ' ')
            # remove anything unexpected
            body = clean_string_keep_punct(body)

        if 'insufficient context' in body.lower():
            self.found = 0
            self.retrieved = 0
            self.status = 'READY'
            return

        self.warning(f"SnowflakeAI: Body: {body}")

        self.results = [
                {
                    'url': url.replace("\\/", "/"),
                    'title': self.query_string_to_provider,
                    'body': body,
                    'author': 'Snowflake AI',
                    'date_published': str(datetime.now())
                }
        ]

        self.warning("Results saved!")

        return
