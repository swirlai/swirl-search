'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from django.conf import settings

from swirl.processors.processor import *
from swirl.web_page import PageFetcherFactory, PageFetcher, WebPage

#############################################
#############################################

import json
import re
import os
import requests
from tika import parser
import time
import uuid
import re

from urllib.parse import urlparse

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

#############################################

def is_valid_url(url):
    parsed_url = urlparse(url)
    return bool(parsed_url.scheme)

def get_filename_from_url(url):
    parsed_url = urlparse(url)
    path = parsed_url.path
    filename = os.path.basename(path)
    return filename

def generate_unique_id():
    return str(uuid.uuid4())

def fetch_and_parse(url):
    filename = None
    try:
        logger.debug(f'about to call get on {url}')
        # response = requests.get(url)
        pf = PageFetcherFactory.alloc_page_fetcher(url=url, options= { "cache": "false"})
        if not pf:
            logger.error(f"unable to find fetcher for {url}")
            return None

        page = pf.get_page()
        if not page:
            logger.error(f"unable to fetch {url}")
            return None

        logger.debug(f'returned from fetch of {url}')
        file_content = page.get_content()

        # Write content to a temporary file
        filename = f'{settings.SWIRL_WRITE_PATH}/tk_{generate_unique_id()}.tmp'
        logger.debug(f'attempting write of content of {url} to {filename}')
        with open(filename, 'wb') as f:
            f.write(file_content)
        # Use Apache Tika to parse the file
        logger.debug(f'about to attempt parse')
        return parser.from_file(filename)
    except Exception as err:
        logger.error(f'{err} : while fetching and parsing')
    finally:
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception as err:
                logger.error(f"Failed to delete file {filename}. Error: {err}")

def clean_tika(input_string):
    # Remove extra spaces, newlines, and tabs using regular expressions
    cleaned_string = re.sub(r'\s+', ' ', input_string.strip())
    return cleaned_string

#############################################

# note: must have tika running
# java -jar tika-server.jar

#############################################

class FetchURLPostResultProcessor(PostResultProcessor):

    type="FetchURLPostResultProcessor"

    def process(self):

        # to do: check that tika is running P1
        # to do: start tika in services.py

        # for tmp
        if not os.path.exists(settings.SWIRL_WRITE_PATH):
            os.makedirs(settings.SWIRL_WRITE_PATH)

        updated = 0
        for result in self.results:
            if result.json_results:
                at_least_one_item = False
                for item in result.json_results:
                    if 'url' in item:
                        if is_valid_url(item['url']):
                            logger.info(f"Fetching: {item['url']}")
                            parsed = fetch_and_parse(item['url'])
                            logger.debug(f"content content for {item['url']}")
                            time.sleep(1) # fix me, get rid of this
                        else:
                            continue
                        if not parsed:
                            self.warning(f"fetch_and_parse failed: {item['url']}")
                            continue
                        at_least_one_field = False
                        if 'metadata' in parsed:
                            if not 'payload' in item:
                                item['payload'] = {}
                            item['payload']['tika_metadata'] = parsed['metadata']
                            at_least_one_field = True
                        if 'content' in parsed:
                            if not 'payload' in item:
                                item['payload'] = {}
                            logger.debug(f"call clean_tika on parse content")
                            item['payload']['tika_body'] = clean_tika(str(parsed['content']))
                            logger.debug(f"back from clean_tika")
                            at_least_one_field = True
                        if at_least_one_field:
                            at_least_one_item = True
                            updated = updated + 1
                if at_least_one_item:
                    result.save()

        return updated
