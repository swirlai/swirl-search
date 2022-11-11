'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
'''

from nltk.corpus import stopwords
stopwords_en = set(stopwords.words('english'))

from nltk.stem import PorterStemmer
ps = PorterStemmer()

from nltk.tokenize import word_tokenize, sent_tokenize
