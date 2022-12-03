![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# SWIRL SEARCH 1.7

This version incorporates feedback around UI and hosting usability. 

## PLEASE STAR OUR REPO: [http://swirl.today/](http://swirl.today)

<br/>

![SWIRL qs query](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/swirl_qs_parameter.png)

<br/>

## New Features

:small_blue_diamond: The new qs URL parameter provides a synchronous response, with no need to poll or handle a redirect. 

qs accepts the same arguments as the q parameter:

```
localhost:8000/swirl/search/?qs=knowledge+management
```

```
localhost:8000/swirl/search/?qs=knowledge+management+software+NOT+practice
```

```
localhost:8000/swirl/search/?qs='knowledge+management'+software+NOT+practice&providers=news,email,companies
```

The result_mixer can be specified as well:

```
localhost:8000/swirl/search/?qs=knowledge+management&result_mixer=DateMixer
```

Only the first page of results are provided. Use the next_page link in the info.results block to access additional pages.

More details: [Getting synchronous results with the qs URL Parameter](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#getting-synchronous-results-with-the-qs-url-parameter)

<br/>

:small_blue_diamond: Django User permissions are now enforced on SearchProvider, Search and Result objects.

![Django Admin, SWIRL Permissions](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/django_admin_console_permissions.png)
 
More details: [Permissioning Users](https://github.com/sidprobstein/swirl-search/wiki/5.-Admin-Guide#permissioning-users)

<br/>

## Changes

:small_blue_diamond: swirl.py now supports a ```logs``` command that will output all log files to the console

```
swirl-search% python swirl.py logs
__S_W_I_R_L__1_._7______________________________________________________________

tail -f logs/*.log - hit ^C to stop:

==> logs/django.log <==
127.0.0.1:58635 - - [02/Dec/2022:19:27:10] "GET /admin/" 200 8932
...etc...
```

<br/>

## Issues Resolved

:small_blue_diamond: [key error: 'searchprovider_rank' when processing results with GenericResultProcessor](https://github.com/sidprobstein/swirl-search/issues/67)

:small_blue_diamond: [PostgreSQL driver Psycopg2 issues](https://github.com/sidprobstein/swirl-search/issues/55)

The PostgreSQL connector has been removed from [swirl.connectors.__init__]](../swirl/connectors/__init__.py) to avoid warnings, and the [documentation](https://github.com/sidprobstein/swirl-search/wiki/4.-Object-Reference#installing-the-postgresql-driver) has been updated.

<br/>

## Known Issues

:small_blue_diamond: SWIRL won't highlight terms that have preceeding or trailing quotes

For example ```'hello``` or ```'hello'```. These may be quite acceptable to search engines as phrase searches. This will be fixed in a future release.

<br/>

:small_blue_diamond: [Creating searches from a browser with q=](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#creating-a-search-object-with-the-q-url-parameter) can sometimes create two Search objects. 

This is because of browser prefetch. [Turn off Chrome prefetch](https://www.technipages.com/google-chrome-prefetch). [Turn off Safari prefetch](https://stackoverflow.com/questions/29214246/how-to-turn-off-safaris-prefetch-feature)

Please [report any issues](https://github.com/sidprobstein/swirl-search/issues/) with this to [support](#support).

<br/>

# Upgrading

:warning: Version 1.7 requires database migration. Details: [Upgrading SWIRL](https://github.com/sidprobstein/swirl-search/wiki/5.-Admin-Guide#upgrading-swirl)

<br/>

# Documentation

* [Quick Start](https://github.com/sidprobstein/swirl-search/wiki/1.-Quick-Start)
* [User Guide](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide)

<br/>

# Support

:small_blue_diamond: [Create an Issue](https://github.com/sidprobstein/swirl-search/issues) if something doesn't work, isn't clear, or should be documented

:small_blue_diamond: Email: [support@swirl.today](mailto:support@swirl.today) with issues, requests, questions, etc - we'd love to hear from you!
