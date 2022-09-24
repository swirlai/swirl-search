![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# DOCKER SETUP for SWIRL 1.3

:warning: Warning: when using docker the SWIRL database is instantly and irrevocably deleted upon container shutdown!

Please [contact support](#support) for a docker image suitable for production deployment. 

<br/>

## Install Docker

[https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)

## Clone the Repo Branch

```
git clone https://github.com/sidprobstein/swirl-search
```

Feel free to specify the name of a new folder, instead of using the default (swirl-search):

```
git clone https://github.com/sidprobstein/swirl-search my-folder
```

<br/>

## Setup Container

```
cd swirl-search
docker build . -t swirl-search:latest
```

If you cloned to a directory other than swirl-search, replace it above.

This command should produce a long response starting with:

```
[+] Building 132.2s (21/21) FINISHED
...etc...
```

If you see any error messages, please [contact support](#support) for assistance.

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

The container ID in this example is swirl-c-app-1. It will be different if you cloned the repo to a different folder.

Moments later, Docker desktop will reflect the running container:

![SWIRL running in Docker](/docs/images/swirl_docker.png)

<br/>

## Create Super User Account

```
docker exec -it swirl-search-app-1 python manage.py createsuperuser --email admin@example.com --username admin
```

Again, replace swirl-search-app-1 with your container ID if different. 

Enter a new password, twice. If django complains that the password is too simple, type "Y" to use it anyway. 

### Note down the super user password as it will be needed later!

<br/>

## Load Google PSE SearchProviders

```
docker exec -it swirl-search-app-1 python scripts/swirl_load.py SearchProviders/google_pse.json -u admin -p super-user-password
```

Replace super-user-password with the password you created in the previous step. 
Also, replace swirl-search-app-1 with your container ID if different. 

This should produce the following:

```
##S#W#I#R#L##1#.#3##############################################################
swirl_load.py: fed 3 into SWIRL, 0 errors
```

## View SearchProviders

### [http://localhost:8000/swirl/searchproviders/](http://localhost:8000/swirl/searchproviders/)

This should bring up the following, or similar:

![SWIRL Search Provider List, Google PSE](/docs/images/pse/swirl_spl_list.png)

## Run a Query!

### [http://localhost:8000/swirl/search/?q=search+engine](http://localhost:8000/swirl/search/?q=search+engine)

After 5-7 seconds, this should bring up a unified, relevancy ranked result list:

![SWIRL Search Results, Google PSE](/docs/images/pse/swirl_results_mixed_1.png)

<br/>

### Congratulations, SWIRL docker is installed!

## Notes

:warning: Warning: when using docker the SWIRL database is instantly and irrevocably deleted upon container shutdown!

Please [contact support](#support) for a docker image suitable for production deployment. 

<br/>

:info: Important: SWIRL in Docker cannot use localhost to connect to local endpoints!

For example: if you have solr running on localhost:8983, SWIRL will be unable to contact it from inside the docker container using that URL.

To configure such a source, get the hostname. On OS/X:

```
% hostname
AgentCooper.local
```

In the SearchProvider, replace localhost with the hostname:

```
"url": "http://AgentCooper.local:8983/solr/{collection}/select?wt=json",
```

<br/>

## Documentation

* [User Guide](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide)

<br/>

# Support

:small_blue_diamond: [Create an Issue](https://github.com/sidprobstein/swirl-search/issues) if something doesn't work, isn't clear, or should be documented - we'd love to hear from you!

:small_blue_diamond: Paid support and consulting are available... [contact SWIRL](mailto:swirl@probstein.com) for more information.
