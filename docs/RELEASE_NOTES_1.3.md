![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# SWIRL SEARCH 1.3

This version incorporates additional usability feedback plus improvements to performance, configurability and 
result format.
​
## Changes

:small_blue_diamond: Mixers now support a single-provider filter.

For example:

[http://localhost:8000/swirl/results/?search_id=1&provider=1](http://localhost:8000/swirl/results/?search_id=1&provider=1)

This allows front-ends to easily drill-down into a single source. Note that unless the SearchProvider is configured to request more than the default of 10 results, only one page of results will be available. 

Paging beyond the initial result set is not currently supported by SWIRL, but could be in a future release.

<br/>

:small_blue_diamond: Timings are now reported for each SearchProvider, and each search overall, in seconds. 

```
    "info": {
        "Enterprise Search (web/Google PSE)": {
            "found": 10,
            "retrieved": 10,
            "filter_url": "http://localhost:8000/swirl/results/?search_id=522&provider=3",
            "query_to_provider": "https://www.googleapis.com/customsearch/v1?cx=0c38029ddd002c006&key=AIzaSyDeB1y9l6OQW0dhVdZ9X_Xb2br_SK1K8YM&q=strategic+consulting",
            "result_processor": "GenericResultProcessor",
            "search_time": 2.2
        },
        "results": {
            "retrieved_total": 10,
            "retrieved": 10,
            "federation_time": 5.4
        }
    }
```

The "federation_time" includes: 
* Pre-query processing
* Federation (query processing, response normalization, result processing)
* Post-result processing, including relevancy processing by default

<br/>

:small_blue_diamond: Mappings have been reversed for clarity, and are now in the form swirl_key = source_mapping

All included SearchProviders have been updated. To migrate an existing SearchProvider, make the right-most key the left-most.

For example, change:

```
        "query_mappings": "cx=0c38029ddd002c006,sort=date=DATE_SORT,start=RESULT_INDEX=PAGE",
        "response_mappings": "searchInformation.totalResults=FOUND,queries.request[0].count=RETRIEVED,items=RESULTS",
        "result_mappings": "link=url,htmlSnippet=body,cacheId,NO_PAYLOAD",
```

to:

```
    "query_mappings": "cx=0c38029ddd002c006,DATE_SORT=sort=date,PAGE=start=RESULT_INDEX",
    "response_mappings": "FOUND=searchInformation.totalResults,RETRIEVED=queries.request[0].count,RESULTS=items",
    "result_mappings": "url=link,body=htmlSnippet,cacheId,NO_PAYLOAD",
```

<br/>

:small_blue_diamond: Many hard-wired items are now in the swirl_server/settings.py file:

| Configuration item | Explanation | Example |
| ------------------ | ----------- | ------- |
| HOSTNAME | Used to construct SWIRL URLs; as of SWIRL 1.3 this is the first ALLOWED_HOST entry | HOSTNAME = ALLOWED_HOSTS[0]\nHOSTNAME = 'myserver' |
| SWIRL_BANNER | The string to display in SWIRL data structures; please don't remove it (but you don't have to display it) | |
| SWIRL_TIMEOUT | The number of seconds to wait until declaring federation complete, and terminating any connectors that haven't responded | SWIRL_TIMEOUT = 10 |
| SWIRL_Q_WAIT | The number of seconds to wait before redirecting to the result mixer after using the [q= parameter](2.-User-Guide.md#creating-a-search-object-with-the-q-url-parameter) | SWIRL_Q_WAIT = 7 |
| SWIRL_RERUN_WAIT | The number of seconds to wait before redirecting to the result mixer when [rerunning a search](2.-User-Guide.md#re-starting-re-running--re-scoring) | SWIRL_Q_WAIT = 8 |
| SWIRL_RESCORE_WAIT | The number of seconds to wait before redirecting to the result mixer when [rescoring a search](2.-User-Guide.md#re-starting-re-running--re-scoring) | SWIRL_Q_WAIT = 3 |

Note that the configuration names must be UPPER_CASE per the [django settings convention](https://docs.djangoproject.com/en/4.1/topics/settings/).

<br/>

:small_blue_diamond: The relevancy explain block is now suppressed by default

To view the explain for any mixed result set, add explain=True to the mixer URL. For example:

[http://localhost:8000/swirl/results/?search_id=1&explain=True](http://localhost:8000/swirl/results/?search_id=1&explain=True)

<br/>

## Known Issues

:small_blue_diamond: [Creating searches from a browser with q=](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#creating-a-search-object-with-the-q-url-parameter) can sometimes create two Search objects. 

This is because of browser prefetch. [Turn off Chrome prefetch](https://www.technipages.com/google-chrome-prefetch). [Turn off Safari prefetch](https://stackoverflow.com/questions/29214246/how-to-turn-off-safaris-prefetch-feature)

Please [report any issues](https://github.com/sidprobstein/swirl-search/issues/) with this or the [rerun function](USER_GUIDE.md#re-starting-re-running--re-trying-a-search).

<br/>

:small_blue_diamond: The [Django admin form for managing Result objects](http://localhost:8000/admin/swirl/result/) throws a 500 error. P2.

<br/>

:small_blue_diamond: Watch out for log files in logs/*.log. They'll need periodic purging. Rollover is planned for a future release.

<br/>

# Documentation

* [Quick Start](https://github.com/sidprobstein/swirl-search/wiki/1.-Quick-Start)
* [User Guide](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide)

<br/>

# Support

:small_blue_diamond: [Create an Issue](https://github.com/sidprobstein/swirl-search/issues) if something doesn't work, isn't clear, or should be documented - we'd love to hear from you!

:small_blue_diamond: Paid support and consulting are available... [contact SWIRL](mailto:swirl@probstein.com) for more information.
