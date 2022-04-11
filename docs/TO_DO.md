# SWIRL TO DO LIST

## Refactors
- [ ] Search form
- [ ] add current ppl to swirl@probstein.com
- [ ] back-port explain to generic_relevancy_processor or delete it!
- [ ] url result construction in mappings (result?)

# Test P2
- [X] relevancy documentation
- [ ] It appears that ?q= and rerun may create a new query now? check P1
- [ ] fix URL generation in consumer.py (search.py) line 191 P2
- [ ] swirl.py should support clearing/zipping of logs? P2
- [ ] query_string_processed should be renamed query_string_pre_processed in search model DEFERRED

 ## New Features
- [ ] DOCKER P1
- [ ] search UI P1
- [ ] search?retry=id - P1 rerun only providers that failed etc P2+, if any provider fails during a search, put their id's in a list (new model field?) in the search "failed_providers"
- [ ] relevancy - date boost P2
- [ ] swirl paging part 2 P2
- [ ] report timings P3
- [ ] use callback or webhook to deliver results P3
- [ ] boolean push-down P1 - hard??? DB first?
- [ ] relevancy against payload!! P3 - hard???!

## Processors
- [ ] lookup query processor - CSV, DB - P2
- [ ] support execution of processors in lists - P3
 
## Mixers
- [ ] dedupe using URL P1

## Security
- [ ] Allow user to share objects with other users P2, other groups P3
- [ ] SSO M365 P1
- [ ] SFDC P2

## Cosmetics
- [-] dark mode for django admin - buggy, login and delete button don't work P2
- [-] change logo/text in django admin - doesn't work P2

--------------

## SWIRL Paging Design Part II
### PSE returns see bottom of page

* Add a new message in consumer.py (see below) that means "fetch more results from these providers"
* Add a federated task invokation that accepts a list of soon-to-be-exhausted providers

Then, if invoking result mixer, with page= specified...

* during the loop in which we construct the list of results to be returned, construct a dict of provider id and result #
* when done, update the dict with the next value for each, removing providers who don't have more results, and sending a message to consumer to get more results for those that are out at next page call (see next block)
* put this dict in the url of the mixed results, e.g. page_map, call it nextpage or something - look at google pse
* when the user calls page=next, take pagemap and start mixing from those offsets, and repeat all of this

Async, the consumer

* Receives the message from mixer, including the search_id and the list of soon-to-be exhausted providers
* The consumer creates a new federate task, passing it the the soon-to-be-exhausted list and the search object
* Each federate task handles this using Provider Paging Design Part 1, requesting another provider.results_per_query??

Ideally by the time the user calls for the next page, the celery tasks to get the next pages will be done and it will just work

--------------

## Connectors
- [ ] get/xml p2
- [ ] solr p1
- [ ] m365
- [ ] salesforce
- [ ] Add a credential example for sqlite3? P2
- [ ] Search past results
- [ ] Caching so that if you run the same search within x period, it takes you to the last result set 

## Features
- [ ] bulk load search providers via UI P2
- [ ] ablity to subscribe a query using webhook or callback P4
- [ ] sample code in python P2
- [ ] automated tests P2

## PSE Return for Paging, this is second page of results

"queries": {
    "previousPage": [  
      {
        "title": "Google Custom Search - pwc",
        "totalResults": "205000000",
        "searchTerms": "pwc",
        "count": 10,
        "startIndex": 1,
        "inputEncoding": "utf8",
        "outputEncoding": "utf8",
        "safe": "off",
        "cx": "7d473806dcdde5bc6"
      }
    ],
    "request": [
      {
        "title": "Google Custom Search - pwc",
        "totalResults": "205000000",
        "searchTerms": "pwc",
        "count": 10,
        "startIndex": 11,
        "inputEncoding": "utf8",
        "outputEncoding": "utf8",
        "safe": "off",
        "cx": "7d473806dcdde5bc6"
      }
    ],
    "nextPage": [
      {
        "title": "Google Custom Search - pwc",
        "totalResults": "205000000",
        "searchTerms": "pwc",
        "count": 10,
        "startIndex": 21,
        "inputEncoding": "utf8",
        "outputEncoding": "utf8",
        "safe": "off",
        "cx": "7d473806dcdde5bc6"
      }
    ]

## Completed

- [X] Change query to search??? YES
- [X] Change search.searchprovider_list to searchprovider_list
- [X] Change result.search_provider to result.searchprovider
- [X] Change json_result{'provider'} to 'searchprovider'
- [X] fix search_id_id name??? TBA
- [X] Update all documentation
- [X] Make mappings support jsonpath, e.g. _source.foo
- [X] Change generic result proc so that by default it only emits paths in the mappings into payload 
- [X] support a query string i.e. /swirl/search?q=<whatever> or query_string=<whatever> P1
- [X] Populate result_URL and mixer URL in search object
- [X] have cron job that removes queries & results per policy
- [X] We pass provider_name to connectors, should be by id - check all
- [X] searchproviders - add, list, delete, update
- [X] querys - add, list, delete, update
- [X] results - add, list, delete, update, mix
- [X] ASGI support with Daphne
- [X] ability to re-run a query P1
- [X] generic result processor
- [X] open search 1.1 result processor
- [X] mapping result processor - consumes mappings from searchprovider
- [x] spellcheck query processor
- [X] get/json
- [X] elastic 
- [X] open search 1.1
- [X] google pse
- [X] sqlite real - P1
- [X] sqlite result title & body - P1 
- [X] Add a credential example for requests_get P1
- [X] stack N
- [X] round_robin
- [X] Add mappings to model P1
- [X] Add credentials to model P1
- [X] Refactor jsonplaceholder comment providers to use mappings P1
- [X] Secure all api endpoints
- [X] mixers have their names in the module name unlike the others
- [X] allow search.searchprovider_list to be done by name or id
- [x] move cx and key in google pse to template
- [X] search?q
- [X] NO_PAYLOAD and what happens if you don't use it
- [X] query mappings including url and query_string, scanning of credentials
- [X] result_mappings with = and without
- [X] search?rerun=id deletes old result sets and reruns
- [X] retention & beats
- [X] How to change defaults for objects!!
- [X] break documentation into shorter ones
- [X] hunt print statements
- [X] to do: move features of search like opensearch and rerun to Using guide
- [X] redo all pictures in documentation
- [X] redo all links in documentation
- [X] Fix links at bottom https://github.com/sidprobstein/swirl_server/blob/master/docs/QUICK_START.md under "Next Steps" - 2 are broken
- [X] Clean up object reference examples
- [X] Broken images in SWIRL user and group support / developers guide
- [X] Search Expiration Service has broken image
- [X] Search Expiration Service has broken image
- [X] /swirl/index page
- [X] Fix elastic enron date_published
- [X] startup script
- [X] swirl paging part 1 i.e. &page=N on result
- [X] provider paging - make it so that we can get more than 10 results - needs testing
- [X] Elastic: connect locally, template fixes with ' instead of \", query and result mappings 
- [X] Figure out why?

http://localhost:8000/swirl/results/?search_id=166&result_mixer=round_robin_mixer

Error: request.get succeeded, count > 0, but json data was missing key 'items'",
        "Error: request.get succeeded, count > 0, but json data was missing key 'items'",
        "Error: request.get succeeded, count > 0, but json data was missing key 'items'"

Turns out, was in consumer.py, see commit TBD
- [X] fix stack mixer, maybe it should be stack_2 and stack_3
- [X] elastic paging P1
- [X] handle space in list of mappings
- [X] remove excessive logging... P1
- [X] remove json placeholder entirely, keep for testing request_get??? P1
- [X] Paging doc
- [X] simplified elastic template doc
- [X] swirl.py doc
- [X] Document http://127.0.0.1:8000/swirl/searchproviders/?format=json
- [X] log file locations
- [X] switch django debug to FALSE
- [X] all css is broken, why? P1 - it's bc debug=false, see https://stackoverflow.com/questions/5836674/why-does-debug-false-setting-make-my-django-static-files-access-fail#:~:text=For%20these%20reasons%2C%20the%20Django,fine%20to%20serve%20static%20files.
- [X] elastic connector should not complain about braces {} in template after processing
- [X] remove manage.py from repo REJECTED BAD IDEA
- [X] clean up settings.py and change secret key, seems to be OK to ship (and a bad idea to leave out)
- [x] add documentation to change secret key: generate secret key python -c "import secrets; print(secrets.token_urlsafe())"
- [x] note about rabbit mq password
- [X] swirl.py help should provide a list of services? move dict generation to main, make it global also
- [X] swirl.py check arguments against list of services
- [X] settings.py: create django secret key, generate secret key python -c "import secrets; print(secrets.token_urlsafe())"
- [X] mixer should not take credit in message if only one source :-) P1
- [X] for 429 error (opensearch) add provider.name ... maybe others P1
- [X] settings.py should be removed from source control - DECLINED
- [X] check all return codes P1
- [X] try/catch logic P1
- [X] logging consistency P1
- [X] swagger P2
- [X] ticket system P2
- [X] document/test how to retain a query or result set you want to save
- [X] ASGI support with Daphne
- [X] startup scripts
- [X] bulk load search providers via CLI P1
- [X] document how to delete/edit stuff - P1
- [X] remove producer and consumer
- [X] remove celery config items?
- [X] go back to debug=False
- [X] rename federate() to search()
- [X] federate() to search()
- [X] remove consumer.py references
- [X] break Developer guide into User, Developer, Admin P1
- [X] Beats/retention
- [X] install clean from tarball, git - can we use swirl.py migrate? if so add gatherstatic and make a setup command instead
- [X] swirl.py should not print OK after error P1
- [X] swirl.py start rabbitmq before migration etc
- [X] swirl.py flush, migrate 
- [X] swirl.py migrate output
- [X] change rank from 99 down to 1 up
- [X] remove highlight in generic processors
- [X] highlight and score in post-result "relevancy_processor"
- [X] then have mixers use score if present
- [X] put a results info block with the next page url (&page=2 etc)
- [X] checklist on what to do to biuld a connector e.g. handle paging, handling sort by date
- [X] searchprovider json examples are hard to find, link in Developer Guide preceeded by :star: is bad
- [X] further reading at bottom of developer guide is bad link (extra )
- [X] relevancy part 1 highlight & field-hit rank
- [X] check some query_to_provider results may be blank probably in google PSE, may be because of refactors to saving Search or Result objects P1
- [X] relevancy ranking
- [X] templates in result_mappings, e.g. '{company} in {city} raised {raisedCurrency}{raisedAmt} for series {round}=body' this would sorta solve url also
- [X] boost on # of fields (.100 per additional field)
- [X] boost on phrase (.100 per field) 
- [X] date sort P1  w/elastic, opensearch & db P1
- [X] document rescore
- [X] add active/inactive setting to searchprovider P1 - if id or name specified it still runs; if the default [] is used and it is inactive, it is not run
- [X] fix localhost references in code
- [X] move relevnacy parts of generic.py into relevancy.py!
- [X] Add admin creation to swirl.py setup - can't
- [X] Create a short, concise quick start since it seems fast
- [X] new repo P1
