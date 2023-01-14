'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from swirl.processors.processor import *
from django.conf import settings
from swirl.spacy import nlp
  
#############################################    
#############################################    

class DedupeByFieldPostResultProcessor(PostResultProcessor):

    type="DedupeByFieldPostResultProcessor"

    def process(self):
        
        dupes = 0
        dedupe_key_dict = {}
        for result in self.results:
            deduped_item_list = []
            for item in result.json_results:
                if settings.SWIRL_DEDUPE_FIELD in item:
                    if item[settings.SWIRL_DEDUPE_FIELD]:
                        if item[settings.SWIRL_DEDUPE_FIELD] in dedupe_key_dict:
                            # dupe
                            dupes = dupes + 1
                            logger.info(f"{self}: Excluding duplicate: {item[settings.SWIRL_DEDUPE_FIELD]}")
                            continue
                        else:
                            # not dupe
                            dedupe_key_dict[item[settings.SWIRL_DEDUPE_FIELD]] = 1
                    else:
                        # dedupe key blank
                        logger.info(f"{self}: Ignoring result {item}, {settings.SWIRL_DEDUPE_FIELD} is blank")
                else:
                    # dedupe key missing
                    self.warning(f"Ignoring result {item}, {settings.SWIRL_DEDUPE_FIELD} is missing")
                # end if
                deduped_item_list.append(item)
            # end for
            result.json_results = deduped_item_list
            result.save()
        # end for

        self.results_updated = dupes
        return self.results_updated

#############################################    

class DedupeBySimilarityPostResultProcessor(PostResultProcessor):

    type="DedupeBySimilarityPostResultProcessor"

    def process(self):
        
        dupes = 0
        nlp_list = []
        for result in self.results:
            deduped_item_list = []
            for item in result.json_results:
                content = ""
                for field in settings.SWIRL_DEDUPE_SIMILARITY_FIELDS:
                    if field in item:
                        if field:
                            content = content + ' ' + item[field].strip()
                        # end if
                # end for                    
                content = content.strip()
                nlp_content = nlp(content)
                dupe = False
                max_sim = 0.0
                for n in nlp_list:
                    sim = nlp_content.similarity(n)
                    if sim > settings.SWIRL_DEDUPE_SIMILARITY_MINIMUM:
                        # similar
                        dupe = True
                        dupes = dupes + 1
                        logger.info(f"{self}: Excluding dupe: {sim} for {item['title']}")
                        break
                    else:
                        if sim > max_sim:
                            max_sim = sim
                    # end if
                # end for
                if not dupe:
                    nlp_list.append(nlp_content)
                    deduped_item_list.append(item)
                # end if
            # end for
            result.json_results = deduped_item_list
            logger.info(f"{self}: result.save()")
            result.save()
        # end for
        
        self.results_updated = dupes
        return self.results_updated