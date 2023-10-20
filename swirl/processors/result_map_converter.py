import re
from decimal import Decimal, getcontext
from urllib.parse import quote

# Ensure the precision is set sufficiently high outside the class
getcontext().prec = 10

class ResultMapConverter():

    __BTC_CONVERT_METHOD_PAT = r'sw_btcconvert\((.*)\)'
    __URL_ENCODE_METHOD_PAT = r'sw_urlencode\((.*)\)'

    def __init__(self, key):
        self.__key = key
        self.__found_directive = None

    def __clean_key(self):
        """Extract directive if it exists and remove it from key"""
        if self.__key is None:
            return None
        self.__found_directive = re.search(ResultMapConverter.__BTC_CONVERT_METHOD_PAT, self.__key) or \
                                re.search(ResultMapConverter.__URL_ENCODE_METHOD_PAT, self.__key)
        if self.__found_directive:
            self.__key = self.__found_directive.group(1)
        return self.__key

    def __optional_convert_value(self, v):
        """Convert if needed (Bitcoin or URL encoding)."""
        if self.__found_directive:
            if self.__found_directive.group(0).startswith('sw_btcconvert'):
                if not v.isdigit():
                    raise ValueError("Invalid input. The input should be a numeric string.")
                btc_decimal = Decimal(v) / Decimal(100_000_000)
                return str(btc_decimal)
            elif self.__found_directive.group(0).startswith('sw_urlencode'):
                return quote(str(v), safe='')
        return v

    def get_key(self):
        """
        Return the key with any processing directives removed or the original
        key if there were no directives.
        """
        return self.__clean_key()

    def get_value(self, v):
        """
        Return the value, either as is, or converted if directed (Bitcoin or URL encoding).
        """
        return self.__optional_convert_value(str(v))
