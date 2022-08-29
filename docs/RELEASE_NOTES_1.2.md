![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# SWIRL SEARCH 1.2

## Changes

:small_blue_diamond: New Object Oriented Connectors!

The Connectors have been renamed for clarity:

* Elastic
* RequestsGet
* Sqlite3

The only change required to use these connectors is to change the "Connector" setting in the [SearchProvider](../SearchProviders/current.json). All of the included providers have been updated.

:small_blue_diamond: No longer boosting single term queries

![SWIRL Relvancy Ranked Results featuring SOLR, NLResearch.com](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/swirl_results_solr_nlresearch.png) 

<br/>

## Known Issues

:small_blue_diamond: [Creating searches from a browser with q=](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#creating-a-search-object-with-a-url-and-qquery_string) can sometimes create two Search objects. 

This is because of browser prefetch. [Turn off Chrome prefetch](https://www.technipages.com/google-chrome-prefetch). [Turn off Safari prefetch](https://stackoverflow.com/questions/29214246/how-to-turn-off-safaris-prefetch-feature)

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
