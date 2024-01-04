---
layout: default
title: Azure Marketplace Installation Guide
nav_order: 8
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

# Azure Marketplace Installation Guide

:warning: The user performing this installation must be an authorized M365 tenant Administrator. 

* [Visit the offer page](https://go.swirl.today/azure)

* Click the "Get It Now" button. The following screen, or similar, should appear:

![Azure Marketplace Create Screenshot](https://swirl.youtrack.cloud/api/files/8-754?sign=MTcwNDQxMjgwMDAwMHwxLTF8OC03NTR8ZkFuR0l4WWdxbmxpOXh0NVZiN092VVZrVTMzTnNfRTgtQjZmTUEtdmIyRQ0K&updated=1703880211226)

* Select a pricing plan and click the blue "Create" button. The following screen, or similar, should appear:

![Azure Marketplace Select Screenshot](https://swirl.youtrack.cloud/api/files/8-757?sign=MTcwNDQxMjgwMDAwMHwxLTF8OC03NTd8aURlbkRfRHBlckpyZjdkdzVIS0lnMk1nUDZfclJ2QVU2REtROWZiR2ZWVQ0K&updated=1703880211483)

* Select an Azure subscription, and optionally specify the Resource Group, Region, Application Name and Manged Resource Group name. Then click on the "App Registration" tab, and the following screen, or similar, should appear:

![](https://swirl.youtrack.cloud/api/files/8-756?sign=MTcwNDQxMjgwMDAwMHwxLTF8OC03NTZ8VWNTb0RqUzFMbTJtSWlwbktGOTAyZTlzSUZfVXJOZldPN1NDVkJyalhoZw0K&updated=1703880211347)

* Download the script using the link at the bottom of the page. Run the script in the target installation tenant. Save the output, as it will be required for the next step. Click "Deployment Configuration" when the script has run successfully. The following screen, or similar, should appear:

![Azure Marketplace Configure Screenshot](https://swirl.youtrack.cloud/api/files/8-758?sign=MTcwNDQxMjgwMDAwMHwxLTF8OC03NTh8TTVoa3lQWHh2NW5GVUVTR0ItdEJQLWxTbGg0eGE2RWdkaU9abHNrNU9mbw0K&updated=1703880211486)

* Fill out the form, including all required values reported by the script from the previous stage. 

| Field | Explanation | 
| ----- | ----------- | 
| Environment | Descriptive name to identify the indented deployment release such as dev, testing, qa or production |
| Client ID | Value provided by the swirl_appreg.sh script |
| Object ID | Run the az command found in the tooltips: `az ad signed-in-user show --query id -o tsv` |
| User Identity Name | Value provided by the swirl_appreg.sh script |
| Azure DNS Zone | The existing DNS zone the application will be deployed in (ex: example.com) |
| DNS Zone Resource Group | Value required for Swirl to automatically update the DNS Zone swirl will be registered in. Search your Azure DNS Zones for the appropriate zone name to identify the the Resource Group this zonefile is associated with. |
| App Endpoint Prefix | The DNS A Record name of the host where Swirl will be deployed (ex: swirl.example.com) |
| OpenAI API Key | Allows Swirl to connect and use an OpenAI account via the API | 
| App Admin User Email | The email of the user registering/deploying this application |

When finished click the "Review + create" tab. The following screen should appear:

![Azure Marketplace Confirm Screenshot]()

If you encounter errors or warnings, please [contact support](#support) for assistance.
