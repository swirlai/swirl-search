from abc import ABCMeta, abstractmethod

import requests
import json
import copy

from http import HTTPStatus
from urllib.parse import urlparse
from urllib3.exceptions import NewConnectionError
from readability import Document
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse

# TO DO: is this correct? This is usually used in celery
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

# Page fetcher constants
WEB_PAGE_FETCHER_DEFAULT_TIMEOUT_SECONDS=10
WEB_PAGE_FETCHER_DEFAULT_DO_CACHE="false"
WEB_PAGE_UNKNOWN_DOC_TYPE="unknown"

# Diffbot constants
DIFFBOT_DEFAULT_PARSE_JS = "true"
DIFFBOT_DEFAULT_XE = "analyze"
DIFFBOT_DEFAULT_PREFETCH= "false"
DIFFBOT_GET_HEADERS={"accept": "application/json"}
DIFFBOT_POST_HEADERS={'Content-Type': 'text/html'}
DIFFBOT_DEFAULT_OPTIONS = {
      "extract_entity":DIFFBOT_DEFAULT_XE,
      "parse_javascript": DIFFBOT_DEFAULT_PARSE_JS,
      "prefetch_data":DIFFBOT_DEFAULT_PREFETCH
}

class WebPage (metaclass=ABCMeta):
    def __init__(self, response):
        self._response = response
        self._document_type = None

    @abstractmethod
    def get_response_url(self):
        """ get the resposne URL"""
        pass
    @abstractmethod
    def get_content(self):
        """byte content of page"""
        pass
    @abstractmethod
    def get_text(self):
        """content as a text string"""
        pass
    @abstractmethod
    def get_json(self):
        """content as a json string"""
        pass

    def get_document_type(self):
        """a highlevel document type, examples : list, jobposting, article, etc...."""
        return self._document_type

    def get_text_strip_html(self):
        return self.html_to_text(self.get_text(), skip_summary=True).strip()

    def html_to_text(self, html, skip_summary=False):
        ret_text = ""
        if not html : return ret_text
        try:
            # Assuming 'page_text' contains the raw HTML content
            if skip_summary:
                cleaned_html = html
            else:
                item_content = Document(html)
                # Get the cleaned and readable version of the HTML
                cleaned_html = item_content.summary()

            # Use BeautifulSoup to extract text from the cleaned HTML
            soup = BeautifulSoup(cleaned_html, 'html.parser')
            ret_text = soup.get_text()
        except Exception as err:
            logger.erro(f"{self} convertin html to text")
        finally:
            return ret_text

class DocumentWebPage (WebPage):
    def __str__(self):
        return f"{self.__class__.__name__}"

    def __init__(self, response):
        super().__init__(response)

    def get_response_url(self):
        if not self._response:
            return None
        return self._response.url

    def get_content(self):
        return self._response.content

    def get_text(self):
        return self._response.text

    def get_json(self):
        return self._response.json

    def get_text_for_query(self, query=''):
        ret_text = ""
        try:
            from swirl.processors.utils import clean_string_keep_punct
            page_text = self.get_text()
            if not page_text:
                logger.warning(f"{self} no text in page {self.get_response_url()} and query {query} json : {json.dumps(self.get_json(),indent=2)}")
                return ret_text
            if content_summary := super().html_to_text(page_text):
                ret_text = clean_string_keep_punct(content_summary)
            else:
                logger.warning(f"Retrieval failed: {self._response.url}")
        except Exception as err:
            logger.err(f'exception {err} getting text from page')
        finally:
            return ret_text


class PageFetcher (metaclass=ABCMeta):

    def __str__(self):
        return f"{self.__class__.__name__}"

    def __init__(self, url, headers=None, timeout=WEB_PAGE_FETCHER_DEFAULT_TIMEOUT_SECONDS,
                 do_cache=WEB_PAGE_FETCHER_DEFAULT_DO_CACHE):
        self._url = url
        self._headers = headers
        self._timeout = timeout
        if do_cache.lower() == "true":
            self._do_cache = True
        else:
            self._do_cache = False

        self._http_status = None

    def get_headers(self):
        return self._headers

    def get_timeout(self):
        return self._timeout

    def do_cache(self):
        return self._do_cache

    def get_page_document_type(self):
        "Type of document this fetcher returns"
        return DocumentWebPage

    def get_http_status(self):
        "HTTP status of last HTTP request"
        return self._http_status

    def _get_page(self, document_type):
        """
        returns a web page on success and None on failure. Last HTTP status can be retrieved
        through access methods.
        """
        try:
            response = requests.get(self._url, headers=self._headers, timeout=self._timeout)
            self._http_status = None
            if response.status_code != HTTPStatus.OK:
                logger.error(f"GET Got unexpected status code: {response.status_code} : {self._url} {self._timeout} {self._headers}")
                return None
            return document_type(response=response)
        except (TimeoutError, NewConnectionError, ConnectionError, requests.exceptions.InvalidURL, Exception) as err:
            logger.error(f"{err}")
            return None

    def get_page(self):
        return self._get_page(self.get_page_document_type())

    def post_page(self, data):
        """
        returns a web page on success and None on failure. Last HTTP status can be retrieved
        through access methods.
        """
        try:
            if self._headers.get('Content-Type') == 'application/json':
                response = requests.post(self._url, json=data, headers=self._headers, timeout=self._timeout)
            else:
                response = requests.post(self._url, data=data, headers=self._headers, timeout=self._timeout)
        except (TimeoutError, NewConnectionError, ConnectionError, requests.exceptions.InvalidURL) as err:
            logger.error(f"{err} while posting page")
            return None
        except Exception as err:
            logger.error(f"unexpected {err} while posting page")

        self._http_status = None
        if not response.status_code in ( HTTPStatus.OK, HTTPStatus.CREATED, HTTPStatus.ACCEPTED, HTTPStatus.NO_CONTENT, HTTPStatus.RESET_CONTENT):
            logger.error(f"POST Got unexpected status code: {response.status_code} : {self._url} {self._timeout} {self._headers}")
            return None

        return self.get_page_document_type()(response=response)


class PageFetcherOptions:
    def __init__(self, options={},url=""):
        # merge the passed in options

        # merge the headers, only removing a header if the passed in is set to
        # empty string.
        if "headers" in options:
            options["headers"] = self._merge_options(options["headers"],
                                    PageFetcherOptions.get_page_fetch_defaults()["headers"])

        # merge passed in WITH passed in headers correct, and prefering passed in
        # with defaults
        self._options = PageFetcherOptions._merge_options(input=options, defaults=PageFetcherOptions.get_page_fetch_defaults())
        self._url = url

    @staticmethod
    def get_page_fetch_defaults():
        return  {
            "headers":{'User-Agent': 'Swirlbot/1.0 (+http://swirlaiconnect.com)'},
            "timeout": WEB_PAGE_FETCHER_DEFAULT_TIMEOUT_SECONDS,
        }

    @staticmethod
    def _merge_options(input, defaults):
        """
        Merget the input values with defaults, if the input
        contains a null string for a default, then remove the
        default from the resulting config
        """
        merged = {**defaults, **input}
        # Remove keys with empty string values
        merged = {k: v for k, v in merged.items() if v != ""}
        return merged

    def is_enabled(self):
        return (self._options and "cache" in self._options and
                (self._options.get("cache", "").lower() in ("true","false") )
        )

    def do_cache(self):
        return self._options.get("cache")

    def is_pagefetch(self):
        return  True

    def is_fallback_fetch(self):
        return False

    def get_page_fetch_headers(self):
        return self._options.get("headers",{})

    def get_page_fetch_to(self):
        if self._url:
            parsed_url = urlparse(self._url)
            domain = parsed_url.netloc
            if domain in self._options:
                return self._options.get(domain).get("timeout", None)
        return self._options.get("timeout", None) # Note, if they REALLY set it to nothing, we honor it

class PageFetcherFactory():

    @staticmethod
    def alloc_page_fetcher(url, options):
        if options is None: return None

        pfo = PageFetcherOptions(options=options,url=url)

        if not pfo.is_enabled():
            logger.warning(f"page fetcher requested, but options are not enabled <<{options}>>")
            return None

        if pfo.is_pagefetch():
            logger.debug(f"{PageFetcherFactory.__name__} : Page fetcher alloacted")
            return PageFetcher(url=url, headers=pfo.get_page_fetch_headers(), timeout=pfo.get_page_fetch_to(),
                               do_cache=pfo.do_cache())

        logger.warning("No page fetcher selected but fteched is enabled")
        return None
