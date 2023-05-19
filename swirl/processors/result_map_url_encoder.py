import re
from urllib.parse import quote

class ResultMapUrlEncoder():

    __RESULT_MAP_URL_ENCODE_METHOD_PAT = r'sw_urlencode\((.*)\)'

    def __init__(self, key):
        self.__key = key
        self.__found_encode_directive = None

    def __clean_key(self):
        """Extract directive if it exists and remove it from key"""
        if self.__key == None:
            return None
        self.__found_encode_directive = re.search(ResultMapUrlEncoder.__RESULT_MAP_URL_ENCODE_METHOD_PAT, self.__key)
        if self.__found_encode_directive:
            self.__key = self.__found_encode_directive.group(1)
        return self.__key

    def __optional_encode_value(self, v):
        """encode if needed"""
        if self.__found_encode_directive:
            return quote(str(v),safe='')
        return v

    def get_key(self):
        """
        return the key w/ any prcessing direcrives removed or the original
        key if there were no directives
        """
        return self.__clean_key()

    def get_value(self, v):
        """
        return the value, either as is, or URL encoded if directed
        """
        return self.__optional_encode_value(v)
