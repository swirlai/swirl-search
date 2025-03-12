---
layout: default
title: Microsoft 365 Guide
nav_order: 14
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

<span class="big-text">Microsoft 365 Guide</span><br/><span class="med-text">Community Edition | Enterprise Edition</span>

---

This guide explains how to integrate SWIRL with an existing **Microsoft 365 (M365) tenant**. It is intended for **M365 administrators** who have permission to **register new applications** in the **Azure Portal**.  

Administrators may also need to **grant API permissions** so users can **query their personal M365 content** through SWIRL.

# Register a New App in Azure Portal

To connect **SWIRL** to an **M365 tenant**, you must **register and configure a new App** in the **Azure Portal**.

Once registered, the App allows:

- **User authentication via OIDC**
- **Personal M365 content searches using OAuth2 permission consent**

## Before You Begin

Ensure you have the following details about your **SWIRL deployment**:

- **`swirl-host`** – The **fully qualified domain name** of your SWIRL instance.  
- **`swirl-port`** – The **port SWIRL runs on** (**only needed** if different from the default).  

Example:  
If your deployment is **`search.swirl.today`**, the `swirl-host` is **`search.swirl.today`**.

**HTTPS Requirement**

To use **OIDC** and **OAuth2**, your deployment **must use** `https`, except when using `localhost`, where `http://` is allowed.  

**Single Page Applications and Web Protocols** require `https://` for fully qualified domains.

## Getting Started

1. **Log in to the Azure Portal**: [https://portal.azure.com](https://portal.azure.com/)

2. In the **search bar**, type: **`app registrations`**, then select **"App registrations"** under **Services**.

   ![Azure find app registration](images/Azure_find_app_reg.png)

## Create the New App

1. On the **"App registrations"** page, click **`New registration`**:

   ![Azure New Registration](images/Azure_new_registration.png)

2. On the **"Register an application"** page:

   - **Name** → Enter a name for the App (e.g., **`SWIRL App`**).
   - **Supported account types** → Select:  
     `Accounts in this organizational directory only (MSFT only - Single tenant)`.
   - **Add a "Redirect URI"** for a Web application:
     - **Platform**: `Web`
     - **Value**: `https://<swirl-host>[:<swirl-port>]/swirl/microsoft-callback`.

3. Click **`Register`** to create the application.

   ![Azure App Registration](images/Azure_app_registration.png)

4. The **"Overview"** page for the newly created App should look similar to this:

   ![Azure App Details](images/Overview_to_authentication.png)

## Configure Redirect URIs for a Single Page Application

1. Navigate to the **"Authentication"** page:

   ![Click on Authentication](images/Overview_to_authentication.png)

2. Click **`Add a platform`** and select **"Single Page Application"**:

   ![Single Page Application Protocol](images/Add_platform_single_page.png)

3. **Add the OIDC Callback URL**:

   ![Add OIDC Callback URL](images/Add_OIDC_Callback.png)

4. **Add the Microsoft OAuth2 Callback URLs**:

   ![Add OAUTH Callback URL 1](images/Add_OAUTH_Callback_1.png)

   ![Add OAUTH Callback URL 2](images/Add_OAUTH_Callback_2.1.png)

5. Return to the **"Overview"** page:

   ![Return to Overview 1](images/Return_to_Overview_1.png)

# Add App API Permissions

## Assign the Necessary Permissions

1. In the left column, select **"API permissions"**, then click **`Add a permission`**:

   ![Azure Add Permissions 1](images/Azure_add_permissions_1.png)

2. In the **"Request API permissions"** panel that opens:
   - Select the **"Microsoft APIs"** tab (at the top).
   - Click the **"Microsoft Graph"** button.
   - Click the **"Delegated permissions"** button.

   ![Azure Add Permissions 2](images/Azure_add_permissions_2.png)

3. In the **search box**, enter and select each of the following permissions, then click **`Add permissions`**:

   ![Azure Add Permissions 4](images/Azure_add_permissions_4.png)

4. **Required Permissions:**

   - `Calendars.Read`
   - `ChannelMessage.Read.All`
   - `Directory.Read.All`
   - `email`
   - `Chat.Read`
   - `Files.Read.All`
   - `profile`
   - `Mail.Read`
   - `offline_access`
   - `Sites.Read.All`
   - `User.Read`

## Admin Consent for Permissions

1. After adding the permissions, click **`Grant admin consent for MSFT`** under **"Configured permissions"**:

   ![Azure Add Permissions 3](images/Azure_add_permissions_3.png)

2. Confirm by selecting **"Yes"**:

   ![Azure Add Permissions 5](images/Azure_add_permissions_5.png)

3. The **Configured permissions** section should now display all granted permissions:

   ![Azure Add Permissions 6](images/Azure_add_permissions_6.png)

# Generate a Client Secret

1. In the left sidebar, select **"Certificates & secrets"**, then click **`New client secret`**:

   ![Azure Client Secret 1](images/Azure_client_secret_1.png)

2. In the **"Add a client secret"** panel:
   - Enter a **`Description`** for the new secret.
   - Select an **`Expires`** time range for the secret.

   ![Azure Client Secret 2](images/Azure_client_secret_2.png)

3. Click **`Add`**. The **"Certificates & secrets"** page will now display a new **Client secret** entry.

   ![Azure Client Secret 3](images/Azure_client_secret_3.png)

{: .warning }
**Once the secret is created, copy the value immediately!**  It will be **hidden permanently** once you leave this page.

# Configure OIDC and OAUTH2 in the SWIRL Client and Server

In the following sections, you will configure **OIDC and OAuth2** for SWIRL. Locate the following values in your **Azure App Registration**:

- **`<application-id>`**  
- **`<tenant-id>`**  
- **`<secret-value>`**  
- **`<server-authentication-callback-url>`**  
- **`<client-authentication-callback-url>`**  
- **`<client-authorization-callback-url>`**  

### Finding These Values in Azure

- **Application & Tenant IDs**:

  ![Azure App and Tenant Ids](images/Show_IDs_in_Overview.png)

- **Client Secret Value**:

  ![Azure Secret Value](images/Azure_secret_value.png)

- **Callback URLs**:

  ![Azure Callback URLs](images/Show_Callback_Urls.png)

## Updating the SWIRL `.env` File

Edit the **`.env`** file (or `.env.docker` for Docker installations) and add the following:

```shell
MICROSOFT_CLIENT_ID='' # deprecated
MICROSOFT_CLIENT_SECRET='' # deprecated
MICROSOFT_REDIRECT_URI='' # deprecated
OIDC_RP_CLIENT_ID='<application-id>'
OIDC_RP_CLIENT_SECRET='<secret-value>'
OIDC_OP_AUTHORIZATION_ENDPOINT='https://login.microsoftonline.com/<tenant-id>'
OIDC_OP_TOKEN_ENDPOINT='https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token'
OIDC_OP_USER_ENDPOINT='https://graph.microsoft.com/oidc/userinfo'
OIDC_RP_SIGN_ALGO='RS256'
OIDC_OP_JWKS_ENDPOINT='https://login.microsoftonline.com/<tenant-id>/discovery/v2.0/keys'
LOGIN_REDIRECT_URL='/swirl'
LOGOUT_REDIRECT_URL='/swirl'
OIDC_USERNAME_ALGO='swirl.backends.generate_username'
OIDC_STORE_ACCESS_TOKEN='True'
OIDC_STORE_ID_TOKEN='True'
OIDC_AUTHENTICATION_CALLBACK_URL='<server-authentication-callback-url>'
```

## Updating the Client Configuration

Edit the `static/api/config/default` file:

```json
  "msalConfig": {
    "auth": {
      "clientId": "<application-id>",
      "authority": "https://login.microsoftonline.com/<tenant-id>",
      "redirectUri": "<client-authorization-callback-url>"
    }
  },
  "oauthConfig": {
    "issuer": "https://login.microsoftonline.com/<tenant-id>/v2.0",
    "redirectUri": "<client-authentication-callback-url>",
    "clientId": "<application-id>",
    "scope": "openid email",
    "responseType": "code",
    "requireHttps": false,
    "oidc": true,
    "strictDiscoveryDocumentValidation": false,
    "tokenEndpoint": "https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token",
    "userinfoEndpoint": "https://graph.microsoft.com/v1.0/me",
    "skipIssuerCheck": true
  }
```

{: .warning }
The following section applies to **SWIRL Enterprise Edition only**.
Community Edition users may skip to the next section.

## Activate the Authenticator

SWIRL includes a preconfigured **Microsoft Authenticator**, here: <http://localhost:8000/swirl/authenticators/Microsoft/>

* Update the `client-id`
* Update the `client-secret` 
* Change the `app_uri` to the address of the server where SWIRL is installed

```
{
    "idp": "Microsoft",
    "name": "Microsoft",
    "active": false,
    "callback_path": "/swirl/callback/microsoft-callback",
    "client_id": "<client-id>",
    "client_secret": "<client-secret>",
    "app_uri": "http://localhost:8000",
    "auth_uri": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
    "token_uri": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
    "user_data_url": "https://graph.microsoft.com/v1.0/me",
    "user_data_params": {
        "$select": "displayName,mail,userPrincipalName"
    },
    "user_data_headers": {
        "Authorization": "Bearer {access_token}"
    },
    "user_data_method": "GET",
    "initiate_auth_code_flow_params": {},
    "exchange_code_params": {},
    "is_code_challenge": true,
    "scopes": "User.Read Mail.Read Files.Read.All Calendars.Read Sites.Read.All Chat.Read offline_access",
    "should_expire": true,
    "use_basic_auth": true
}
```

Click the `PUT` button to save the Authenticator.

## Restart SWIRL

```shell
python swirl.py restart
```

# Activate the Microsoft 365 SearchProviders

The **SWIRL distribution** includes pre-configured **SearchProviders** for:

- **Outlook Email**  
- **Calendar Events**  
- **OneDrive Files**  
- **SharePoint Sites**  
- **Teams Chat**  

{: .warning }
The **Microsoft Teams desktop app must be open** before clicking a Teams Chat result link.  

{: .highlight }
> - **Calendar Events** – Only **recent** events are shown.  
> - **Outlook Threads** – Only the **latest** messages are shown.  
> - **OneDrive** – **Folders are omitted**; only documents appear.  
> - **Teams** – **Only chat messages** are indexed. Files shared in chats appear in **OneDrive or SharePoint results**.

**Enable Microsoft SearchProviders**

1. **Open the Admin Console**:  
   [http://localhost:8000/swirl/](http://localhost:8000/swirl/)

2. **Access SearchProviders**:  
   Click **`SearchProviders`** to view all configured providers.

3. **Find and Edit a Microsoft 365 SearchProvider:**  
   Each M365 app has its own **SearchProvider** entry.  
   - To edit a provider, add its `id` to the URL.  
   - Example: If the **id** is `16`, navigate to:  
     [http://localhost:8000/swirl/searchproviders/16/](http://localhost:8000/swirl/searchproviders/16/)

   ![SWIRL SearchProvider](images/swirl_sp_m365.png)

4. **Activate the Provider:**  
   - Scroll to the **Raw data** tab at the bottom.
   - Change `"active": false` → `"active": true`

   **Before:**  
   ```json
   {
     "id": 16,
     "name": "Outlook Messages - Microsoft 365",
     ...
     "active": false,
     ...
   }
   ```

   **After:**  
   ```json
   {
     "id": 16,
     "name": "Outlook Messages - Microsoft 365",
     ...
     "active": true,
     ...
   }
   ```

# Authenticating with Microsoft

To verify that **SWIRL-M365 integration** is working:

1. **Open the Galaxy UI:**  
   - [http://localhost:8000](http://localhost:8000)  
   - or [http://localhost:8000/galaxy/](http://localhost:8000/galaxy/)

2. **Enable Microsoft Authentication:**  
   - Click the **profile icon** (top right).  
   - Toggle **Microsoft** to activate authentication.  
   - If required, grant permissions during authentication.

   <img src="images/swirl_40_ms_login.png" alt="SSO Provider Login Page" width="300">

3. **Successful Connection:**  
   - The **Microsoft toggle lights up** after authentication.  
   - You can now search Microsoft 365 sources.

   ![SWIRL Assistant discussion](images/swirl_40_search_msft.png)

{: .warning }
If the **Microsoft toggle does not activate** after authentication, please [contact support](#support). The [Related Documentation](#related-documentation) below may also be helpful.

# Related Documentation

- [Register an app with Azure Active Directory](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/walkthrough-register-app-azure-active-directory) *(Some steps do not apply to the SWIRL App)*

- [Configure user consent for applications](https://learn.microsoft.com/en-us/azure/active-directory/manage-apps/configure-user-consent?pivots=portal#risk-based-step-up-consent)
