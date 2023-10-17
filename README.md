[![Swirl](https://docs.swirl.today/images/hack_swirl_fest.png)](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)

<div align="center">

[![Swirl](https://docs.swirl.today/images/transparent_header_3.png)](https://www.swirl.today)

</div>

<h1 align="center">Swirl</h1>

<div align="center">

### Swirl is open-source software that simultaneously searches multiple content sources and returns AI ranked results.

<div align="center">


[𝚂𝚝𝚊𝚛𝚝 𝚂𝚎𝚊𝚛𝚌𝚑𝚒𝚗𝚐](#-try-swirl-now-in-docker) ⦁
[𝚂𝚕𝚊𝚌𝚔](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw) ⦁
[𝙺𝚎𝚢 𝙵𝚎𝚊𝚝𝚞𝚛𝚎𝚜 ](#-key-features) ⦁
[𝙲𝚘𝚗𝚝𝚛𝚒𝚋𝚞𝚝𝚎](#-contributing-to-swirl) ⦁
[𝙳𝚘𝚌𝚞𝚖𝚎𝚗𝚝𝚊𝚝𝚒𝚘𝚗](#-documentation) ⦁ [𝙲𝚘𝚗𝚗𝚎𝚌𝚝𝚘𝚛𝚜](#-list-of-connectors)


</div>

---

<br/>

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?color=088395&logoColor=blue&style=flat-square)](https://opensource.org/license/apache-2-0/)
[![GitHub Release](https://img.shields.io/github/v/release/swirlai/swirl-search?style=flat-square&color=8DDFCB&label=Release)](https://github.com/swirlai/swirl-search/releases)
[![Slack](https://custom-icon-badges.demolab.com/badge/Join%20Our%20Slack-black?style=flat-square&logo=slack&color=0E21A0&logoColor=white)](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)
[![PRs Welcome](https://custom-icon-badges.demolab.com/badge/PRs%20Welcome-black?style=flat-square&logo=github&color=4D2DB7&logoColor=C70039)](#contributing-to-swirl)
[![Website](https://custom-icon-badges.demolab.com/badge/www.swirl.today-black?style=flat-square&logo=globe&color=241468&logoColor=white)](https://www.swirl.today)
[![Docker Build](https://github.com/swirlai/swirl-search/actions/workflows/docker-image.yml/badge.svg?style=flat-square&branch=main)](https://github.com/swirlai/swirl-search/actions/workflows/docker-image.yml)
[![Tests](https://github.com/swirlai/swirl-search/actions/workflows/smoke-tests.yml/badge.svg?branch=main)](https://github.com/swirlai/swirl-search/actions/workflows/smoke-tests.yml)

</div>

Swirl is open source software that simultaneously searches multiple content sources and returns AI ranked results. Prompt your choice of Generative AI using the top N results to get answers incorporating your own data.

Swirl can connect to:

* Databases (SQL & NoSQL, Google BigQuery)
* Public data services (Google Programmable Search, Arxiv.org, etc.)
* Enterprise sources (Microsoft 365, Jira, Miro etc.)

And generate insights with AI and LLMs like ChatGPT. Start discovering and generating the answers you need based on your data.

Swirl is as simple as ABC: (a) Download YML, (b) Start in Docker, (c) Search with Swirl. From there, add credentials to preloaded SearchProviders to get results from more sources.

## 🚀 Try Swirl with ChatGPT 

![Swirl with ChatGPT as a configured AI Model](https://docs.swirl.today/images/Animation_1.gif)

_Swirl with ChatGPT as a configured AI Model._

>**Note**
> We need your help 🙏. Help us create more examples of things you can or want to do with Swirl. Join our [Slack Community](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw) to discuss and learn more. We'd be very happy to help you contribute 🤗!

<br/>

# 🔎 How Swirl Works

Swirl adapts and distributes user queries to anything with a search API - search engines, databases, noSQL engines, cloud/SaaS services, data siloes, etc. And uses Large Language Models to re-rank the unified results *without* extracting or indexing *anything*. 

![Swirl Diagram](https://docs.swirl.today/images/Animation_2.gif)

<br/>

# 🔌 List of Connectors

<img src="https://docs.swirl.today/images/Connectors_2.png" height=60% width=70%/>

➕ **For Enterprise Support on Connectors**  Contact the Swirl Team at: [support@swirl.today](mailto:support@swirl.today)  

🚀 **Help Us Expand!** Want to see a new connector? [Contribute by adding a connector](#👩‍💻-contributing-to-swirl) and join our growing community of contributors. 

<br/>

# 🔥 Try Swirl Now In Docker

## Prerequisites

* To run Swirl in Docker, you must have the latest [Docker app](https://docs.docker.com/get-docker/) for MacOS, Linux, or Windows installed and running locally.

* Windows users must also install and configure either the WSL 2 or the Hyper-V backend, as outlined in the  [System Requirements for installing Docker Desktop on Windows](https://docs.docker.com/desktop/install/windows-install/#system-requirements).

## Start Swirl in Docker

> **Warning** 
> Make sure the Docker app is running before proceeding!

* Download [https://raw.githubusercontent.com/swirlai/swirl-search/main/docker-compose.yaml](https://raw.githubusercontent.com/swirlai/swirl-search/main/docker-compose.yaml)

```
curl https://raw.githubusercontent.com/swirlai/swirl-search/main/docker-compose.yaml -o docker-compose.yaml
```

* In MacOS or Linux, run the following command from the Console:

```
docker-compose pull && docker-compose up
```

* In Windows, run the following command from PowerShell:

```
docker compose up
```

After a few minutes the following or similar should appear:

<img src="https://docs.swirl.today/images/swirl_docker_1.png" height="70%" width="90%">

* Open this URL with a browser: <http://localhost:8000> (or <http://localhost:8000/galaxy>)

* If the search page appears, click `Log Out` at the top, right. The Swirl login page will appear.

* Enter the username `admin` and password `password`, then click `Login`.

* Enter a search in the search box and press the `Search` button. Ranked results appear in just a few seconds:

<img src="https://docs.swirl.today/images/galaxy_ui_2.png" height="70%" weight="70%">

* To view the raw JSON, open <http://localhost:8000/swirl/search/>

The most recent Search object will be displayed at the top. Click on the `result_url` link to view the full JSON Response.

## Notes 📝

> **Warning**
> The Docker version of Swirl *does not* retain any data or configuration when shut down!

:key: Swirl includes four (4) Google Programmable Search Engines (PSEs) to get you up and running right away. The credentials for these are shared with the Swirl Community.

:key: Using Swirl with Microsoft 365 requires installation and approval by an authorized company Administrator. For more information, please review the [M365 Guide](https://docs.swirl.today/4.-M365-Guide.html) or [contact us](mailto:hello@swirl.today).

## Next Steps 👇

* Check out the details of our [latest release](https://github.com/swirlai/swirl-search/releases)!

* Head over to the [Quick Start Guide](https://docs.swirl.today/1.-Quick-Start.html) and install Swirl locally!

<br/>

# 🌟 Key Features

| ✦ | Feature |
|:-----:|:--------|
| 📌 | [Microsoft 365 integration and OAUTH2 support](https://docs.swirl.today/4.-M365-Guide.html) |
| 🔍 | [SearchProvider configurations](https://github.com/swirlai/swirl-search/tree/main/SearchProviders) for all included Connectors. They can be [organized with the active, default and tags properties](https://docs.swirl.today/2.-User-Guide.html#organizing-searchproviders-with-active-default-and-tags). |
| ✏️ | [Adaptation of the query for each provider](https://docs.swirl.today/2.-User-Guide.html#search-syntax) such as rewriting `NOT term` to `-term`, removing NOTted terms from providers that don't support NOT, and passing down the AND, + and OR operators. |
| ⏳ | [Synchronous or asynchronous search federation](https://docs.swirl.today/5.-Developer-Guide.html#architecture) via [APIs](http://localhost:8000/swirl/swagger-ui/) |
| 🛎️ | [Optional subscribe feature](https://docs.swirl.today/5.-Developer-Guide.html#subscribe-to-a-search) to continuously monitor any search for new results |
| 🛠️ | Pipelining of [Processor](https://docs.swirl.today/5.-Developer-Guide.html#develop-new-processors) stages for real-time adaptation and transformation of queries, responses and results |
| 🗄️ | [Results stored](https://docs.swirl.today/6.-Developer-Reference.html#result-objects) in SQLite3 or PostgreSQL for post-processing, consumption and/or analytics |
| ➡️ | Built-in [Query Transformation](https://docs.swirl.today/5.-Developer-Guide.html#using-query-transformations) support, including re-writing and replacement |
| 📖 | [Matching on word stems](https://docs.swirl.today/6.-Developer-Reference.html#cosinerelevancypostresultprocessor) and [handling of stopwords](https://docs.swirl.today/5.-Developer-Guide.html#configure-stopwords-language) via NLTK |
| 🚫 | [Duplicate detection](https://docs.swirl.today/5.-Developer-Guide.html#detect-and-remove-duplicate-results) on field or by configurable Cosine Similarity threshold |
| 🔄 | Re-ranking of unified results [using Cosine Vector Similarity](https://docs.swirl.today/6.-Developer-Reference.html#cosinerelevancypostresultprocessor) based on [spaCy](https://spacy.io/)'s large language model and [NLTK](https://www.nltk.org/) |
| 🎚️ | [Result mixers](https://docs.swirl.today/6.-Developer-Reference.html#mixers-1) order results by relevancy, date or round-robin (stack) format, with optional filtering of just new items in subscribe mode |
| 📄 | Page through all results requested, re-run, re-score and update searches using URLs provided with each result set |
| 📁 | [Sample data sets](https://github.com/swirlai/swirl-search/tree/main/Data) for use with SQLite3 and PostgreSQL |
| ✒️ | [Optional spell correction](https://docs.swirl.today/5.-Developer-Guide.html#add-spelling-correction) using [TextBlob](https://textblob.readthedocs.io/en/dev/quickstart.html#spelling-correction) |
| ⌛ | [Optional search/result expiration service](https://docs.swirl.today/3.-Admin-Guide.html#search-expiration-service) to limit storage use |
| 🔌 | Easily extensible [Connector](https://github.com/swirlai/swirl-search/tree/main/swirl/connectors) and [Mixer](https://github.com/swirlai/swirl-search/tree/main/swirl/mixers) objects |


<br/>

# 👩‍💻 Contributing to Swirl 

**Got a brilliant idea or improvement for Swirl?** We're all ears—and thrilled you're here to help!

🔗 **Get Started in 3 Easy Steps**:
1. **Connect with Fellow Enthusiasts** - Jump into our [Slack community](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw) and share your ideas. You'll find a welcoming group of Swirl enthusiasts and team members eager to assist and collaborate.
2. **Branch It Out** - Always branch off from the `develop` branch with a descriptive name that encapsulates your idea or fix. Remember, all PRs should be made to the `develop` branch to ensure `main` remains our stable gold-standard.
3. **Start Your Contribution** - Ready to get your hands dirty? Make sure all contributions come through a GitHub pull request. We roughly follow the [Gitflow branching model](https://nvie.com/posts/a-successful-git-branching-model/), so all changes destined for the next release should be made to the `develop` branch.

📚 **First time contributing on GitHub?** No worries, the [GitHub documentation](https://docs.github.com/en/get-started/quickstart/contributing-to-projects) has you covered with a great guide on contributing to projects.

💡 Every contribution, big or small, makes a difference. Join us in shaping the future of Swirl!


<br/>

# ☁ Use the Swirl Cloud 

For information about Swirl as a managed service, please [contact us](mailto:hello@swirl.today)!

<br/>

# 📖 Documentation

[Overview](https://docs.swirl.today/) | [Quick Start](https://docs.swirl.today/1.-Quick-Start) | [User Guide](https://docs.swirl.today/2.-User-Guide) | [Admin Guide](https://docs.swirl.today/3.-Admin-Guide) | [M365 Guide](https://docs.swirl.today/4.-M365-Guide) | [Developer Guide](https://docs.swirl.today/5.-Developer-Guide) | [Developer Reference](https://docs.swirl.today/6.-Developer-Reference)

<br/>

# 👷‍♂️ Need Help? We're Here for You!

At Swirl, every user matters to us. Whether you're a beginner finding your way or an expert with feedback, we're here to support, listen, and help. Don't hesitate to reach out us.

* 🎉 **Join the Conversation:** Dive into our vibrant [Swirl Metasearch Community on Slack](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw) - it's where all the magic happens!

* 📧 **Direct Support:** For any questions, suggestions, or even a simple hello, drop us an email at [support@swirl.today](mailto:support@swirl.today). We cherish every message and promise to get back to you promptly!

* 💼 **Request A Connector (Enterprise Support)** Want to see a new connector quickly and fast. Contact the Swirl Team at: [support@swirl.today](mailto:support@swirl.today)

Remember, you're part of our family now. 🌍💙


<br/>
