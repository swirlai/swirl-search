'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import logging as logger

from django.conf import settings

from nltk.corpus import stopwords

module_name = 'nltk.py'

try:
    stopwords = set(stopwords.words(settings.SWIRL_DEFAULT_QUERY_LANGUAGE))
except OSError:
    logger.warning(f"{module_name}: Warning: No stopwords for language: {settings.SWIRL_DEFAULT_QUERY_LANGUAGE}, check SWIRL_DEFAULT_QUERY_LANGUAGE in swirl_server/settings.py")
    logger.warning(f"{module_name}: Warning: Using english stopwords")
    stopwords = set(stopwords.words('english'))

from nltk.stem import PorterStemmer
ps = PorterStemmer()

from nltk.tokenize import sent_tokenize
