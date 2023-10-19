'''
@author:     Spears
@contact:    erik@swirl.today
'''
import re
from decimal import Decimal, getcontext

# Ensure the precision is set sufficiently high outside the class
getcontext().prec = 10

# Ensure the precision is set sufficiently high outside the class
getcontext().prec = 10

class ResultMapBtcConverter():

    __RESULT_MAP_BTC_CONVERT_METHOD_PAT = r'sw_btcconvert\((.*)\)'

    def __init__(self, key):
        self.__key = key
        self.__found_convert_directive = None

    def __clean_key(self):
        """Extract directive if it exists and remove it from key"""
        if self.__key is None:
            return None
        self.__found_convert_directive = re.search(ResultMapBtcConverter.__RESULT_MAP_BTC_CONVERT_METHOD_PAT, self.__key)
        if self.__found_convert_directive:
            self.__key = self.__found_convert_directive.group(1)
        return self.__key

    def __optional_convert_value(self, v):
        """Convert if needed."""
        if self.__found_convert_directive:
            if not v.isdigit():
                raise ValueError("Invalid input. The input should be a numeric string.")
            btc_decimal = Decimal(v) / Decimal(100_000_000)
            return str(btc_decimal)
        return v

    def get_key(self):
        """
        Return the key with any processing directives removed or the original
        key if there were no directives.
        """
        return self.__clean_key()

    def get_value(self, v):
        """
        Return the value, either as is, or converted if directed.
        """
        return self.__optional_convert_value(v)
