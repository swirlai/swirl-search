![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# SWIRL SEARCH 1.6

Version 1.6 shifts focus from relevancy to query adaptation with the new AdaptiveQueryProcessor that rewrites NOT or -term queries depending on SearchProvider configuration:

<br/>

![SWIRL NOT query](./images/swirl_NOT_query.png)
![SWIRL NOT query](./images/swirl_aqp_rewrote.png)
![SWIRL NOT query](./images/swirl_km_NOT_practice.png)

Also new: AND, + and OR are passed along to each SearchProvider and ignored by SWIRL SEARCH for relevancy and highlighting purposes.

## PLEASE STAR OUR REPO: [http://swirl.today/](http://swirl.today)

<br/>

## New Features

:small_blue_diamond: The new AdaptiveQueryProcessor rewrites simple NOT and -term queries to the format supported by each SearchProvider, as defined in the query_mappings. 

```
        "query_mappings": "cx=7d473806dcdde5bc6,DATE_SORT=sort=date,PAGE=start=RESULT_INDEX,NOT_CHAR=-",
```

This indicates that the SearchProvider supports only the ```-term``` format. SWIRL rewrites a query like ...

```
elon musk NOT twitter
```

...to...

```
elon musk -twitter
```

This is noted in the Mixed results set under the SearchProvider block:

```
"Mergers & Acquisitions (web/Google PSE)": {
            "query_string_to_provider": "elon musk -twitter",
            "query_to_provider": "https://www.googleapis.com/customsearch/v1?cx=b384c4e79a5394479&key=AIzaSyDeB1y9l6OQW0dhVdZ9X_Xb2br_SK1K8YM&q=elon+musk+-twitter",
            "result_processor": "MappingResultProcessor",
        }
    ...etc...
},
        "search": {
            "query_string": "elon musk NOT twitter",
            "query_string_processed": "elon musk NOT twitter",
        },
```

<br/>

:small_blue_diamond: The MappingResultsProcessor can map multiple result fields to a single SWIRL field using the ```|``` operator:

```
        "result_mappings": "body=content|description...",

```

This configures SWIRL to populate the ```body``` result field with the ```content``` and/or ```description``` if populated. If both are populated, the second ```description``` field is placed in the payload for clarity.

![SWIRL Multi-Mapping of Results](./images/swirl_multi_mapping.png)

<br/>

:small_blue_diamond: The search endpoint now supports a provider URL parameter! 

```
http://localhost:8000/swirl/search/?q=knowledge+management&providers=3,maritime,news
```

The parameter will accept a SearchProvider id or tag. Full details: [Specifying SearchProviders with the providers URL Parameter](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#specifying-the-searchproviders-with-the-providers-url-parameter)

 
<br/>

:small_blue_diamond: ```scripts/email_load.py``` has been included to make it easy to load the [Enron email dataset](https://www.cs.cmu.edu/~enron/) into ElasticSearch

<br/>

## Changes

:small_blue_diamond: swirl_load.py has been moved to the SWIRL root directory

```
swirl-search% python swirl_load.py SearchProviders/google_pse.json -a admin -p some-admin-password
##S#W#I#R#L##1#.#6##############################################################

swirl_load.py: fed 3 into SWIRL, 0 errors
```

<br/>

:small_blue_diamond: The former ```GenericResultProcessor``` has been renamed ```MappingResultProcessor```

A new GenericResultProcessor now takes no option on results, allowing connectors that already produce the SWIRL format to save processing.

<br/>

## Issues Resolved

:small_blue_diamond: [Need to highlight alternative word forms](https://github.com/sidprobstein/swirl-search/issues/34)

```
"explain": {
                "stems": "agil oper",
                "body": {
                    "agile_operations_*": 0.7048520990053376,
                    "agile_24": 0.589995250602152,
                    "operations_10": 0.8256623948725578,
                    "operating_19": 0.6893337836077386
                }
            }
```

:small_blue_diamond: [Highlighting of terms with 's](https://github.com/sidprobstein/swirl-search/issues/44) 

```
"body": "*Elon* *Musk’s* top lieutenant at Tesla ... is now working at SpaceX after leaving Tesla over a strange controversy. more… The post *Elon* *Musk* moves his top lieutenant at Tesla to SpaceX after a controversy appeared first on Electrek ."
```

:small_blue_diamond: [Highlighting collisions](https://github.com/sidprobstein/swirl-search/issues/38) 

The updated CosineRelevancyProcessor should not allow this. Each term is highlighted once and only once. Please screen shot & [report any examples to support](#support).

:small_blue_diamond: [swirl.py not working on some Ubuntu configs](https://github.com/sidprobstein/swirl-search/issues/47)

swirl.py now checks to see if rabbitmq is running, and skips it if so:

```
sid@agentcooper swirl-search-master % python swirl.py start
##S#W#I#R#L##1#.#6##############################################################

Warning: rabbitmq appears to be running, skipping it:
  501 95899 95503   0  1:54PM ttys000    0:00.01 /bin/sh /usr/local/sbin/rabbitmq-server
Start: django -> daphne swirl_server.asgi:application ... Ok, pid: 95948
Start: celery-worker -> celery -A swirl_server worker --loglevel=info ... Ok, pid: 95963
Start: celery-beats -> celery -A swirl_server beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler ... Ok, pid: 95994
Updating .swirl... Ok
```

:heart: Thanks to all who reported this issue!!

<br/>

## Known Issues

:small_blue_diamond: [Creating searches from a browser with q=](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#creating-a-search-object-with-the-q-url-parameter) can sometimes create two Search objects. 

This is because of browser prefetch. [Turn off Chrome prefetch](https://www.technipages.com/google-chrome-prefetch). [Turn off Safari prefetch](https://stackoverflow.com/questions/29214246/how-to-turn-off-safaris-prefetch-feature)

Please [report any issues](https://github.com/sidprobstein/swirl-search/issues/) with this to [support](#support).

<br/>

# Documentation

* [Quick Start](https://github.com/sidprobstein/swirl-search/wiki/1.-Quick-Start)
* [User Guide](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide)

<br/>

# Support

:small_blue_diamond: [Create an Issue](https://github.com/sidprobstein/swirl-search/issues) if something doesn't work, isn't clear, or should be documented

:small_blue_diamond: Email: [support@swirl.today](mailto:support@swirl.today) with issues, requests, questions, etc - we'd love to hear from you!
