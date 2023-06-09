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
from datetime import datetime, timedelta

class TemporalRelevancyPostResultProcessor(PostResultProcessor):

    type="TemporalRelevancyPostResultProcessor"

    def process(self):

        removed = 0
        temporally_relevant = 0

        # mark time
        current_time = datetime.now()
        temporal_results = []

        for result in self.results:
            if result.json_results:
                for item in result.json_results:
                    if float(item['swirl_score']) <= settings.SWIRL_MIN_RELEVANCY_SCORE:
                        removed = removed + 1
                        continue
                    if item['date_published'] != 'unknown':
                        date = datetime.strptime(item['date_published'], '%Y-%m-%d %H:%M:%S')
                        if settings.SWIRL_MAX_TEMPORAL_DISTANCE_UNITS == 'days':
                            if current_time - date <= timedelta(days=settings.SWIRL_MAX_TEMPORAL_DISTANCE):
                                item['explain']['temporal_match'] = item['date_published']
                                # self.warning('Alert the Doctor! Temporal Hit!')
                                temporal_results.append(item)
                                temporally_relevant = temporally_relevant + 1
                            else:
                                removed = removed + 1
                            continue
                        if settings.SWIRL_MAX_TEMPORAL_DISTANCE_UNITS == 'hours':
                            if current_time - date <= timedelta(hours=settings.SWIRL_MAX_TEMPORAL_DISTANCE):
                                item['explain']['temporal_match'] = item['date_published']
                                # self.warning('Alert the Doctor! Temporal Hit!')
                                temporal_results.append(item)
                                temporally_relevant = temporally_relevant + 1
                            else:
                                removed = removed + 1
                            continue
                    else:
                        # logger.warning(f"Failed temporal check: {item['body']}")
                        removed = removed + 1
                    # end if
                # end for

                if result.json_results != temporal_results:
                    result.json_results = temporal_results
                    result.save()
                # end if
            # end if
        # end for

        return -1 * removed