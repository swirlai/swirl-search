![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# SWIRL SEARCH 1.5

This version consists of a new relevancy model supported by stemmed matching and cleaning of source responses.

:warning: Installing the new packages is required before upgrading. Read more: [Upgrading to 1.5](#upgrading)

## Changes

![SWIRL SEARCH 1.5 Vector Similarity Re-Ranked Unified Results](images/swirl_results_focus.png)

:small_blue_diamond: New relevancy model which weights and aggregates the similarity of each query match against the most relevant section of text, and normalizes results by length

:small_blue_diamond: Matching on stems using [nltk](https://www.nltk.org/) and highlighting of actual matches

:small_blue_diamond: Removal of html tags and entities with [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)

:small_blue_diamond: Relevancy scores are now broken by date_published, descending

## Issues Resolved

:small_blue_diamond: [Re-run and re-score now remove previous search.messages, and provide an update with timestamp](https://github.com/sidprobstein/swirl-search/issues/35) 

:small_blue_diamond: [Fixed highlighting interaction with tags](https://github.com/sidprobstein/swirl-search/issues/33) by removing tags prior to highlighting

:small_blue_diamond: [Fixed newsdata.io](https://github.com/sidprobstein/swirl-search/issues/28) including date_published and author mappings

:small_blue_diamond: Fixed date_published conversion from PostgreSQL

:small_blue_diamond: Updated swirl.py help to clarify lists, show core service

## Upgrading

For all platforms other than docker, run the following from the command line, in the swirl installation folder:

```
python install.py
./install.sh
```

(Windows users, run install.bat)

If these scripts don't work for any reason, install manually:

```
pip install -r requirements.txt
python -m spacy download en_core_web_lg
python -m nltk.downloader stopwords
python -m nltk.downloader punkt
```

<br/>

:warning: Docker users need to restart their image to get the new version. Containers using sqlite3 for storage delete all content upon shut down! Read more: [Docker Build for SWIRL](https://github.com/sidprobstein/swirl-search/blob/main/docs/DOCKER_BUILD.md)

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

:small_blue_diamond: [Create an Issue](https://github.com/sidprobstein/swirl-search/issues) if something doesn't work, isn't clear, or should be documented - we'd love to hear from you!

:small_blue_diamond: Paid support and consulting are available... [contact SWIRL](mailto:support@swirl.today) for more information.
