![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# SWIRL SEARCH 1.1 DOCKER SETUP

:warning: Warning: as of the current version of the containerization-wip branch, the SWIRL database is instantly and unrecoverably deleted if you shut down the container.

<br/>

## Install Docker

[https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)

## Clone the Repo Branch

```
sid@AgentCooper code % git clone -b containerization-wip https://github.com/sidprobstein/swirl-search swirl-c
Cloning into 'swirl-c'...
remote: Enumerating objects: 417, done.
remote: Counting objects: 100% (417/417), done.
remote: Compressing objects: 100% (389/389), done.
remote: Total 417 (delta 194), reused 246 (delta 27), pack-reused 0
Receiving objects: 100% (417/417), 15.14 MiB | 7.21 MiB/s, done.
Resolving deltas: 100% (194/194), done.
```

Feel free to replace swirl-c with your choice of folder name.

<br/>

## Setup Container

```
cd swirl-c
docker build . -t swirl-search:latest
```

If you cloned to a directory other than swirl-c, replace it above.

This command should produce a long response starting with:

```
[+] Building 132.2s (21/21) FINISHED
...etc...
```

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
Attaching to swirl-c-app-1
```

### Note down the container ID attached, as it will be needed later!

The container ID in this example is swirl-c-app-1. It will be different if you cloned the repo to a different folder.

Moments later, Docker desktop will reflect the running container:

![SWIRL running in Docker](/docs/images/swirl_docker.png)

<br/>

## Create Super User Account

```
docker exec -it swirl-c-app-1 python manage.py createsuperuser --email admin@example.com --username admin
```

Again, replace swirl-c-app-1 with your container ID if different. 

Enter a new password, twice. If django complains that the password is too simple, type "Y" to use it anyway. 

### Note down the super user password as it will be needed later!

<br/>

## Load Google PSE SearchProviders

```
docker exec -it swirl-c-app-1 python scripts/swirl_load.py SearchProviders/google_pse.json -u admin -p super-user-password
```

Replace super-user-password with the password you created in the previous step. 
Also, replace swirl-c-app-1 with your container ID if different. 

This should produce the following:

```
##S#W#I#R#L##1#.#3##############################################################
swirl_load.py: fed 3 into SWIRL, 0 errors
```

## View SearchProviders

### [http://localhost:8000/swirl/searchproviders/](http://localhost:8000/swirl/searchproviders/)

This should bring up the following, or similar:

![SWIRL Search Provider List, Google PSE](/docs/images/pse/swirl_spl_list.png)

<br/>

:key: Important note: you cannot use localhost when configuring endpoints using SWIRL Docker!!

For example if you have solr running on localhost:8983, SWIRL will be unable to contact it
from inside the docker container. 

On OS/X go to the shell and type hostname to get this, e.g.

```
sid@AgentCooper solr-8.11.1 % hostname
AgentCooper.local
```

In the SearchProvider, replace localhost with the hostname, and it will work:

```
"url": "http://AgentCooper.local:8983/solr/{collection}/select?wt=json",
```

<br/>

## Run a Query!

### [http://localhost:8000/swirl/search/?q=search+engine](http://localhost:8000/swirl/search/?q=search+engine)

After 5-7 seconds, this should bring up a unified, relevancy ranked result list:

![SWIRL Search Results, Google PSE](/docs/images/pse/swirl_results_mixed_1.png)

<br/>

### Congratulations, SWIRL docker is installed!

<br/>

:warning: Warning: as of the current version of the containerization-wip branch, the SWIRL database is instantly and unrecoverably deleted if you shut down the container.

## Documentation

* [User Guide](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide)

<br/>

# Support

:small_blue_diamond: [Create an Issue](https://github.com/sidprobstein/swirl-search/issues) if something doesn't work, isn't clear, or should be documented - we'd love to hear from you!

:small_blue_diamond: Paid support and consulting are available... [contact SWIRL](mailto:swirl@probstein.com) for more information.
