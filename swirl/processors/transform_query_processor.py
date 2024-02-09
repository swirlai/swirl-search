'''
@author:     Nicodemus
@contact:    dave@swirl.today
'''

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from abc import ABCMeta, abstractmethod

import csv
import io
import re

from swirl.processors.processor import QueryProcessor
from swirl.processors.utils import clean_string
from swirl.processors.utils import str_tok_get_prefixes
from swirl.nltk import word_tokenize

#############################################
#############################################
class TransformQueryProcessorFactory():

    @staticmethod
    def alloc_query_transform(query_string, name, qxf_type, config):
        """
        Get the query transformer based on type
        TODO : Cache?
        """
        ret = None
        if qxf_type == "rewrite":
            ret =  RewriteQueryProcessor(query_string, name,  config)
        elif qxf_type == "synonym":
            ret =  SynonymQueryProcessor(query_string, name, config)
        elif qxf_type == "bag":
            ret =  SynonymBagQueryProcessor(query_string, name,  config)
        else:
            raise ValueError("Invalid Query Transform Processor type")
        ret.parse_config()
        return ret

class _ConfigReplacePattern ():
    def __init__(self, pat, rep):
        self.pattern = pat
        self.replace = rep
    def __str__(self):
        return f"<<{self.pattern}>> -> <<{self.replace}>>"


class AbstractTransformQueryProcessor(QueryProcessor, metaclass=ABCMeta):
    """
    Holder for Query shared transform fuctionality and interfaces
    """

    def __init__(self,  query_string, name, config):
        super(AbstractTransformQueryProcessor,self).__init__(query_string=query_string, query_mappings={}, tags=[])
        self._name = name
        self._config = config
        self._config_parsed = False
        self.replace_patterns = []
        self.replace_index = {}

    def _config_start(self):
        """Prepare to read the config as a csv"""
        try:
            csv_file = io.StringIO(self._config)
            csv_reader = csv.reader(csv_file)
        except csv.Error as e:
            logger.error(f'Exception {e} while parsing CSV ')
            return None
        return csv_reader

    def _config_next_line(self, csv_reader):
        """
        Get the next line, skip comment lines, returns None if there are no more lines
        or if an exception is thrown.
        """
        try:
            if not csv_reader:
                return None
            while (ret := next(csv_reader, None)) is not None:
                # skip comments and empty lines
                if not ret or len(ret) == 0 or len(ret[0]) == 0 or ret[0][0] == '#':
                    continue
                break
            return ret
        except StopIteration:
            return None
        except csv.Error as e:
            logger.error(f'Exception {e} while parsing CSV ')
            return None

    def _get_synonyms(self, word):
        if not self.replace_index:
            return []
        entry = self.replace_index.get(word, None)
        if not entry:
            return []
        return entry.replace

    def parse_config(self):
        if self._config_parsed:
            return
        logger.debug(f'parse config {self.type}')
        conf_lines = self._config_start()
        if not conf_lines:
            return
        n = 0
        while (cline := self._config_next_line(conf_lines)) is not None:
            n = n + 1
            self._parse_cline(cline,n)
        self._config_parsed = True

    def _cline_is_valid(self, cline, nth, min_num_cols):
        if not cline:
            return False # not valid, not not an error
        if min_num_cols and len(cline) < min_num_cols:
            logger.warning(f'ignoring malformed line {nth} in {self._name}')
            return False
        return True

    def _clean_word_tok_quote_artificats(self, q_new, q_org):
        if not '"' in q_org:
            return q_new
        q_new = q_new.replace('``','"')
        q_new = q_new.replace("''",'"')
        return q_new

    def _normalize_word(self, word):
        """ Strip and normalize whitespace """
        tmp_toks = word.strip().split()
        return ' '.join(tmp_toks)

    @abstractmethod
    def get_replace_patterns(self):
        """return the replace patterns"""
        pass

    @abstractmethod
    def _parse_cline(self, cline, nth):
        """ parse line and add to replace patterns """
        pass


class RewriteQueryProcessor(AbstractTransformQueryProcessor):

    """
    parse rules and based on them replace patterns in the
    input string w/ the appropriate substitution or nothing, if that is indicated
    """

    type = 'RewriteQueryProcessor'

    def get_replace_patterns(self):
        return self.replace_patterns

    def _parse_cline(self, cline, nth):
        """ parse line and add to replace patterns """
        if not super(RewriteQueryProcessor, self)._cline_is_valid(cline, nth, 1):
            return

        if len(cline) == 1:
            pats = r'\b'+cline[0]+r'\b\s?'
            repl = ''
        else:
            pats = cline[0]
            repl = cline[1]
        for p in pats.split(';'):
            self.replace_patterns.append(_ConfigReplacePattern(p.strip(), [repl.strip()]))

    def process(self):
        super(RewriteQueryProcessor, self).parse_config()
        ret = clean_string(self.query_string).strip()
        if not ret:
            return ret
        logger.debug(f'{self.type} {self._name} processing query')
        for rp in self.replace_patterns:
            ret = re.sub(rp.pattern, rp.replace[0], ret)
        return ret

#############################################

class SynonymQueryProcessor(AbstractTransformQueryProcessor):

    type = 'SynonymQueryProcessor'

    def get_replace_patterns(self):
        return list(self.replace_index.values())

    def _parse_cline(self, cline, nth):
        if not super(SynonymQueryProcessor, self)._cline_is_valid(cline, nth, 2):
            return
        word = cline[0].strip()

        # tokenizer the matching word(s)
        normal_word = super(SynonymQueryProcessor, self)._normalize_word(word)
        repl = cline [1].strip()
        entry = self.replace_index.get(word, None)
        if not entry:
            self.replace_index[word] = (_ConfigReplacePattern(normal_word, [repl]))
        else:
            entry.replace.append(repl)

    def process(self):
        """
        limits: does not handle overlapping rules, only the longest rule wins.
        If you have two rules A B => x and B = y, the Query A B will return
        A B OR x. The query B will return B OR y
        """
        super(SynonymQueryProcessor,self).parse_config()
        clean_query = clean_string(self.query_string).strip()
        if not clean_query:
            return clean_query
        q_toks = word_tokenize(self.query_string)
        q_len = len(q_toks)
        prfx_strs = str_tok_get_prefixes(q_toks) # all prefix strings
        ret_toks = []
        # for all of the prefix strings, look for a match in the synonm lib
        n_q_toks_processed = 0
        index_p_str = 0
        while n_q_toks_processed < q_len:
            p_str = prfx_strs[index_p_str]
            p_str_len = len(p_str.split())
            syns = super(SynonymQueryProcessor,self)._get_synonyms(p_str)
            if syns:
                ret_toks.append('(' + ' OR '.join([p_str] + list(syns)) + ')')
                n_q_toks_processed = n_q_toks_processed + p_str_len
            elif p_str_len == 1:
                ret_toks.append(p_str)
                n_q_toks_processed = n_q_toks_processed + 1
            index_p_str = index_p_str + 1 # next prefix string
        return super(SynonymQueryProcessor,self)._clean_word_tok_quote_artificats(' '.join(ret_toks), clean_query)


#############################################

class SynonymBagQueryProcessor(SynonymQueryProcessor):

    type = 'SynonymBagQueryProcessor'

    def get_replace_patterns(self):
        return list(self.replace_index.values())

    def _parse_cline(self, cline, nth):
        if not super(SynonymBagQueryProcessor, self)._cline_is_valid(cline, nth, None):
            return
        for word in cline:
            normal_word = super(SynonymBagQueryProcessor, self)._normalize_word(word)
            # noramlize and add to the config replace pattern
            word_buf = [bw for w in cline if (bw := super(SynonymBagQueryProcessor,self)._normalize_word(w)) != normal_word ]
            self.replace_index[normal_word] = _ConfigReplacePattern(normal_word, word_buf)
