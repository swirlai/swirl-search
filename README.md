<div align="center">

[![Swirl](https://docs.swirl.today/images/transparent_header_3.png)](https://www.swirlaiconnect.com)

<h1>SWIRL AI Connect</h1>

### _Bring AI to the Data, not the Data to the AI._

### SWIRL AI Connect is AI Infrastructure Software. We aim to build a safe, secure and robust AI Infrastructue for the enterprise.

[Start Searching](#-try-swirl-now-in-docker) · [Slack](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw) · [Key Features ](#-key-features) · [Contribute](#-contributing-to-swirl) · [Documentation](#-documentation) · [Connectors](#-list-of-connectors)


<br/>

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?color=088395&logoColor=blue&style=flat-square)](https://opensource.org/license/apache-2-0/)
[![GitHub Release](https://img.shields.io/github/v/release/swirlai/swirl-search?style=flat-square&color=8DDFCB&label=Release)](https://github.com/swirlai/swirl-search/releases)
[![Website](https://img.shields.io/badge/Website-swirlaiconnect.com-00215E?style=flat-square)](https://www.swirlaiconnect.com)
[![SWIRL Slack](https://img.shields.io/badge/Slack-SWIRL%20Community-0E21A0?logo=slack&style=flat-square)](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)

[![Docker Build](https://github.com/swirlai/swirl-search/actions/workflows/docker-image.yml/badge.svg?style=flat-square&branch=main)](https://github.com/swirlai/swirl-search/actions/workflows/docker-image.yml)
[![Tests](https://github.com/swirlai/swirl-search/actions/workflows/smoke-tests.yml/badge.svg?branch=main)](https://github.com/swirlai/swirl-search/actions/workflows/smoke-tests.yml)

</div>



**Get your AI up and running in minutes, not months.** SWIRL AI Connect is an open-source platform that simplifies AI infrastructure setup and empowers Retrieval Augmented Generation (RAG) without the complexity of additional tools.

### Why SWIRL AI Connect?

* **Instant AI:**  Deploy your AI solutions rapidly with built-in security controls (data compliance, firewall, granular access, etc.).
* **RAG Made Easy:** Perform Retrieval Augmented Generation directly on your data, eliminating the need for vector databases, LangChain, or LlamaIndex.
* **No Data Movement:** No ETL, re-indexing, or data movement. Work with your data where it lives.
* **Boost Productivity:**  Enhance your team's efficiency by finding information faster and streamlining workflows.

<br/>

## SWIRL AI Connect Features

![Features](SWIRL_AI_Connect_Features/Feature_1.png)
![Features](SWIRL_AI_Connect_Features/Feature_2.png)

## Based on SWIRL AI Connect

![](SWIRL_AI_Connect_Features/Products_1.png)

# 🔎 How Swirl Works

SWIRL AI Connect adapts and distributes user queries to anything with a search API - search engines, databases, noSQL engines, cloud/SaaS services, data siloes, etc. and uses Reader LLMs to re-rank the unified results *without* extracting or indexing *anything*. 

1. **Connect:**  Point SWIRL AI Connect to your data sources (databases, documents, etc.) adding in your auth/bearer token.
2. **Query:** Ask questions or provide prompts in natural language.
3. **Get Results:** SWIRL AI Connect combines powerful search with generative AI to deliver precise answers augmented by relevant context.

<br/>

# 🔌 List of Connectors

![GitHub Connectors](SWIRL_AI_Connect_Features/GitHub_Connectors.png)

**Full list of connectors is available [here](https://swirlaiconnect.com/connectors)**.

**For Enterprise Support on Connectors**  Contact the Swirl Team at: [support@swirl.today](mailto:support@swirl.today)  


<br/>

# 🔥 Try Swirl Now In Docker

## Prerequisites

* To run Swirl in Docker, you must have the latest [Docker app](https://docs.docker.com/get-docker/) for MacOS, Linux, or Windows installed and running locally.

* Windows users must also install and configure either the WSL 2 or the Hyper-V backend, as outlined in the  [System Requirements for installing Docker Desktop on Windows](https://docs.docker.com/desktop/install/windows-install/#system-requirements).

## Start Swirl in Docker

> **Warning** 
> Make sure the Docker app is running before proceeding!

* Download the YML file: [https://raw.githubusercontent.com/swirlai/swirl-search/main/docker-compose.yaml](https://raw.githubusercontent.com/swirlai/swirl-search/main/docker-compose.yaml)

```
curl https://raw.githubusercontent.com/swirlai/swirl-search/main/docker-compose.yaml -o docker-compose.yaml
```

* *Optional*: To enable Swirl's Real-Time Retrieval Augmented Generation (RAG) in Docker, run the following commands from the Console using a valid OpenAI API key:
``` shell
export MSAL_CB_PORT=8000
export MSAL_HOST=localhost
export OPENAI_API_KEY=‘<your-OpenAI-API-key>’
```

:key: Check out [OpenAI's YouTube video](https://youtu.be/nafDyRsVnXU?si=YpvyaRvhX65vtBrb) if you don't have an OpenAI API Key.

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

:key: Swirl includes five (5) Google Programmable Search Engines (PSEs) to get you up and running right away. The credentials for these are shared with the Swirl Community.

:key: Using Swirl with Microsoft 365 requires installation and approval by an authorized company Administrator. For more information, please review the [M365 Guide](https://docs.swirl.today/M365-Guide.html) or [contact us](mailto:hello@swirl.today).

## Next Steps 👇

* Check out the details of our [latest release](https://github.com/swirlai/swirl-search/releases)!

* Head over to the [Quick Start Guide](https://docs.swirl.today/Quick-Start.html) and install Swirl locally!

<br/>

# 🌟 Key Features

| ✦ | Feature |
|:-----:|:--------|
| 📌 | [Microsoft 365 integration and OAUTH2 support](https://docs.swirl.today/M365-Guide.html) |
| 🔍 | [SearchProvider configurations](https://github.com/swirlai/swirl-search/tree/main/SearchProviders) for all included Connectors. They can be [organized with the active, default and tags properties](https://docs.swirl.today/User-Guide.html#organizing-searchproviders-with-active-default-and-tags). |
| ✏️ | [Adaptation of the query for each provider](https://docs.swirl.today/User-Guide.html#search-syntax) such as rewriting `NOT term` to `-term`, removing NOTted terms from providers that don't support NOT, and passing down the AND, + and OR operators. |
| ⏳ | [Synchronous or asynchronous search federation](https://docs.swirl.today/Developer-Guide.html#architecture) via [APIs](http://localhost:8000/swirl/swagger-ui/) |
| 🛎️ | [Optional subscribe feature](https://docs.swirl.today/Developer-Guide.html#subscribe-to-a-search) to continuously monitor any search for new results |
| 🛠️ | Pipelining of [Processor](https://docs.swirl.today/Developer-Guide.html#develop-new-processors) stages for real-time adaptation and transformation of queries, responses and results |
| 🗄️ | [Results stored](https://docs.swirl.today/Developer-Reference.html#result-objects) in SQLite3 or PostgreSQL for post-processing, consumption and/or analytics |
| ➡️ | Built-in [Query Transformation](https://docs.swirl.today/Developer-Guide.html#using-query-transformations) support, including re-writing and replacement |
| 📖 | [Matching on word stems](https://docs.swirl.today/Developer-Reference.html#cosinerelevancypostresultprocessor) and [handling of stopwords](https://docs.swirl.today/Developer-Guide.html#configure-stopwords-language) via NLTK |
| 🚫 | [Duplicate detection](https://docs.swirl.today/Developer-Guide.html#detect-and-remove-duplicate-results) on field or by configurable Cosine Similarity threshold |
| 🔄 | Re-ranking of unified results [using Cosine Vector Similarity](https://docs.swirl.today/Developer-Reference.html#cosinerelevancypostresultprocessor) based on [spaCy](https://spacy.io/)'s large language model and [NLTK](https://www.nltk.org/) |
| 🎚️ | [Result mixers](https://docs.swirl.today/Developer-Reference.html#mixers-1) order results by relevancy, date or round-robin (stack) format, with optional filtering of just new items in subscribe mode |
| 📄 | Page through all results requested, re-run, re-score and update searches using URLs provided with each result set |
| 📁 | [Sample data sets](https://github.com/swirlai/swirl-search/tree/main/Data) for use with SQLite3 and PostgreSQL |
| ✒️ | [Optional spell correction](https://docs.swirl.today/Developer-Guide.html#add-spelling-correction) using [TextBlob](https://textblob.readthedocs.io/en/dev/quickstart.html#spelling-correction) |
| ⌛ | [Optional search/result expiration service](https://docs.swirl.today/Admin-Guide.html#search-expiration-service) to limit storage use |
| 🔌 | Easily extensible [Connector](https://github.com/swirlai/swirl-search/tree/main/swirl/connectors) and [Mixer](https://github.com/swirlai/swirl-search/tree/main/swirl/mixers) objects |

<br/>

# 👩‍💻 Contributing to Swirl 

**Do you have a brilliant idea or improvement for Swirl?** We're all ears, and thrilled you're here to help!

🔗 **Get Started in 3 Easy Steps**:
1. **Connect with Fellow Enthusiasts** - Jump into the [Swirl Slack Community](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw) and share your ideas. You'll find a welcoming group of Swirl enthusiasts and team members eager to assist and collaborate.
2. **Branch It Out** - Always branch off from the `develop` branch with a descriptive name that encapsulates your idea or fix.
3. **Start Your Contribution** - Ready to get your hands dirty? Make sure all contributions come through a GitHub pull request. We roughly follow the [Gitflow branching model](https://nvie.com/posts/a-successful-git-branching-model/), so all changes destined for the next release should be made to the `develop` branch.

📚 **First time contributing on GitHub?** No worries, the [GitHub documentation](https://docs.github.com/en/get-started/quickstart/contributing-to-projects) has you covered with a great guide on contributing to projects.

💡 Every contribution, big or small, makes a difference. Join us in shaping the future of Swirl!

<br/>

# ☁ Use the Swirl Cloud 

For information about Swirl as a managed service, please [contact us](mailto:hello@swirl.today)!

<br/>

# 📖 Documentation

[Overview](https://docs.swirl.today/) | [Quick Start](https://docs.swirl.today/Quick-Start) | [User Guide](https://docs.swirl.today/User-Guide) | [Admin Guide](https://docs.swirl.today/Admin-Guide) | [M365 Guide](https://docs.swirl.today/M365-Guide) | [Developer Guide](https://docs.swirl.today/Developer-Guide) | [Developer Reference](https://docs.swirl.today/Developer-Reference) | [AI Guide](https://docs.swirl.today/AI-Guide)

<br/>

# 👷‍♂️ Need Help? We're Here for You!

At Swirl, every user matters to us. Whether you're a beginner finding your way or an expert with feedback, we're here to support, listen, and help. Don't hesitate to reach out to us.

* 🎉 **Join the Conversation:** Dive into our vibrant [Swirl Community on Slack](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw) - it's where all the magic happens!

* 📧 **Direct Support:** For any questions, suggestions, or even a simple hello, drop us an email at [support@swirl.today](mailto:support@swirl.today). We cherish every message and promise to get back to you promptly!

* 💼 **Request A Connector (Enterprise Support)** Want to see a new connector quickly and fast. Contact the Swirl Team at: [support@swirl.today](mailto:support@swirl.today)

Remember, you're part of our family now. 🌍💙
