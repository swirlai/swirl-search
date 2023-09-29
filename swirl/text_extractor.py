import re
from abc import ABCMeta, abstractmethod
from tika import parser
from django.conf import settings
from swirl.utils import generate_unique_id, remove_file, make_dir_if_not_exist
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

class TextExtractor (metaclass=ABCMeta):
    def __init__(self, content, source_id=""):
        self._content = content
        self._source_id = source_id

    @abstractmethod
    def extract_text(self):
        """ get the resposne URL"""
        pass

class TikaTextExtractor(TextExtractor):
    """
    requires the tika server to be running, otherwise, this will not work.
    """
    def _clean_tika(self, input_string):
        # Remove extra spaces, newlines, and tabs using regular expressions
        cleaned_string = re.sub(r'\s+', ' ', input_string.strip())
        return cleaned_string

    def extract_metadata(self):
        if not self._parsed:
            self.extract_text()
        return  self._parsed['metadata']

    def extract_text(self):
        filename = None
        try:
            make_dir_if_not_exist(settings.SWIRL_WRITE_PATH)
            file_content = self._content
            # Write content to a temporary file
            filename = f'{settings.SWIRL_WRITE_PATH}/tk_{generate_unique_id()}.tmp'
            logger.debug(f'attempting write of content of {self._source_id} to {filename}')
            with open(filename, 'wb') as f:
                f.write(file_content)
            # Use Apache Tika to parse the file
            logger.debug(f'about to attempt parse')
            self._parsed = parser.from_file(filename)
            return self._clean_tika(str(self._parsed['content']))
        except Exception as err:
            logger.error(f'{err} : while fetching and parsing')
            return None
        finally:
            remove_file(filename=filename)

class TextExtractorFactory():
    @staticmethod
    def alloc_text_extactor(content, source_id):
        return TikaTextExtractor(content,source_id=source_id)
