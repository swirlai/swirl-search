from django.conf import settings
import pytest
from django.test import TestCase
from swirl.web_page import PageFetcher, PageFetcherFactory, PageFetcherOptions, DocumentWebPage
import responses
import re

@pytest.fixture
def mock_html():
    return '<!DOCTYPE html> <html lang="en"> <head>     <meta charset="UTF-8">     <meta name="viewport" content="width=device-width, initial-scale=1.0">     <title>Test Page</title>     <style>         body {             font-family: Arial, sans-serif;             text-align: center;             padding: 50px;             background-color: #f4f4f4;         }         h1 {             color: #333;         }         p {             color: #555;         }     </style> </head> <body>     <h1>Welcome to the Test Page</h1>     <p>This is a simple page for testing purposes. Feel free to modify or expand upon it!</p> </body> </html>'


class PostSearchProviderTestCase(TestCase):
    @pytest.fixture(autouse=True)
    def _init_fixtures(self, mock_html):
        self._mock_html = mock_html

    def setUp(self):
        settings.SWIRL_TIMEOUT = 1
        settings.CELERY_TASK_ALWAYS_EAGER = True

    @responses.activate
    def test_pagefetcher_2(self):
        test_url = "http://www.foo.com/test.html"
        responses.add(responses.GET, test_url, json=self._mock_html, status=200)
        p = PageFetcher(test_url)
        page = p.get_page()
        assert page
        text = page.get_text_strip_html()
        assert text
        assert text == '"     Test Page    Welcome to the Test Page This is a simple page for testing purposes. Feel free to modify or expand upon it!  "'

    @responses.activate
    def test_pagefetcher_1(self):
        test_url = "http://www.foo.com/test.html"
        responses.add(responses.GET, test_url, json=self._mock_html, status=200)
        p = PageFetcher(test_url)
        page = p.get_page()
        assert page
        text = page.get_text_for_query("simple page")
        assert text
        assert text == '" Test Page Welcome to the Test Page This is a simple page for testing purposes. Feel free to modify or expand upon it! "'

    def assert_page_fetch_default_options(self, pf, do_cache):
            """takes into account things that are not in the default becasue they are mandatory"""
            dops = PageFetcherOptions.get_page_fetch_defaults()
            assert pf.get_headers() == dops.get("headers", None)
            assert pf.get_timeout() == dops.get("timeout", None)
            assert pf.do_cache() == do_cache

    def test_page_fetch_factory_options_1(self):

        """
        tests focused on page fetchert
        """
        test_url = "http://www.foo.com/test.html"

        ## basic null/empty/none cases
        assert PageFetcherFactory.alloc_page_fetcher(url=test_url,options=None) is None
        assert PageFetcherFactory.alloc_page_fetcher(url=test_url,options={}) is None
        assert PageFetcherFactory.alloc_page_fetcher(url=test_url,options={
            "cache": ""
        })  is None
        assert PageFetcherFactory.alloc_page_fetcher(url=test_url,options={
            "cache": "xxx"
        })  is None

        ## Page fetch w/ no diffbot
        do_cache = "true"
        pf = PageFetcherFactory.alloc_page_fetcher(url=test_url,options={"cache": do_cache})
        assert isinstance(pf,PageFetcher)
        self.assert_page_fetch_default_options(pf, do_cache=True)

        do_cache = "false"
        pf = PageFetcherFactory.alloc_page_fetcher(url=test_url,options={"cache": do_cache})
        assert isinstance(pf,PageFetcher)
        self.assert_page_fetch_default_options(pf, do_cache=False)

        ## set values in the headers
        test_user_agent = 'Testbot/1.0 (+http://swirlaiconnect.com)'
        test_header_val = "bar-value"
        pf = PageFetcherFactory.alloc_page_fetcher(url=test_url,
                                                   options= {
                                                        "cache": "false",
                                                        "headers":{'User-Agent': test_user_agent,
                                                                   'foo-header': test_header_val}
                                                   }
                                                )
        assert isinstance(pf,PageFetcher)
        assert (ah := pf.get_headers())
        assert ah.get('User-Agent', None) == test_user_agent
        assert ah.get('foo-header', None) == test_header_val

        ## rm the user agent by config options
        test_user_agent = ''
        pf = PageFetcherFactory.alloc_page_fetcher(url=test_url,
                                                   options= {
                                                        "cache": "false",
                                                        "headers":{'User-Agent': test_user_agent}
                                                   }
                                                )
        assert isinstance(pf,PageFetcher)
        assert pf.get_headers() == {}

        ## set timeout
        test_timeout = 20
        pf = PageFetcherFactory.alloc_page_fetcher(url=test_url,
                                                   options= {
                                                        "cache": "false",
                                                        "timeout":test_timeout
                                                   }
                                                )
        assert isinstance(pf,PageFetcher)
        assert pf.get_timeout() == test_timeout

        ## set all
        test_timeout = 22
        test_user_agent = 'Testbot/1.0 (+http://swirlaiconnect.com)'
        test_header_val = 'bar-value'
        pf = PageFetcherFactory.alloc_page_fetcher(url=test_url,
                                                   options= {
                                                        "cache": "false",
                                                        "headers":{'User-Agent': test_user_agent,
                                                                   'foo-header': test_header_val},
                                                        "timeout":test_timeout
                                                   }
                                                )
        assert isinstance(pf,PageFetcher)
        assert pf.get_timeout() == test_timeout
        assert ah.get('User-Agent', None) == test_user_agent
        assert ah.get('foo-header', None) == test_header_val
