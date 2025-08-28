---
layout: default
title: Release 4.1.0, Enterprise Edition
nav_exclude: true
---

# 🚀 SWIRL Enterprise 4.1 Release Announcement

Team SWIRL is announcing the general availability of **SWIRL AI Search 4.1, Enterprise Edition.**
  
⭐ PLEASE STAR OUR REPO: [https://github.com/swirlai/swirl-search](https://github.com/swirlai/swirl-search)  
🌐 PLEASE VISIT OUR WEBSITE: [https://www.swirlaiconnect.com/](https://www.swirlaiconnect.com/)  

---

SWIRL 4.1 delivers upgraded LLM and Assistant interfaces - including better citation handling, a new **SearchProvider config block** that accepts JSON, stronger **SQL** & formatted-query support and **AI Provider fallback** for resilient AI operations. 

We’ve also polished the Galaxy UI, added a quick **DESELECT ALL → SELECT ALL** toggle:

![SWIRL Galaxy UI showing select all toggle](../images/4_1_0-SelectAll.png)

## New features

- **RAG & Assistant Interfaces:** Enhanced citation handling; refactored Assistant with new **SWIRL Search** syntax; improved **SQL** and other formatted-query language support  
- **AI Provider Fallback:** Automatic failover across AIProviders configured for the same role (e.g., “rag”)  
- **SearchProvider Config Block:** Supports arbitrary **JSON** for advanced source configuration
- **Crontab Persistence:** All crontab settings now use database defaults and persist across Docker restarts  
- **Manage SWIRL Setup Guide:** Built-in onboarding guide for Enterprise deployments

## Improvements

- **Galaxy UI**  
  - Numerous fixes and refinements  
  - **SWIRL version** now appears in the **User Profile** menu  
  - **DESELECT ALL** now toggles to **SELECT ALL** after click, enabling quick reset of selections  
  - Full **unit test suite** implemented; unused components and services removed

- **RAG / Search**  
  - More robust citation handling during RAG  
  - Expanded support for structured query inputs (including **SQL**)  
  - **arXiv SearchProvider** now quotes the user’s search terms by default for more precise results

- **Technical Improvements**  
  - Validated on **Python 3.12.9**  
  - Updated `docker-compose.yaml` to stream **celery-worker logs** to the Terminal output  

## Upgrading

⚠️ Version 4.1 does not require database migration.  

---

## Known issues

- Clicking a Microsoft Teams result may show:  
  `We cannot take you to that message because it's in a chat you're not in.`  
  Ensure the Microsoft Teams app is open and you are authenticated before clicking Teams links.  
- Creating searches from a browser with `q=` can sometimes create two Search objects due to browser prefetch / predictive services. If this is undesirable, disable Chrome prediction se
