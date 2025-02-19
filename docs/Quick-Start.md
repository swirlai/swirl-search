---
layout: default
title: Quick Start
nav_order: 3
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

# Quick Start Guide - Community Edition

{: .warning }
This version applies to the Community Edition of SWIRL!

* To run SWIRL in Docker, you must have the latest [Docker app](https://docs.docker.com/get-docker/) for MacOS, Linux, or Windows installed and running locally.

* Windows users must first install and configure either the WSL 2 or the Hyper-V backend, as outlined in the  [System Requirements for installing Docker Desktop on Windows](https://docs.docker.com/desktop/install/windows-install/#system-requirements).

{: .warning }
Make sure the Docker app is running before proceeding!

* Download [https://raw.githubusercontent.com/swirlai/swirl-search/main/docker-compose.yaml](https://raw.githubusercontent.com/swirlai/swirl-search/main/docker-compose.yaml)

``` shell
curl https://raw.githubusercontent.com/swirlai/swirl-search/main/docker-compose.yaml -o docker-compose.yaml
```

* *IMPORTANT*: To use SWIRL's Real-Time Retrieval Augmented Generation (RAG) in Docker, run the following commands from the Console using a valid OpenAI API key...

For Mac OS or Linux:
``` shell
export MSAL_CB_PORT=8000
export MSAL_HOST=localhost
export OPENAI_API_KEY=<your-OpenAI-API-key>
```

For Windows:
``` shell
set MSAL_CB_PORT=8000
set MSAL_HOST=localhost
set OPENAI_API_KEY=<your-OpenAI-API-key>
```

{: .highlight }
Check out [OpenAI's YouTube video](https://youtu.be/nafDyRsVnXU?si=YpvyaRvhX65vtBrb) if you don't have an OpenAI API Key.

* On MacOS or Linux, run the following command from the Console:

``` shell
docker-compose pull && docker-compose up
```

* On Windows, run the following command from PowerShell:

``` shell
docker compose up
```

After a few minutes, the following or similar should appear:

``` shell
app-1    | Start: celery-worker -> celery -A swirl_server worker ... Ok, pid: 55
app-1    | Start: celery-beats -> celery -A swirl_server beat --scheduler django_celery_beat.schedulers:DatabaseScheduler ... Ok, pid: 81
app-1    | Updating .swirl... Ok
app-1    | 
app-1    |   PID TTY          TIME CMD
app-1    |    55 ?        00:00:05 celery
app-1    |    81 ?        00:00:04 celery
app-1    | 
app-1    | setting up logging...
app-1    | setting up logging DONE
app-1    | You're using version 4.0.0.0 of Swirl, the current version.
app-1    | Command successful!
app-1    | INFO 2025-02-17 15:45:00 cli Starting server at tcp:port=8000:interface=0.0.0.0
app-1    | INFO 2025-02-17 15:45:00 server HTTP/2 support not enabled (install the http2 and tls Twisted extras)
app-1    | INFO 2025-02-17 15:45:00 server Configuring endpoint tcp:port=8000:interface=0.0.0.0
app-1    | INFO 2025-02-17 15:45:00 server Listening on TCP address 0.0.0.0:8000
```

* Open this URL with a browser: <http://localhost:8000> (or <http://localhost:8000/galaxy>)

If the search page appears, click `Log Out` at the top, right. The SWIRL login page will appear:

<img src="images/swirl_40_login.png" alt="SWIRL 4.0 Login" width="300">

* Enter the username `admin` and password `password`, then click `Login`.

* Enter a search in the search box and press the `Search` button. Ranked results appear in just a few seconds:

![SWIRL AI Connect 4.0 Results](images/swirl_40_results.png)

* Click the `Generate AI Insight` button to RAG using the most relevant results. 

{: .warning }
As noted above, if using the Community Edition, you *must* setup OpenAI or Azure/OpenAI prior to executing this step.

![SWIRL AI Connect 4.0 Results with RAG](images/swirl_40_community_rag.png)

* Click the profile avatar in the upper right corner of the Galaxy UI. Then click [Manage SWIRL](http://localhost:8000/swirl/) to explore the rest of SWIRL's features.

* To view the raw result JSON, click `Search` under the API section of the `Manage SWIRL` page linked above, or open <http://localhost:8000/swirl/search/>

The most recent Search object will be displayed at the top. Click on the `result_url` link to view the full JSON Response. For example:

![SWIRL JSON response](images/swirl_results_mixed_1.png)

* Read the [SWIRL User Guide](./User-Guide.html) for additional information.

* To shut down SWIRL:

1.	Via Docker Desktop: 
![Shutdown SWIRL with Docker Desktop](images/shutdown_docker.png)

2.	Press CTRL-C in the terminal window where Docker Compose is running:
![Shutdown SWIRL with Control-C](images/shutdown_ctl_c.png)

3. Execute docker-compose stop from a different terminal:
![Shutdown SWIRL with docker compose in a different window](images/shutdown_compose.png)

{: .warning }
The Docker version of SWIRL AI Connect Community Edition does *not* retain any data or configuration when shut down. 

## Notes

{: .highlight }
SWIRL includes SearchProviders for Google Web (via their Programmable Search Engine offering), Arxiv.org, European PMC, Google News and SWIRL Documentation to get you up and running right away. The credentials for the Google Cloud API are shared with the SWIRL Community for this purpose.

{: .highlight }
Using SWIRL with Microsoft 365 requires installation and approval by an authorized company Administrator. For more information, please review the [M365 Guide](M365-Guide.html) or contact support as noted below. 