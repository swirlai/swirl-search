'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.0
'''

# load spacy
import spacy
nlp = spacy.load('en_core_web_md')

from .generic import *
from .relevancy import *
from .spellcheck_query import *

# Add new SWIRL processors here
from .swirl_result_matches import *