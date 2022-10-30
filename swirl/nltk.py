'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.0
'''

from nltk.corpus import stopwords

# TO DO: add lang detection and others
stopwords_en = set(stopwords.words('english'))

from nltk.stem import PorterStemmer

ps = PorterStemmer()

from nltk.tokenize import word_tokenize, sent_tokenize
