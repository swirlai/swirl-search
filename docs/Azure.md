---
layout: default
title: Azure Marketplace Guide
nav_order: 10
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

# Azure Marketplace Guide

{: .warning }
The user performing this installation must be an authorized M365 tenant Administrator. 

* [Visit the offer page](https://go.swirl.today/azure)

* Click the "Get It Now" button, and on the following screen, select a "Plan" option and click the blue "Create" button.
![Azure Marketplace Create Screenshot](images/Azure_Marketplace-1.png)

* Click into the "Basics" tab. Select an Azure "Subscription", specify a new "Resource Group" specifically for the Swirl Managed App, select a Region, and provide an Application Name of your choosing.  The "Managed Resource Group" value should already be provided.  Click the "Next" button to save this configuration.
![Azure Marketplace Basics Screenshot](images/Azure_Marketplace-3.png)

{: .highlight }
Make note of the Application Name value as it will be used in the next steps!

* Click into the "App Registration" tab and read the instructions provided there.
![Azure Marketplace Select Screenshot](images/Azure_Marketplace-2.png)

* Download the script using the link at the bottom of the "App Registration" tab and run it in the target installation tenant.  The "Application Name" value from above is required in some of the script inputs.
```
Enter the FQDN for the Swirl app: <your-application-name>.<your-domain>
Enter your Azure Tenant ID: <your-tenant-id>
Enter your Azure Subscription ID: <your-subscription-id>
Enter your name of the App to register (no spaces, use _ or - for multiword): <your-application-name>
Enter your DNS Zone Resource Group: <your-DNS-zone-resource-group>
```

{: .highlight }
Save the script output as it will be used in for the next step!

* Click into the "Deployment Configuration" tab. Fill out the form, including all required values, using the values reported by the script from the previous step.
![Azure Marketplace Configure Screenshot](images/Azure_Marketplace-4.png)

| Field | Explanation | 
| ----- | ----------- | 
| Environment | Your "Application Name" from the Basics tab. |
| Client ID | Value provided by the `swirl_appreg.sh` script |
| Object ID | Value provided by running the `az` command found in the tooltips: `az ad signed-in-user show --query id -o tsv` |
| User Identity Name | Value provided by the `swirl_appreg.sh` script |
| Azure DNS Zone | The existing DNS Zone the application will be deployed in (e.g.: `example.com`) |
| DNS Zone Resource Group | Value required for Swirl to automatically update the DNS Zone swirl will be registered in. Search your Azure DNS Zones for the appropriate Zone name to identify the the Resource Group this `zonefile` is associated with. |
| App Endpoint Prefix | Your "Application Name" from the Basics tab. |
| OpenAI API Key | Allows Swirl to connect to and use an OpenAI account via the API. | 
| App Admin User Email | The email of the user registering/deploying this application |

* When all of the above steps are completed, click into the "Review + create" tab and review your configuration.  Click the "Create" button to complete the setup and install Swirl!
![Azure Marketplace Confirm Screenshot](images/Azure_Marketplace-5.png)

# Questions

If you encounter errors or warnings, please contact support for assistance (see below).
