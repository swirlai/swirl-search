---
layout: default
title: Google Workspace Guide
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

<span class="big-text">Google Workspace Guide</span><br/><span class="med-text">Community Edition | Enterprise Edition</span>

---

This guide explains how to integrate SWIRL with an existing **Google Workspace (GW) tenant**. It is intended for **GW administrators** who have permission to **register new applications** in the **GW Portal**.  

Administrators may also need to **grant API permissions** so users can **query their personal GW content** through SWIRL.

# Register a New App in GW Portal

To connect **SWIRL** to an **GW tenant**, you must **register and configure a new App** in the **GW Portal**.

Once registered, the App allows:

- **User authentication via OIDC**
- **Personal GW content searches using OAuth2 permission consent**

## Before You Begin

Ensure you have the following details about your **SWIRL deployment**:

- **`swirl-host`** – The **fully qualified domain name** of your SWIRL instance.  
- **`swirl-port`** – The **port SWIRL runs on** (**only needed** if different from the default).  

Example:  
If your deployment is **`search.swirl.today`**, the `swirl-host` is **`search.swirl.today`**.

## HTTPS Requirement

To use **OIDC** and **OAuth2** with Microsoft, your deployment **must use** `https` (except when using `localhost`, where `http://` is allowed).

Single-Page Applications and Web Protocols in GW Applications require `https://` for fully qualified domains.

## Getting Started

1. **Log in to the GW Portal**: [https://portal.GW.com](https://portal.GW.com/)

2. In the **search bar**, type: **`app registrations`**, then select **"App registrations"** under **Services**.

   ![GW find app registration](images/GW_find_app_reg.png)

## Create the New Application

1. On the **"App registrations"** page, click **`New registration`**:

   ![GW New Registration](images/GW_new_registration.png)

2. On the **"Register an application"** page:

   - **Name** → Enter a name for the App (e.g., **`SWIRL Documentation App`**).
   - **Supported account types** → Select:  
     `Accounts in this organizational directory only (MSFT only - Single tenant)`.

3. **For the SWIRL Enterprise Edition:**
   - Add a **Redirect URI (optional)** value for a "Web" application:
     - **Platform**: `Web`
     - **Value**: `https://<swirl-host>[:<swirl-port>]/swirl/callback/microsoft-callback`

   ![GW App Registration](images/GW_app_registration.png)

4. Click **`Register`** to create the application.

## Configure Redirect URI(s) for a Single-Page Application

1. Navigate to the **"Authentication"** page and click **`Add a platform`** and select **"Single Page Application"**:

   ![Overview, Authentication option](images/Overview_to_authentication.png)
   ![Single-Page Application Protocol](images/Add_platform_single_page.png)

2. **For SWIRL Community edition:**
   - Add the OAuth2 callback URL:
      - Click `Add URI`
      - **Value**: `https://<swirl-host>[:<swirl-port>]/galaxy/microsoft-callback`
   - Click `Configure` to add the URI.

   ![Add Community OAuth Callback URL](images/OAuth-callback-Community.png)

3. **Optional, for both Community and Enterprise Editions:**
   - If you plan to configure "Login with Microsoft", add the OIDC Callback URL:
      - Click `Add URI`
      - **Value**: `https://<swirl-host>[:<swirl-port>]/galaxy/oidc-callback`
   - Click `Save` to add the URI.

   ![Add OIDC Callback URL](images/Add_OIDC_Callback.png)

4. Return to the **Authentication** screen:

   ![Return to Overview 1](images/Return_to_Overview_1.png)

# Add App API Permissions

## Assign the Necessary Permissions

1. In the left column, select **"API permissions"**, then click **`Add a permission`**:

   ![GW Add Permissions 1](images/GW_add_permissions_1.png)

2. In the **"Request API permissions"** panel that opens:
   - Select the **"Microsoft APIs"** tab (at the top).
   - Click the **"Microsoft Graph"** button.
   - Click the **"Delegated permissions"** button.

   ![GW Add Permissions 2](images/GW_add_permissions_2.png)

3. In the **search box**, enter and select each of the following permissions, then click **`Add permissions`**:

   ![GW Add Permissions 4](images/GW_add_permissions_4.png)

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

1. After adding the permissions, click **`Grant admin consent for <your-tenant>`** under **"Configured permissions"**:

   ![GW Add Permissions 3](images/GW_add_permissions_3.png)

2. Confirm by selecting **"Yes"**:

   ![GW Add Permissions 5](images/GW_add_permissions_5.png)

3. The **Configured permissions** section should now display all granted permissions:

   ![GW Add Permissions 6](images/GW_add_permissions_6.png)

# Generate a Client Secret

1. In the left sidebar, select **"Certificates & secrets"**, then click **`New client secret`**:

   ![GW Client Secret 1](images/GW_client_secret_1.png)

2. In the **"Add a client secret"** panel:
   - Enter a **`Description`** for the new secret.
   - Select an **`Expires`** time range for the secret.

   ![GW Client Secret 2](images/GW_client_secret_2.png)

3. Click **`Add`**. The **"Certificates & secrets"** page will now display a new **Client secret** entry.

   ![GW Client Secret 3](images/GW_client_secret_3.png)

{: .warning }
**Once the secret is created, copy the Value immediately!**  It will be **hidden permanently** once you leave this page.

# Configure OAuth2 for GW

## Community Edition

### Add the OAuth2 Configurations

To enable OAuth2 content search for GW in the SWIRL Community Edition, locate and copy the following values from your new GW App Registration:
- **`<application-id>`**  
- **`<tenant-id>`** 

![GW App Values](images/GW_app_values.png)

From the SWIRL home directory, open the `static/api/config/default` file within in an editor and locate the `msalConfig` section:

```
  "msalConfig": {
    "auth": {
      "clientId": "",
      "authority": "https://login.microsoftonline.com/",
      "redirectUri": "http://:/galaxy/microsoft-callback"
    }
  },
```

Update this section with the values from your GW App Registration and the host and (optional) port of the SWIRL application.  Those values should be added as follows:

```
  "msalConfig": {
    "auth": {
      "clientId": "<application-id>",
      "authority": "https://login.microsoftonline.com/<tenant-id>",
      "redirectUri": "http(s)://<swirl-host>(:<swirl-port>)/galaxy/microsoft-callback"
    }
  },
```

Example configuration for SWIRL running locally:

```
  "msalConfig": {
    "auth": {
      "clientId": "7df052ca-a153-4514-b26c-87eef2696e59",
      "authority": "https://login.microsoftonline.com/2c1f7fec-50db-4d19-99c2-073454d5e3c2",
      "redirectUri": "http://localhost:8000/galaxy/microsoft-callback"
    }
  },
```

Example configuration for SWIRL running behind a gateway:

```
  "msalConfig": {
    "auth": {
      "clientId": "7df052ca-a153-4514-b26c-87eef2696e59",
      "authority": "https://login.microsoftonline.com/2c1f7fec-50db-4d19-99c2-073454d5e3c2",
      "redirectUri": "https://search.swirl.today/galaxy/microsoft-callback"
    }
  },
```

### Restart SWIRL

```shell
python swirl.py restart
```

Proceed to [Activate the GW SearchProviders](#activate-the-microsoft-365-searchproviders) for Community Edition.


## Enterprise Edition

To enable OAuth2 content search for GW in the SWIRL Enterprise edition, locate and copy the following values from your new GW App Registration:
- **`<application-id>`**
- **`<tenant-id>`**
- **`<client-secret-value>`**

![GW App Values](images/GW_app_values.png)
![GW Secret Value](images/GW_secret_value.png)


### Configure the Microsoft Authenticator

SWIRL includes a preconfigured **Microsoft Authenticator**, here: <http://localhost:8000/swirl/authenticators/Microsoft/>

* Update the Authenticator `client_id` value with GW App `<application-id>`
* Update the Authenticator `client_secret` value with GW App `<client-secret-value>`
* Update the Authenticator `app_uri` value with the host and optional port of the SWIRL application.
* Update the Authenticator `auth_uri` and `token_uri` values to include the GW App `<tenant-id>` where indicated.
* Update the Authenticator `active` value to `true`.

{: .highlight }
Do not include a trailing slash in the `app_uri` value!


```json
{
    "idp": "Microsoft",
    "name": "Microsoft",
    "active": false,
    "callback_path": "/swirl/callback/microsoft-callback",
    "client_id": "<application(client)-id>",
    "client_secret": "<client-secret>",
    "app_uri": "https://<fully-qualified-domain-of-swirl-app>",
    "auth_uri": "https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/authorize",
    "token_uri": "https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token",
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
    "use_basic_auth": true,
    "expires_in": 0
}
```

Example Authenticator configuration for SWIRL running locally:

```json
{
    "idp": "Microsoft",
    "name": "Microsoft",
    "active": true,
    "callback_path": "/swirl/callback/microsoft-callback",
    "client_id": "7df052ca-a153-4514-b26c-87eef2696e59",
    "client_secret": "<secret-redacted>",
    "app_uri": "http://localhost:8000",
    "auth_uri": "https://login.microsoftonline.com/<tenant-id-redacted>/oauth2/v2.0/authorize",
    "token_uri": "https://login.microsoftonline.com/<tenant-id-redacted>/oauth2/v2.0/token",
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
    "use_basic_auth": true,
    "expires_in": 0
}
```

Click the `PUT` button to save the Authenticator.

Proceed to [Activate the GW SearchProviders](#activate-the-microsoft-365-searchproviders) for Enterprise Edition.

# Configuring OIDC for Microsoft

To enable OIDC ("Login with Microsoft) in both SWIRL Enterprise and Community edition, locate and copy the following values from your new GW App Registration:
- **`<application-id>`**
- **`<tenant-id>`**
- **`<oidc-callback-url>`**

{: .highlight }
Complete Step 3 of the [Configure Redirect URI(s) for a Single-Page Application](#configure-redirect-uris-for-a-single-page-application) section above before proceeding!

## Update the Default Configuration Values

From the SWIRL home directory, open the `static/api/config/default` file within in an editor and locate the `oidcConfig` section:

```
"oidcConfig": {
   "Google": {
      "active": false,
      "clientId":  "<google-client-id>.apps.googleusercontent.com",
      "redirectUri": "http://<swirl-host>:<swirl-port>/galaxy/oidc-callback",
      "scope": "openid email profile"
   }
},
```

Add the values from your GW App Registration to the `Google` section as follows:
* Update the `clientId` value with the GW App `<application-id>`
* Update the `redirectUri` value with the `<oidc-callback-url>` from your Single-Page Application
* Update the `issuer` field with the GW App `<tenant-id>`
* Update the `active` value to `true`

{: .highlight }
For the Enterprise Edition, the Google Authenticator must be correctly configured as well.  Please see above to [Configure the Google Workspace Authenticator](#TBD if needed.

### Restart SWIRL

```shell
python swirl.py restart
```

The SWIRL login page should now contain a `Login with Google` button configured to your GW tenant.

   ![Login with Microsoft](images/TBD)

## Configure OIDC for the SWIRL Preview Docker

{: .warning }
You must persist the `.env` file to your local working directory in order to enable OIDC in the Preview Docker following the instructions provided with the image.

Configure the following environment variables in the `.env` file persisted to the local working directory:

TBD: revise below

- `MS_AUTH_CLIENT_ID` - Microsoft application registration client ID value.
- `MS_TENANT_ID` - Tenant ID value from Microsoft GW IdP.
- `PROTOCOL` - The protocol used by the SWIRL instance (e.g. `http` or `https`).
- `SHOULD_USE_TOKEN_FROM_OAUTH`- Set this value to "True" (default) to use the tokens from OIDC. Otherwise, set it to False.
- `SWIRL_FQDN`	The Fully Qualified Domain Name of the SWIRL instance.
- `SWIRL_PORT`	The port used by SWIRL (defaults to `unset` allowing `PROTOCOL` to set to 443 for HTTPS, and 80 for HTTP).

### Restart the Preview Docker

```
docker-compose stop
docker-compose up
```

The SWIRL login page should now contain a `Login with Microsoft` button configured to your GW tenant.

![SWIRL with Login with Google Workspace button enabled via OIDC](images/swirl_login_google_workspace.png)

# Activate the Google Workspace SearchProviders

The **SWIRL distribution** includes pre-configured **SearchProviders** for:

- **Google Mail (GMail)**  
- **Google Calendar**  
- **Google Drive**  
- **Google Chat**  

{: .highlight }
> - **Google Mail** – Only the **latest** messages are shown.  
> - **Google Calendar** – Only **recent** events are shown.  
> - **Google Drive** – **Folders are omitted**; only documents appear.  
> - **Google Chat** – **Only chat messages** are indexed. Files shared in chats appear in **Google Drive results**.

**Enable Google Workplaces**

1. **Open the Admin Console**:  
   [http://localhost:8000/swirl/](http://localhost:8000/swirl/)

2. **Access SearchProviders**:  
   Click **`SearchProviders`** to view all configured providers.

3. **Find and Edit a Google Workspace SearchProvider:**  
   Each GW app has its own **SearchProvider** entry.  
   - To edit a provider, add its `id` to the URL.  
   - Example: If the **id** is `16`, navigate to:  
     [http://localhost:8000/swirl/searchproviders/16/](http://localhost:8000/swirl/searchproviders/16/)

   ![SWIRL SearchProvider](images/TBD)

4. **Activate the Provider:**  
   - Scroll to the **Raw data** tab at the bottom.
   - Change `"active": false` → `"active": true`

   **Before:**  
   ```json
   {
     "id": 16,
     "name": "Google Mail",
     ...
     "active": false,
     ...
   }
   ```

   **After:**  
   ```json
   {
     "id": 16,
     "name": "Google Mail",
     ...
     "active": true,
     ...
   }
   ```

# Authenticating with Microsoft

To verify that **SWIRL-GW integration** is working:

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
   - You can now search Google Workspace sources.

   ![SWIRL Assistant discussion](images/swirl_40_search_msft.png)

{: .warning }
If the **Microsoft toggle does not activate** after authentication, please [contact support](#support). The [Related Documentation](#related-documentation) below may also be helpful.

# Related Documentation

- [Register an app with GW Active Directory](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/walkthrough-register-app-GW-active-directory) *(Some steps do not apply to the SWIRL App)*

- [Configure user consent for applications](https://learn.microsoft.com/en-us/GW/active-directory/manage-apps/configure-user-consent?pivots=portal#risk-based-step-up-consent)
