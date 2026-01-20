---
layout: default
title: Troubleshooting
nav_order: 26
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

<span class="big-text">Troubleshooting SWIRL</span><br/><span class="med-text">Community Edition | Enterprise Edition</span>

---

# Understanding `.swirl`

The `swirl.py` control script tracks running services and their process IDs (PIDs) in a file called `.swirl`.

## Example `.swirl` File

For a fully running system, the file looks like this:

```shell
{"django": 26391, "celery-worker": 26424}
```

## How `.swirl` Works

- The `.swirl` file is **read** by the `status` and `stop` commands to check running processes.
- These commands use `ps -p` with stored PIDs to determine if services are actually running.

If you manually `start` or `stop` services, the `.swirl` file updates accordingly.

## Fixing Out-of-Sync `.swirl` Files

If the `.swirl` file **does not match** actual running processes:

1. **Delete** the file (`rm .swirl`).
2. **Restart SWIRL** to regenerate it.
3. **Manually stop any remaining SWIRL processes** before restarting.

# Finding SWIRL Processes

To check for running SWIRL processes, use the following commands:

### On macOS or Linux:

```shell
ps -ef | grep daphne
ps -ef | grep celery
ps -ef | grep redis
```

# Logs

All SWIRL services write logs to the `logs/` folder inside `swirl-search`.

### Log Files Overview

| Logfile | Description | Notes |
|---------|-------------|-------|
| **logs/django.log** | Logs **Django container activity**, including all API calls. | Not involved in query federation. |
| **logs/celery-worker.log** | Logs **Celery tasks**, including search federation processes. | Look for errors in `search.status` or partial results. |
| **logs/celery-beats.log** | Logs **Celery Beats service**, used for **Search Expiration** and **Subscription Services**. | Check here if subscriptions or expirations are not working. |

# Viewing Logs

To continuously view logs, run:

```shell
python swirl.py logs/
```

This command displays **live log output** from all SWIRL services.

## Example Log Entry (INFO Level)

```shell
2023-08-02 10:49:09,466 INFO     admin search 452 FULL_RESULTS_READY 32 2.2
```

For **detailed logging**, enable **Debug mode**:

- Restart SWIRL with the `--debug` flag.
- Alternatively, update the `settings.py` file (see the Developer Guide for details).
