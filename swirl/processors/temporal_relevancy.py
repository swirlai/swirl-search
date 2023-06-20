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

        # identify the requested temporal distance 
        temporal_distance = temporal_units = temporal_distance_base = None
        if self.search.tags:
            for tag in self.search.tags:
                if tag.lower().startswith('temporaldistance'):
                    if ':' in tag:
                        temporal_distance_base = tag.split(':')[1]
                    else:
                        self.warning(f"Can't extract temporal distance from tag: {tag}")
                        return 0
                    
        if temporal_distance_base:
            # format d=10
            if '=' in temporal_distance_base:
                temporal_units = temporal_distance_base.split('=')[0]
                temporal_distance = temporal_distance_base.split('=')[1]
            else:
                self.error(f"Can't extract temporal distance in format [days|hours]=distance from tag: {tag}")
                return 0
            
        if not temporal_distance or not temporal_units:
            self.error(f"Temporal distance or units not set! distance:{temporal_distance}, units:{temporal_units}")
            return 0
                    
        # identify the requested minimum relevancy
        minimum_relevancy_score = None
        if self.search.tags:
            for tag in self.search.tags:
                if tag.lower().startswith('minimumrelevancy'):
                    if ':' in tag:
                        minimum_relevancy_score = tag.split(':')[1]
                    else:
                        self.warning(f"Can't extract minimum relevancy from tag: {tag}")
                        return 0
                    
        if not minimum_relevancy_score:
            self.error("Minimum relevancy score not set!")
            return 0

        removed = 0
        temporally_relevant = 0

        # mark time
        current_time = datetime.now()
        temporal_results = []

        for result in self.results:
            if result.json_results:
                for item in result.json_results:
                    if float(item['swirl_score']) <= float(minimum_relevancy_score):
                        removed = removed + 1
                        continue
                    if item['date_published'] != 'unknown':
                        date = datetime.strptime(item['date_published'], '%Y-%m-%d %H:%M:%S')
                        if temporal_units.lower() == 'days':
                            if current_time - date <= timedelta(days=int(temporal_distance)):
                                item['explain']['temporal_match'] = item['date_published']
                                # self.warning('Alert the Doctor!!')
                                temporal_results.append(item)
                                temporally_relevant = temporally_relevant + 1
                            else:
                                # self.warning("Exterminate!")
                                removed = removed + 1
                            continue
                        if temporal_units.lower() == 'hours':
                            if current_time - date <= timedelta(hours=int(temporal_distance)):
                                item['explain']['temporal_match'] = item['date_published']
                                # self.warning('Alert the Doctor!!')
                                temporal_results.append(item)
                                temporally_relevant = temporally_relevant + 1
                            else:
                                # self.warning("Exterminate!")
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