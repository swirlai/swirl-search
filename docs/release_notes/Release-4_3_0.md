---
layout: default
title: Release 4.3.0, Enterprise Edition
nav_exclude: true
---

# 🚀 SWIRL Enterprise 4.3 Release Announcement

Team SWIRL is announcing the release of **SWIRL AI Search 4.3, Enterprise Edition.**
  
⭐ PLEASE STAR OUR REPO: [https://github.com/swirlai/swirl-search](https://github.com/swirlai/swirl-search)  
🌐 PLEASE VISIT OUR WEBSITE: [https://www.swirlaiconnect.com/](https://www.swirlaiconnect.com/)  

---

SWIRL 4.3 incorporates Deep Linking of all LLM generated responses, along with user rating support - all directly in the Galaxy UI.
The release also includes advanced Japanese language support.

🔹 **Deep Linking from RAG & Chat to Sources**  
RAG and Chat prompts now provide links directly to the citation for web sources. 


![Deeplinking Result](https://raw.githubusercontent.com/swirlai/swirl-search/main/docs/images/4_3_0-Deeplinking-1.png)
![Deeplinking Source 1](https://raw.githubusercontent.com/swirlai/swirl-search/main/docs/images/4_3_0-Deeplinking-2.png)
![Deeplinking Source 2](https://raw.githubusercontent.com/swirlai/swirl-search/main/docs/images/4_3_0-Deeplinking-3.png)


🔹 **User Ratings for RAG & Chat Responses**  
Users can now provide feedback on Search RAG and Chat Assistant responses directly in the UI.  
These responses are recorded in SWIRL and can be reviewed, reported on and analyzed in the SWIRL Activity Analyzer.

![Response Rating 1](https://raw.githubusercontent.com/swirlai/swirl-search/main/docs/images/4_3_0-Response-rating-1.png)
![Response Rating 2](https://raw.githubusercontent.com/swirlai/swirl-search/main/docs/images/4_3_0-Response-rating-2.png)

🔹 **Advanced Japanese Language Support**  
SWIRL now includes modern Japanese language processing, from query parsing to re-ranking, highlighting, RAG and the AI Search Assistant.
This includes all SWIRL prompts. 

![JA Search RAG](https://raw.githubusercontent.com/swirlai/swirl-search/main/docs/images/4_3_0-JA-search-rag.png)
![JA Assistant](https://raw.githubusercontent.com/swirlai/swirl-search/main/docs/images/4_3_0-JA-assistant.png)

🔹 **New Connectors**  
This release includes support for querying M-Files, Better Regulation, custom Sharepoint collections and Outline Team Knowledge Base. 

## New features

- **High Relevancy Option:** Preserve native Elastic/OpenSearch ranking when results only come from that source  
- **Logs Download:** Celery-Worker and Django logs are now downloadable from the Django Admin
- **MappingResultProcessor Enhancements:** Unknown keys are now preserved in payloads, with improved handling of quotes in mappings 
- **PDF Improvements:** Alternative parser for PDF tables added
- **Assistant Query Support:** the SWIRL AI Assistant can now query using SQL, Mongo QL, Elastic/OpenSearch and many other languages

## Improvements

- **Galaxy UI**  
  - RAG options hidden if no AIProvider is active
  - Exported Chat PDFs now display the SWIRL logo
  - Improved feedback when no results are relevant enough to trigger RAG
  - Cookie-consent banner is now optional
  - Fixed relevancy star assignment in non-Relevancy mixers

- **RAG / Search**  
  - Follow-up questions now returned as **Optional AI Instructions** instead of firing a new search
  - RoundRobinThreshold option fixed to honor configured threshold
  - RAG processor now handles SearchProvider renames gracefully 

- **Technical Improvements**  
  - Fixed SharePoint/OneDrive link issue with pound-signs  
  - Validated with **Apache Tika 3.2.1** 
  - Replaced Websocket interface for Search RAG with REST

## Upgrading

⚠️ Version 4.3 includes **Django migrations**.  Please see the [Database Migrations](../Admin-Guide.md#database-migration) documentation for details.

---

## Documentation

📘 SWIRL’s [documentation site](../index) has been updated reflecting the new features above.
