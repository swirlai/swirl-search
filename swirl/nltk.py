'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import logging
logger = logging.getLogger(__name__)

from django.conf import settings

from nltk.corpus import stopwords

module_name = 'nltk.py'

try:
    SWIRL_DEFAULT_QUERY_LANGUAGE = getattr(settings, 'SWIRL_DEFAULT_QUERY_LANGUAGE', 'english')
    stopwords = set(stopwords.words(SWIRL_DEFAULT_QUERY_LANGUAGE))
except OSError:
    logger.warning(f"{module_name}: Warning: No stopwords for language: {SWIRL_DEFAULT_QUERY_LANGUAGE}, check SWIRL_DEFAULT_QUERY_LANGUAGE in swirl_server/settings.py")
    logger.warning(f"{module_name}: Warning: Using english stopwords")
    stopwords = set(stopwords.words('english'))

from nltk.stem import PorterStemmer
ps = PorterStemmer()

from nltk.tokenize import sent_tokenize
from nltk.tokenize import word_tokenize
from nltk.tokenize.punkt import PunktToken

def is_punctuation(c):
    if not c:
        return False

    if len(c) > 1:
        return False

    t = PunktToken(c)
    return not t.is_non_punct
