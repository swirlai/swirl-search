'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from django.conf import settings

from swirl.processors.processor import *

#############################################
#############################################

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

import re
from datetime import datetime
import copy

class DateFinderResultProcessor(ResultProcessor):

    type="DateFinderResultProcessor"

    def __init__(self, results, provider, query_string, request_id='', **kwargs):
        super().__init__(results, provider, query_string, request_id=request_id, **kwargs)

    def process(self):

        date_regex = r'\b(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s\d{1,2},\s\d{4}|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d{1,2},\s\d{4})\b'

        updated = 0
        for item in self.results:
            if 'date_published' in item:
                if item['date_published'] == 'unknown':
                    matches = re.findall(date_regex, item['body'])
                    if matches:
                        for match in matches:
                            try:
                                if '/' in match:
                                    date = datetime.strptime(match, '%m/%d/%Y')
                                elif '.' in match:
                                    date = datetime.strptime(match, '%m.%d.%Y')
                                elif '-' in match:
                                    date = datetime.strptime(match, '%m-%d-%Y')
                                elif len(match.split()[0]) > 3:  # Check if month name is full month name
                                    date = datetime.strptime(match, '%B %d, %Y')
                                else:
                                    date = datetime.strptime(match, '%b %d, %Y')
                                item['date_published'] = date.strftime('%Y-%m-%d %H:%M:%S')
                                updated = updated + 1
                            except ValueError:
                                logger.warning(f'ignoring invalud date {match}')
                                continue
                            break
                # end if
            # end if
        # end for

        self.processed_results = self.results
        self.modified = updated
        return self.modified
