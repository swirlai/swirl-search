![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# SWIRL SEARCH 1.4

This version expands usability for multiple topics by adding default providers plus tagging of searchproviders, search and result objects. Tags can be specified freely in combination with provider name and/or id. More tag-based enhancements are coming soon.

## Additions

:small_blue_diamond: New SearchProvider properties "Default" and "Tags"

SearchProviders can now be organized using Tags - json lists that can hold any monicker desired for one or more providers. Tags can be specified in search objects using the searchprovider_list, and freely combined with provider names or IDs. If no searchprovider_list is specified, only providers with Default = True will be run. 

This allows you to set up a set of general use providers as 'default' and ones for specific topics under various tags. For example:

SearchProvider:

```
{
        "active": true,
        "default": false,
        "name": "Maritime News (web/Google PSE)",
        "connector": "RequestsGet",
        ...etc...
        "tags": [
            "maritime"
        ]
    },
```

Search:

```
{
    "query_string": "strategic consulting",
    "searchprovider_list": [ 6, 12, "maritime" ]
}
```

Read more: [Organizing SearchProviders with Active, Default and Tags](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#organizing-searchproviders-with-active-default-and-tags)

:small_blue_diamond: New PostGresql Connector

The funding database example has also been updated to run with PostGresql.

```
{
    "name": "Company Funding Records (local/sqlite3)",
    "connector": "PostGresql",
    "url": "host:port:database:username:password",
    "query_template": "select {fields} from {table} where {field1} ilike '%{query_string}%' or {field2} ilike '%{query_string}%';",
    "query_mappings": "fields=*,sort_by_date=fundedDate,table=funding,field1=city,field2=company",
    "result_mappings": "title='{company} series {round}',body='{city} {fundeddate}: {company} raised usd ${raisedamt}\nThe company is headquartered in {city} and employs {numemps}',date_published=fundeddate,NO_PAYLOAD"
}
```

Read more: [PostGresql Connector](https://github.com/sidprobstein/swirl-search/wiki/4.-Object-Reference#postgresql)

## Changes

:small_blue_diamond: New property SWIRL_EXPLAIN in [swirl_server/settings.py](../swirl_server/settings.py) now controls the default Relevancy explain setting. 

```
SWIRL_EXPLAIN = True
```

The default is True.

:small_blue_diamond: Relevancy has been improved, particularly for one-term queries, and the all-terms boost has been retired.

<br/>

## Known Issues

:small_blue_diamond: [Creating searches from a browser with q=](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#creating-a-search-object-with-the-q-url-parameter) can sometimes create two Search objects. 

This is because of browser prefetch. [Turn off Chrome prefetch](https://www.technipages.com/google-chrome-prefetch). [Turn off Safari prefetch](https://stackoverflow.com/questions/29214246/how-to-turn-off-safaris-prefetch-feature)

Please [report any issues](https://github.com/sidprobstein/swirl-search/issues/) with this to [support](#support).

<br/>

:small_blue_diamond: Watch out for log files in logs/*.log. They'll need periodic purging. Rollover is planned for a future release.

<br/>

# Documentation

* [Quick Start](https://github.com/sidprobstein/swirl-search/wiki/1.-Quick-Start)
* [User Guide](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide)

<br/>

# Support

:small_blue_diamond: [Create an Issue](https://github.com/sidprobstein/swirl-search/issues) if something doesn't work, isn't clear, or should be documented - we'd love to hear from you!

:small_blue_diamond: Paid support and consulting are available... [contact SWIRL](mailto:support@swirl.today) for more information.
