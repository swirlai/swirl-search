---
layout: default
title: Release 4.4.1, Enterprise Edition
nav_exclude: true
---

# 🚀 SWIRL Enterprise 4.4.1 Release Notes

Team SWIRL is announcing the release of **SWIRL Enterprise, Version 4.4.1**.

⭐ PLEASE STAR OUR REPO: <https://github.com/swirlai/swirl-search><br/>
🌐 PLEASE VISIT OUR WEBSITE: <https://www.swirlaiconnect.com>

<hr style="border:0;height:2px;background:#000;margin:16px 0;"/>

This version resolves issues found with Version 4.4.0. 


# New Features

- Connect ALl now available in the Search Assistant

- New Export as PDF option for search results

- New SORT_PAYLOAD option for SearchProvider result mappings, with default sorting now following field order

# Improvements

- The iManage SearchProvider has been updated

- Certificate renewal in the Azure Marketplace has been improved

- Added django.log to the logs download for Azure Marketplace deployments

- Fixed celry_metrics issues impacting auto-scaling

- Updated preloaded periodic task list to split celery worker queues

- Galaxy UI support for narrower screens

- Eliminated unnecessary startup warnings

- Improved service startup ordering and port checking

- Verified SWIRL on Python 3.13.11

# Upgrading

⚠️ Version 4.4.1 includes **Django migrations**.  Please see the [Database Migrations](../Admin-Guide#database-migration) documentation for details.

---

## Documentation

📘 SWIRL’s [documentation site](../index) has been updated reflecting the new features above.

