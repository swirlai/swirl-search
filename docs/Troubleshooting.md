---
layout: default
title: Troubleshooting
nav_order: 16
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

# Troubleshooting SWIRL

{: .warning }
This document applies to all SWIRL Editions. 

## Understanding .swirl

The `swirl.py` control script writes the list of services and their associated pids to a file: `.swirl`

Here is an example of a `.swirl` file for a fully running system:

``` shell
{"django": 26391, "celery-worker": 26424}
```

This file is read by the `status` and `stop` commands. Both commands invoke `ps -p` with the pids for the services to determine if they are actually running and display this information for you.

If you `start` or `stop` individual services, the `.swirl` file should only have the names and pids for running services. 

In the event that the `.swirl` file is out of sync with the running processes, you may delete it, or edit it to match the
actual running processes. Be sure to manually delete any running processes. 

## Finding SWIRL processes

You can find the SWIRL procsses as follows:

On OS/X or Linux:

``` shell
ps -ef | grep daphne
ps -ef | grep celery
ps -ef | grep redis
```

## Logs

All SWIRL services write log files in the `logs/` folder under `swirl-search`.

Here's what to expect in each:

| Logfile | Details | Notes | 
| ---------- | ---------- | ---------- ||
| logs/django.log | Contains the log of the Django container, which includes all HTTP activity API calls. | Not involved in federation |
| logs/celery-worker.log | Contains the log of Celery tasks | Very involved in federation, look for detailed information regarding errors in `search.status` or partial results |
| logs/celery-beats.log | Contains the log of the celery-beats service, which is only used by the Search Expiration and Subscription Services | Look here for issues with subscription or expiration not working | 

## Viewing Logs

From the SWIRL root directory, try running:

``` shell
python swirl.py logs/
```

This will show you the collected, latest output of all logs, continuously.

SWIRL outputs a single log entry with each request at the default log level INFO:

``` shell
2023-08-02 10:49:09,466 INFO     admin search 452 FULL_RESULTS_READY 32 2.2
```

Detailed logging is available in Debug mode: restart SWIRL with the `--debug` flag to enable (or edit the `settings.py` file as outlined below).

## Reporting a Problem

If you find a problem, please [contact support](#support) via email, or on slack, for the fastest response. 