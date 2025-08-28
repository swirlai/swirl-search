---
layout: default
title: Release 3.9.0, Enterprise Edition
nav_exclude: true
---

# 🚀 SWIRL Enterprise 3.9 Release Announcement

Team SWIRL is announcing the release of **SWIRL AI Search 3.9, Enterprise Edition.**
  
⭐ PLEASE STAR OUR REPO: [https://github.com/swirlai/swirl-search](https://github.com/swirlai/swirl-search)  
🌐 PLEASE VISIT OUR WEBSITE: [https://www.swirlaiconnect.com/](https://www.swirlaiconnect.com/)  

---

SWIRL 3.9 adds **LLM-generated follow-up questions** in Co-Pilot, **expanded user context** for personalized responses, a revised **Box** connector with full-text fetch & snippet extraction for better re-ranking, and a new **Datadog** connector for recent logs. 

🔹 **Co-Pilot: LLM-Generated Follow-Up Questions**  

![SWIRL 3.9 Co-Pilot generating follow up questions](https://media.licdn.com/dms/image/v2/D4E12AQFugJ8VtQssBw/article-inline_image-shrink_1500_2232/article-inline_image-shrink_1500_2232/0/1731724279189?e=1761782400&v=beta&t=3wV-dNgW-hcM1H1Ts1Lwx-p16FwFGx5LDitUag50ycY)

Just click the link to get the answer!

![SWIRL 3.9 Co-Pilot generating follow up questions](https://media.licdn.com/dms/image/v2/D4E12AQEp6Pr7mqrReA/article-inline_image-shrink_1500_2232/article-inline_image-shrink_1500_2232/0/1731724393627?e=1761782400&v=beta&t=ZvR8Dw061r-URMNifQ5z1Tq_GbsrORSg9Fo3ZaFtbks)

🔹 **Box Connector: Full-Text Fetch & Snippet Extraction**  
The revised Box connector retrieves full text, extracts snippets, and feeds relevant text into re-ranking. Click **Generate AI Response** to summarize via RAG when needed.

![SWIRL 3.9 and Box](https://media.licdn.com/dms/image/v2/D4E12AQFR2o9oKLboKw/article-inline_image-shrink_1000_1488/article-inline_image-shrink_1000_1488/0/1731724440666?e=1761782400&v=beta&t=tKsIITxyBXWuLU42rt6CxdqNdJVCPqvWduz3DTyDgCM)

🔹 **New Connector: Datadog (Recent Logs)**  
Query recent log files directly from Datadog to investigate errors and operational signals.

![SWIRL 3.9 and Data Dog](https://media.licdn.com/dms/image/v2/D4E12AQGZ0Ae3r2oUSQ/article-inline_image-shrink_1500_2232/article-inline_image-shrink_1500_2232/0/1731724716643?e=1761782400&v=beta&t=KByNhCvvzZLwahwGSrh1I0nVPGxT1BGE8bQ4-0NJtMY)

## New features

- **Co-Pilot Follow-Ups:** LLM-generated follow-up questions with one-click execution  
- **Box Full-Text Pipeline:** Automatic full-text fetch, snippet extraction, and relevance-aware re-ranking  
- **Datadog Connector:** Query recent logs as a federated source  
- **Personalized Context:** Optional user metadata (name, role, location, preferences) + current date for tailored results  
- **Connector Enhancements:** BigQuery, Elasticsearch, OpenSearch, MongoDB, PostgreSQL, SQLite updates  
- **Reader LLM → Tika 3.0**  
- **Python 3.12.6 Certification**

## Improvements

- **Galaxy UI**  
  - More graceful handling of **longer result titles** and **window resizing**  
  - New **“Dev”** tag to search across development-centric SearchProviders  
  - **Unselect All** button when using **Select Items** for RAG (from Community)

- **RAG / Search**  
  - **Elastic SearchProvider** now returns the configured number of results  
  - Improved handling of **citations** and **follow-up questions** in RAG

- **Technical Improvements**  
  - **Database schema changes** are now managed via **Django migrations** (version-controlled and shipped with releases)  
  - **OneDrive**: removed default `FILE_SYSTEM` directive; **Outlook Email** result processors reordered for better thread handling  
  - **SWIRL AI Connect** validated on **Python 3.12.6** (Community parity)

## Upgrading

⚠️ Version 3.9 includes **Django migrations**. After updating, apply migrations (e.g., `python manage.py migrate`) and follow standard upgrade steps. For assistance, please contact support.

---

## Documentation

📘 SWIRL’s [documentation site](../index) has been updated reflecting the new features above.
