![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# SWIRL SEARCH 1.1

## Additions

:small_blue_diamond: New SearchProvider for Apache Solr - tested against 8.1

:small_blue_diamond: New SearchProvider for Northern Light's NLResearch.com service - subscription required

![SWIRL Relvancy Ranked Results featuring SOLR, NLResearch.com](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/swirl_results_solr_nlresearch.png) 

<br/>

:small_blue_diamond: New Date Sort Mixer omits documents with unknown date_published

![SWIRL Date Sorted Results featuring NLResearch.com](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/swirl_results_date_mixer.png) 

<br/>

:small_blue_diamond: New SearchProvider for newsdata.io service - subscription required

![SWIRL Results featuring Newsdata.io](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/swirl_results_newsdata_io.png)

<br/>

## Changes

:small_blue_diamond: Revised [requests_get connector](../swirl/connectors/requests_get.py) now supports most any json response by configuration

:small_blue_diamond: [Google PSE SearchProvider](../SearchProviders/google_pse.json) revised to use requests_get

```
"query_mappings": "cx=some-google-pse-id,sort=date=DATE_SORT,start=RESULT_INDEX=PAGE",
"result_mappings": "link=url,htmlSnippet=body,cacheId,NO_PAYLOAD,searchInformation.totalResults=FOUND,queries.request[0].count=RETRIEVED,items=RESULTS"
```

:small_blue_diamond: Former Google opensearch connector retired

:small_blue_diamond: There are new [query mappings DATE_SORT, RELEVANCY_SORT and PAGE](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#query-mappings), and new [result mappings FOUND, RETRIEVED, RESULTS and RESULT](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#result-mappings) now available for the requests_get connetor

:small_blue_diamond: Updated [Round Robin and Stack mixers](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#mixers) now use relevancy as primary sort

:small_blue_diamond: All mixed results now include swirl_rank, swirl_score, retrieved_total and links to rescore/re-run searches

## Notes

:small_blue_diamond: New SearchProvider for [Apache SOLR](https://solr.apache.org/) has been tested against [8.1.1](https://solr.apache.org/downloads.html). 

Here's the [sample SearchProvider](../SearchProviders/solr_with_auth.json):

```
{
    "name": "techproducts (local/solr)",
    "connector": "requests_get",
    "url": "http://localhost:8983/solr/{collection}/select?wt=json",
    "query_template": "{url}&q={query_string}",
    "query_mappings": "collection=techproducts,start=RESULT_ZERO_INDEX=PAGE",
    "result_mappings": "name=title,response.numFound=FOUND,response.docs=RESULTS",
    "credentials": "HTTPBasicAuth('solr-username','solr-password')"
}
```

<br/>

:small_blue_diamond: New SearchProvider for [NLResearch.com](https://www.nlresearch.com/) has been tested live as of July, 2022. Please note that an account is required to use this connector.

Here's the [sample SearchProvider](../SearchProviders/nlresearch.json):

```
{
    "name": "IT News (web/NLResearch.com)",
    "connector": "requests_get",
    "url": "https://nlresearch.com/results.php?datasource=BRECE&language=1&periodDate=-7&resultsPerPage=10&micpr=0&extended=1&output=json",
    "query_template": "{url}&login={login}&password={password}&textQuery={query_string}",
    "query_mappings": "startNumber=RESULT_INDEX=PAGE,sort=2=DATE_SORT",
    "result_mappings": "summary=body,date=date_published,publisher=author,type,source,country,language,NO_PAYLOAD,header.@attributes.total_documents=FOUND,result_list.result=RESULTS,document=RESULT",
    "results_per_query": 10,
    "credentials": "login=nl-username,password=nl-password"
}
```

<br/>

:small_blue_diamond: New SearchProvider for [newsdata.io](https://www.newsdata.io/) has been tested live as of July, 2022. Please note that an account is required to use this connector, and results are always date sorted, descending.

View the [sample SearchProvider](../SearchProviders/newsdata_api.json).

<br/>

## Known Issues

:small_blue_diamond: [Creating searches from a browser with q=](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#creating-a-search-object-with-a-url-and-qquery_string) can sometimes create two Search objects. 

This appears to be because of browser prefetch. [Turn off Chrome prefetch](https://www.technipages.com/google-chrome-prefetch). [Turn off Safari prefetch](https://stackoverflow.com/questions/29214246/how-to-turn-off-safaris-prefetch-feature)

Please [report any issues](https://github.com/sidprobstein/swirl-search/issues/) with this or the [rerun function](USER_GUIDE.md#re-starting-re-running--re-trying-a-search).

<br/>

:small_blue_diamond: The q= search federation timer has been set more aggressively; if you are redirected to a results page and see the message "Results Not Ready Yet", wait a second or two and reload the page or hit the GET button and it should appear.

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
