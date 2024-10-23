---
layout: default
title: Docker Build
nav_exclude: true
search_exclude: true
sitemap: 'false'
---

# DOCKER BUILD for SWIRL

{: .warning }
The Docker version of SWIRL does *not* retain any data or configuration when shut down!

Please [contact support](mailto:support@swirl.today) for a Docker image suitable for production deployment. 

<br/>

## Install Docker

[https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)

<br/>

## Clone the Repo Branch

```
git clone https://github.com/swirlai/swirl-search
```

Feel free to specify the name of a new directory, instead of using the default (`swirl-search`):

```
git clone https://github.com/swirlai/swirl-search my-directory
```

<br/>

## Setup Container

```
cd swirl-search
docker build . -t swirlai/swirl-search:latest
```

If you cloned to a directory other than `swirl-search`, replace it above.

This command should produce a long response starting with:

```
[+] Building 132.2s (21/21) FINISHED
...etc...
```

If you see any error messages, please [contact support](mailto:support@swirl.today) for assistance.

<br/>

## Start Container

```
docker compose up
```

Docker should respond with the following, or similar:

```
[+] Running 2/2
Network swirl-c_default Created 0.0s
Container swirl-c-app-1 Created 0.0s
Attaching to swirl-search-app-1
```

### Note down the container ID attached, as it will be needed later!

The Container ID in this example is `swirl-c-app-1`. It will be different if you cloned the repo to a different folder.

Moments later, Docker desktop will reflect the running Container:

![SWIRL running in Docker](https://docs.swirl.today/images/swirl_docker.png)

<br/>

## Create Super User Account

```
docker exec -it swirl-search-app-1 python manage.py createsuperuser --email admin@example.com --username admin
```

Again, replace `swirl-search-app-1` with your Container ID if different. 

Enter a new password, twice. If django complains that the password is too simple, type "Y" to use it anyway. 

### Note down the Super User password as it will be needed later!

<br/>

## Load Google PSE SearchProviders

```
docker exec -it swirl-search-app-1 python swirl_load.py SearchProviders/google_pse.json -u admin -p super-user-password
```

Replace `super-user-password` with the password you created in the previous step. Also, replace `swirl-search-app-1` with your container ID if different. 

The script will load all SearchProvider configurations in the specified file at once and confirm.

<br/>

## View SearchProviders

### [http://localhost:8000/swirl/searchproviders/](http://localhost:8000/swirl/searchproviders/)

This should bring up the following, or similar:

![SWIRL SearchProviders, Google PSE - 1](https://raw.githubusercontent.com/wiki/swirlai/swirl-search/images/swirl_sp_pse-1.png)
![SWIRL SearchProviders, Google PSE - 2](https://raw.githubusercontent.com/wiki/swirlai/swirl-search/images/swirl_sp_pse-2.png)

<br/>

## Run a Query!

### [http://localhost:8000/swirl/search/?q=knowledge+management](http://localhost:8000/swirl/search/?q=knowledge+management)

After 5-7 seconds, this should bring up a unified, relevancy ranked result list:

![SWIRL Search Results, Google PSE](https://raw.githubusercontent.com/wiki/swirlai/swirl-search/images/swirl_results_mixed_1.png)

### Congratulations, SWIRL Docker is installed!

<br/>

## Notes

{: .warning }
SWIRL in Docker cannot use localhost to connect to local endpoints!

For example: If you have solr running on localhost:8983, SWIRL will be unable to contact it from inside the Docker container using that URL.

To configure such a source, get the hostname. On OS/X:

```
% hostname
AgentCooper.local
```

In the SearchProvider configuration, replace localhost with the hostname:

```
"url": "http://AgentCooper.local:8983/solr/{collection}/select?wt=json",
```
