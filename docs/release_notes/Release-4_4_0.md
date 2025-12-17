---
layout: default
title: Release 4.3.0, Enterprise Edition
nav_exclude: true
---

# 🚀 SWIRL Enterprise 4.4 Release Notes

Team SWIRL is announcing the release of **SWIRL AI Search 4.4, Enterprise Edition**.

⭐ PLEASE STAR OUR REPO: https://github.com/swirlai/swirl-search
🌐 PLEASE VISIT OUR WEBSITE: https://www.swirlaiconnect.com/

---

SWIRL 4.4 includes file location and holding for deep, detailed, ongoing conversations, plus updated PII redaction, improved advanced querying support and usability fixes.

# New features

- The AI Search Assistant can now locate and hold files for an ongoing conversation.

![](TBD)

- PII redaction via Microsoft Presidio is now supported for queries, results, and RAG responses.

![](TBD)

- Advanced German query processing is now supported, including de-compounding of words.
- New connector for SpiraPlan TBD

# Improvements

- The AI Search Assistant has improved tool calling for SQL and sources that require complex query languages.

![](TBD)

- The list of preloaded SearchProviders has been re-organized to improve clarity.

![](TBD)

- Each SearchProvider can now specify a unique timeout... TBD

![](TBD)

- The RequestGet and RequestPost connectors have been updated to support 429 back-off
- The Galaxy Source Selector now supports partial source selection as per the CUA protocol.
- Galaxy's handling of LLM-generated markup, late-arriving results and author display has been improved.
- Japanese tokenization & stemming have been improved.
- Celery workers have been re-organized for easier scaling.
- The Manage SWIRL link is now restricted to admins & superusers.
- Updated Docker base to Debian Trixie and validated Python 3.13.9. 
- Upgraded Galaxy UI to Angular 20 and updated Yarn Berry. 

# Upgrading

⚠️ Version 4.3 includes **Django migrations**.  Please see the [Database Migrations](../Admin-Guide#database-migration) documentation for details.

---

## Documentation

📘 SWIRL’s [documentation site](../index) has been updated reflecting the new features above.

