# SWIRL SEARCH TO DO LIST

## Refactors
- [ ] back-port explain vector to generic_relevancy_processor, or delete it
- [ ] Url result construction
- [ ] Clean up Enron email body

## New Features
- [ ] Docker P1
- [ ] Search UI P1
- [ ] search?retry=id - P1 rerun only providers that failed etc
- [ ] If any provider fails during a search, put their ids in a list (new model field) in the search "failed_providers" P2
- [ ] Relevancy - date boost P2
- [ ] Paging Part 2 P2
- [ ] Report timings P3
- [ ] Use callback or webhook to deliver results P3
- [ ] Rename query_string_processed to query_string_pre_processed in search model
- [ ] swirl.py start management (sqlite, open rabbit window, open /admin window?)

## Processors
- [ ] Lookup query processor - scans for regex in query, replaces with value(s) from CSV or SQlite - P1
 
## Mixers
- [ ] Dedupe using URL P1 

## Security
- [ ] Allow user to share objects with other users P2, other groups P3

## Cosmetics
- [ ] Change logo/text in django admin P1
- [ ] Dark mode for django admin - see swirl/templates/x_*.html, remove x_ to enable them again; currently login and delete button don't work P2
- [ ] Dark mode for swagger?

## Connectors
- [ ] Http get with auth and xml response
- [ ] SOLR
- [ ] Add a credential example for Sqlite3 P2
- [ ] RBD connector with sql-alchemy
- [ ] Search past results 
- [ ] Caching so that if you run the same search within x period, it takes you to the last result set, otherwise, refreshes it? P3 #MAJOR

## Features
- [ ] bulk load search providers via UI P2
- [ ] ablity to subscribe a query using webhook or callback P4
- [ ] sample code in python P2
- [ ] automated tests P2

## Test P2
- [ ] It appears that ?q= and rerun may create a new query sometimes P1

--------------

# SWIRL SEARCH Paging Design, Part 2

* Add a new task that "fetches more results from these providers"
* Add a federated task invokation that accepts a list of soon-to-be-exhausted providers

Then, if invoking result mixer, with page= specified...

* During the loop in which we construct the list of results to be returned, construct a dict of provider id and result #
* When done, update the dict with the next value for each, removing providers who don't have more results, and sending a message to get more results for those that are out at next page call (see next block)
* Put this dict in the url of the mixed results, e.g. page_map, call it nextpage or something - look at google pse
* When the user calls page=next, take pagemap and start mixing from those offsets, and repeat all of this

Async, the new task

* Receives the message from mixer, including the search_id and the list of soon-to-be exhausted providers
* Creates a new federate task, passing it the the soon-to-be-exhausted list and the search object
* Each federate task handles this using Provider Paging Design Part 1, requesting another provider.results_per_query worth of data, specifying the starting page

By the time the user calls for the next page, the celery tasks to get the next pages will be landed

-------------

# SWIRL SEARCH UI Requirements

* Nav links across top, e.g. management tools, searchproviders
* Search box
* Spellcheck option?
* Search history
* Messages area that can be open/closed
* Better source/retrieved display 
* Put rank & score in box left aligned
* Color code score yellow < 0.6 red < 0.4?
* Retention picker
* Sort by relevancy/date 
* Filter by sourceprovider
* Filter by date, author
* Save item (TBD)
