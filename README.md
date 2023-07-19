<h1>Swirl Metasearch 2.1<img alt='Swirl Metasearch Logo' src='.github/images/swirl-logo-transparent.png'  width='148' align='right' /></h1>

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?color=blue&logoColor=blue&style=flat)](https://opensource.org/license/apache-2.0/)
[![GitHub Release](https://img.shields.io/github/v/release/swirlai/swirl-search?style=flat&label=Release)](https://github.com/swirlai/swirl-search/releases)
[![Docker Build](https://github.com/swirlai/swirl-search/actions/workflows/docker-image.yml/badge.svg?branch=main)](https://github.com/swirlai/swirl-search/actions/workflows/docker-image.yml)
[![Tests](https://github.com/swirlai/swirl-search/actions/workflows/smoke-tests.yml/badge.svg?branch=main)](https://github.com/swirlai/swirl-search/actions/workflows/smoke-tests.yml)
[![Built with spaCy](https://img.shields.io/badge/Built%20with-spaCy-09a3d5.svg?color=blue)](https://spacy.io)
[![Slack](https://img.shields.io/badge/Slack--channel-gray?logo=slack&logoColor=black&style=flat)](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)
[![Newsletter](https://img.shields.io/badge/Newsletter-gray?logo=revue&logoColor=black&style=flat)](https://groups.google.com/g/swirl-announce)
[![Twitter](https://img.shields.io/twitter/follow/SWIRL_SEARCH?label=Follow%20%40SWIRL_SEARCH&color=gray&logoColor=black&style=flat)](https://twitter.com/SWIRL_SEARCH)

## Table of Contents

-   [Overview](#overview)
-   [What is Swirl?](#what-is-swirl)
-   [Extended Documentation](README_Extended.md)

## Overview

Swirl is an **open source metasearch platform** for your siloed data.

If you want to get started with Swirl Metasearch, check:

-   [Swirl in docker](README_Extended.md#try-swirl-now)
-   [Swirl in cloud](README_Extended.md#try-swirl-cloud)

You can find our [documentation here](https://github.com/swirlai/swirl-search/wiki).

## What is Swirl?

**SWIRL Search** is a Metasearch platform that utilizes AI, specifically [large language models](https://techcrunch.com/2022/04/28/the-emerging-types-of-language-models-and-why-they-matter/), to distribute queries to various resources with a search API. These resources can include search engines, databases, noSQL engines, and cloud/SaaS services. Unlike traditional search engines, SWIRL Search does not extract or index any information, but re-ranks the unified results from these diverse sources.

The platform supports OAUTH2 integration with a range of enterprise services, including Microsoft 365, Atlassian, JetBrains YouTrack, with more services planned for future integration.

Through its updated Spyglass UI, users can systematically review the top results from various configured services, including:

-   [Apache Solr](https://solr.apache.org/)
-   [ChatGPT](https://openai.com/blog/chatgpt/)
-   [Elastic](https://www.elastic.co/cn/downloads/elasticsearch)
-   [OpenSearch](https://opensearch.org/downloads.html)
-   [PostgreSQL](https://www.postgresql.org/)
-   [Google BigQuery](https://cloud.google.com/bigquery)

It also supports generic HTTP/GET/JSON configurations and offers configurations for premium services like:

-   [Google's Programmable Search Engine](https://programmablesearchengine.google.com/about/)
-   [Miro](https://miro.com/app/)
-   [Northern Light Research](https://northernlight.com/)

![Metasearch diagram](https://raw.githubusercontent.com/wiki/swirlai/swirl-search/images/swirl_arch_diagram.jpg)

Built on the Python/Django stack, Swirl is intended for use by search managers, developers, data scientists and engineers who want to solve multi-silo search problems - including notification services - without moving, re-indexing or re-permissioning sensitive information.

### Learn more: [Documentation Wiki](https://github.com/swirlai/swirl-search/wiki)

| ## Table of Contents                                            |
| :-------------------------------------------------------------- |
| [Swirl Metasearch 2.1](README_Extended.md/#swirl-metasearch-21) |
| [Overview](README_Extended.md/#overview)                        |
| [What is Swirl?](README_Extended.md/#what-is-swirl)             |
| [Try Swirl Now](README_Extended.md/#try-swirl-now)              |
| [Try Swirl Cloud](README_Extended.md/#try-swirl-cloud)          |
| [Download Swirl](README_Extended.md/#download-swirl)            |
| [Documentation Wiki](README_Extended.md/#documentation-wiki)    |
| [Key Features](README_Extended.md/#key-features)                |
| [Support](README_Extended.md/#support)                          |
