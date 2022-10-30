![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# SWIRL SEARCH 1.2.1

This version continues improving developer usability and resolves issues found in 1.2.

## Changes

:small_blue_diamond: New Object Oriented Processors

Query Processors: GenericQueryProcessor, GenericQueryCleaningProcessor
Result Processors: GenericResultProcessor
Post-Result Processors: CosineRelevancyProcessor

Here's the new GenericQueryCleaningProcessor - again around a 90% reduction in code vs 1.1:

```
class GenericQueryCleaningProcessor(QueryProcessor):

    type = 'GenericQueryCleaningProcessor'
    chars_allowed_in_query = [' ', '+', '-', '"', "'", '(', ')', '_', '~'] 

    def process(self):

        try:
            query_clean = ''.join(ch for ch in self.query_string.strip() if ch.isalnum() or ch in self.chars_allowed_in_query)
        except NameError as err:
            self.error(f'NameError: {err}')
        except TypeError as err:
            self.warning(f'TypeError: {err}')
        if self.input != query_clean:
            logger.info(f"{self}: rewrote query from {self.input} to {query_clean}")

        self.query_string_processed = query_clean
        return self.query_string_processed
```

The only change required to use these processors is to change the "various processor" settings in the [SearchProvider](../SearchProviders/current.json) and [Search objects](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#search)). 

All of the included SearchProviders have been updated.

For more information consult the Developers Guide [Processors](https://github.com/sidprobstein/swirl-search/wiki/4.-Object-Reference#processors) section.

<br/>

:small_blue_diamond: Added use of django-environ to ease future deployments.

If you are installing locally, don't forget to install this package:

```
pip install django-environ
```

<br/>

## Known Issues

:small_blue_diamond: [Creating searches from a browser with q=](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#creating-a-search-object-with-the-q-url-parameter) can sometimes create two Search objects. 

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

:small_blue_diamond: Paid support and consulting are available... [contact SWIRL](mailto:support@swirl.today) for more information.
