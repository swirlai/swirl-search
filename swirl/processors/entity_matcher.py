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

import ahocorasick

from swirl.processors.utils import remove_tags

def find_matches(entity_list, target_list):
    matches = []
    entities = set(entity_list)
    automaton = ahocorasick.Automaton()

    # Add patterns from source_list to the Aho-Corasick automaton
    for idx, source_string in enumerate(entity_list):
        automaton.add_word(source_string.lower(), (idx, source_string))

    automaton.make_automaton()

    # Find matches in each target_string
    for target_string in target_list:
        for end_index, (source_index, source_string) in automaton.iter(remove_tags(target_string).lower()):
            matches.append(source_string)
            entities.discard(source_string)

        # If all elements are already found, no need to continue
        if not entities:
            break

    return matches

def read_entity_list(path):
    lines = []
    try:
        with open(path, "r") as file:
            for line in file:
                lines.append(line.strip())
        return lines
    except FileNotFoundError:
        return []

#############################################    

class EntityMatcherPostResultProcessor(PostResultProcessor):

    type="EntityMatcherPostResultProcessor"

    def __init__(self, search_id):

        self.entity_list_path = None
        self.entity_list = None
        return super().__init__(search_id)
    
    def process(self):

        # locate the entity dictionary 
        if self.search.tags:
            for tag in self.search.tags:
                if tag.lower().startswith('entitydictionary'):
                    if ':' in tag:
                        self.entity_list_path = tag.split(':')[1]
                    else:
                        self.error(f"Can't extract filename from tag: {tag}")
                        return 0
        
        if not self.entity_list_path:
            self.error("Tag EntityDictionary not found!")
            return 0
                    
        if not self.entity_list:
            self.entity_list = read_entity_list(self.entity_list_path)      
            # self.warning(f'loaded {len(self.entity_list)} entities')  

        if not self.entity_list:
            return 0   

        removed = 0
        match_count = 0
        matched = []

        for result in self.results:

            if result.json_results:

                for item in result.json_results:
                    matches = find_matches(self.entity_list, [item['title'],item['body']])
                    if matches:
                        # self.warning(f"match: {matches}")
                        item['explain']['matched_entity'] = list(matches)
                        matched.append(item)
                        match_count = match_count + 1
                    else:
                        removed = removed + 1
                    # end if
                # end for

                if result.json_results != matched:
                    # self.warning(f"swapping: {len(result.json_results)} ?= {len(matched)}")
                    result.json_results = matched
                    result.save()

        if removed > 0:
            return -1 * removed

        if match_count > 0:
            return match_count

        return 0 