'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from django.conf import settings

from swirl.processors.processor import *

#############################################    
#############################################    

import json
import re
import os

from datetime import datetime

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

class WriteToFileSystemPostResultProcessor(PostResultProcessor):

    type="WriteToFileSystemPostResultProcessor"

    def process(self):

        result_item_list = []
        for result in self.results:
            if result.json_results:
                for item in result.json_results:
                    result_item_list.append(item)

        base_filename = re.sub(r'\W+', '', self.search.query_string)
        base_filename = base_filename.replace(' ', '_')

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if settings.SWIRL_WRITE_PATH:
            target_filename = f"{settings.SWIRL_WRITE_PATH}/{base_filename}_{timestamp}.json"
        else:
            self.warning("SWIRL_WRITE_PATH not configured!")
            target_filename = f"{base_filename}_{timestamp}.json"

        if not os.path.exists(settings.SWIRL_WRITE_PATH):
            os.makedirs(settings.SWIRL_WRITE_PATH)

        with open(target_filename, 'w') as file:
            json.dump(result_item_list, file)

        logger.info(f"{self.type}: wrote {len(result_item_list)} records to {target_filename}")
        
        # this processor does not modify anything
        return 0