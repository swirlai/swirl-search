'''
@author:     Nicodemus
@contact:    dave@swirl.today
'''
import logging as logger
logger.basicConfig(level=logger.INFO)

from abc import ABCMeta, abstractmethod

from swirl.processors.processor import *
from swirl.processors.utils import clean_string

#############################################
#############################################

class TransformQueryProcessorFactory():
    @staticmethod
    def alloc_query_transform(qxf_type, name, config):
        """
        Get the query transformer based on type
        """
        if qxf_type == "rewrite":
            return RewriteQueryProcessor(name, config)
        elif qxf_type == "synonym":
             return SynonymQueryProcessor(name, config)
        elif qxf_type == "bag":
             return SynonymBagQueryProcessor(name, config)
        else:
            raise ValueError("Invalid Query Transform Processor type")


class AbstractTransformQueryProcessor(QueryProcessor, metaclass=ABCMeta):
    """
    Holder for Query shared transform fuctionality and interfaces
    """

    def __init__(self, name, config):
        self.name = name
        self.config = config

    @abstractmethod
    def parse_config(self):
        """Parse config and extract the rules or fail if the config is not correct"""
        pass

    @abstractmethod
    def process(self):
        """Process input data according to the rules """
        pass


class RewriteQueryProcessor(AbstractTransformQueryProcessor):

    """
    parse rules and based on them replace patterns in the
    input string w/ the appropriate substitution or nothing, if that is indicated
    """

    type = 'RewriteQueryProcessor'

    def parse_config(self):
        logger.info(f'parse config {self.type}')
        pass

    def process(self):
        return clean_string(self.query_string).strip()

#############################################

class SynonymQueryProcessor(AbstractTransformQueryProcessor):

    type = 'SynonymQueryProcessor'

    def parse_config(self):
        logger.info(f'parse config {self.type}')
        pass

    def process(self):
        return clean_string(self.query_string).strip() + " test"

#############################################

class SynonymBagQueryProcessor(AbstractTransformQueryProcessor):

    type = 'SynonymBagQueryProcessor'

    def parse_config(self):
        logger.info(f'parse config {self.type}')
        pass

    def process(self):
        return clean_string(self.query_string).strip() + " test"
